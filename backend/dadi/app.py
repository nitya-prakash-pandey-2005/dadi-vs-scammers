"""FastAPI app: WebSocket call bridge + REST for calls, totals and complaint reports.

Run:  uv run uvicorn dadi.app:create_app --factory --host 127.0.0.1 --port 8765
No keys / bad network:  set DADI_FAKE=1 (scripted scammer, canned Dadi lines, tone audio).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from voice_core.audio import pink_noise
from voice_core.config import Settings, get_settings, repo_root
from voice_core.audio import wav_bytes
from voice_core.gnani.tts import create_voice_embedding
from voice_core.llm import LLM
from voice_core.session import VoiceAgentSession
from voice_core.types import Turn

from voice_core.testing import FakeLLM

from .agent import DadiAgent
from .arena import run_arena, run_noise_benchmark
from .assets import load_or_make_babble, load_or_make_fillers
from .fake_mode import DADI_LINES, CyclingLLM, ScriptedStt, echo_stt, tone_tts, tone_tts_bytes
from .intel import IntelReport
from .personas import PERSONAS
from .checker import check_message
from .insights import freeze_csv, freeze_list, insights
from .report import build_report
from .rings import tts_catalog, build_rings, speech_only, voiceprint_vec
from .scammer_scripts import SCAMMER_VOICE
from .tactics import MISSIONS
from .store import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dadi")


def create_app(settings: Settings | None = None, *, session_factory=None) -> FastAPI:
    settings = settings or get_settings()
    fake = os.environ.get("DADI_FAKE") == "1"
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.cache_dir / ("dadi_fake.db" if fake else "dadi.db"))
    st = SimpleNamespace(fillers={}, babble=pink_noise(settings.sample_rate * 10, seed=5), ready=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if fake or session_factory is not None:
            st.ready = True
        else:
            async def warm():
                st.fillers = await load_or_make_fillers(settings, settings.cache_dir)
                st.babble = await load_or_make_babble(settings, settings.cache_dir)
                st.ready = True
                log.info("assets ready: %d filler clips", len(st.fillers))

            task = asyncio.create_task(warm())
        yield
        if task and not task.done():
            task.cancel()

    app = FastAPI(title="Dadi vs Scammers", lifespan=lifespan)

    def default_factory(send_json, send_audio, persona: str):
        if fake:
            agent = DadiAgent(store=store, llm=CyclingLLM(DADI_LINES), intel_llm=CyclingLLM([]), persona_key=persona)
            sess = VoiceAgentSession(agent, send_json=send_json, send_audio=send_audio, settings=settings,
                                     stt_factory=lambda: ScriptedStt(), tts_fn=tone_tts, noise=st.babble)
        else:
            agent = DadiAgent(store=store, llm=LLM(settings), intel_llm=LLM(settings, purpose="intel"), persona_key=persona)
            sess = VoiceAgentSession(agent, send_json=send_json, send_audio=send_audio, settings=settings,
                                     filler_audio=st.fillers, noise=st.babble)
        return sess, agent

    factory = session_factory or default_factory

    # ------------------------------------------------------------------ REST
    @app.get("/api/health")
    async def health():
        return {
            "gnani_key": bool(settings.gnani_api_key),
            "llm_key": bool(settings.groq_api_key or settings.evon_base_url),
            "llm_provider": settings.llm_provider,
            "intel_llm_provider": settings.intel_llm_provider,
            "stt_mode": settings.stt_mode,
            "fillers_ready": st.ready,
            "fake": fake,
        }

    @app.get("/api/personas")
    async def personas():
        return [{"key": p.key, "name": p.name, "age": p.age, "city": p.city, "language": p.language, "voice": p.voice}
                for p in PERSONAS.values()]

    @app.get("/api/missions")
    async def missions():
        return [{"key": k, "label": v["label"]} for k, v in MISSIONS.items()]

    @app.get("/api/totals")
    async def totals():
        return store.totals()

    @app.get("/api/calls")
    async def calls():
        return store.list_calls()

    @app.get("/api/calls/{call_id}")
    async def call(call_id: str):
        c = store.get_call(call_id)
        if not c:
            raise HTTPException(404, "call not found")
        return c

    @app.get("/api/calls/{call_id}/report")
    async def report(call_id: str):
        c = store.get_call(call_id)
        if not c:
            raise HTTPException(404, "call not found")
        turns = [Turn(t["speaker"], t["text"], t["t"] or 0.0, t.get("lang")) for t in c["turns"]]
        intel = IntelReport(**(c.get("intel") or {}))
        return build_report(c, turns, intel)

    @app.get("/api/rings")
    async def rings():
        return build_rings(store.list_calls(500), store.voiceprints(), catalog=tts_catalog())

    @app.post("/api/check")
    async def check(body: dict):
        text = str(body.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "text is required")
        if fake:
            return await check_message(text, intel_llm=CyclingLLM([]), llm=CyclingLLM(DADI_LINES))
        return await check_message(text, intel_llm=LLM(settings, purpose="intel"), llm=LLM(settings))

    @app.get("/api/insights")
    async def get_insights():
        return insights(store.list_calls(500))

    @app.get("/api/freeze-list")
    async def get_freeze_list(format: str = "json"):
        calls = store.list_calls(500)
        rows = freeze_list(calls, build_rings(calls, store.voiceprints()))
        if format == "csv":
            return Response(freeze_csv(rows), media_type="text/csv",
                            headers={"Content-Disposition": "attachment; filename=dadi-freeze-list.csv"})
        return rows

    async def fingerprint_caller(call_id: str, pcm: bytes):
        speech = speech_only(pcm, settings.sample_rate)
        if fake or not call_id or len(speech) / 2 / settings.sample_rate < 5:
            return
        try:
            emb = await create_voice_embedding(settings.gnani_api_key, wav_bytes(speech, settings.sample_rate))
            store.save_voiceprint(call_id, voiceprint_vec(emb))
        except Exception as e:
            log.info("voiceprint failed: %r", e)

    # ------------------------------------------------------------------ WebSocket call
    @app.websocket("/ws/call")
    async def ws_call(ws: WebSocket):
        await ws.accept()
        lock = asyncio.Lock()
        alive = {"v": True}

        async def send_json(m: dict):
            if alive["v"]:
                async with lock:
                    await ws.send_json(m)

        async def send_audio(b: bytes):
            if alive["v"]:
                async with lock:
                    await ws.send_bytes(b)

        try:
            first = await ws.receive_json()
        except Exception:
            return
        if first.get("type") != "start":
            await ws.close(code=1008)
            return
        sess, agent = factory(send_json, send_audio, first.get("persona") or "auto")
        if first.get("mission") in MISSIONS:
            agent.state.mission = first["mission"]
        await sess.start()
        caller_pcm = bytearray()  # scammer's mic, for the voice fingerprint after hang-up
        if first.get("noise_snr_db") is not None:
            await sess.set_noise(float(first["noise_snr_db"]))
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    if len(caller_pcm) < settings.sample_rate * 2 * 120:
                        caller_pcm.extend(msg["bytes"])
                    await sess.on_audio(msg["bytes"])
                elif msg.get("text"):
                    d = json.loads(msg["text"])
                    if d.get("type") == "hangup":
                        break
                    if d.get("type") == "set_noise":
                        snr = d.get("snr_db")
                        await sess.set_noise(None if snr is None else float(snr))
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            res = await sess.hangup()
            asyncio.create_task(fingerprint_caller(agent.call_id, bytes(caller_pcm)))
            try:
                await send_json({"type": "call_ended", "call_id": agent.call_id, "wasted_seconds": res["session_seconds"]})
            except Exception:
                pass
            alive["v"] = False
            try:
                await ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ Arena (AI scammer vs AI Dadi) + noise benchmark
    @app.websocket("/ws/arena")
    async def ws_arena(ws: WebSocket):
        await ws.accept()
        try:
            req = await ws.receive_json()
        except Exception:
            return

        async def emit(m: dict):
            await ws.send_json(m)

        fakes = dict(tts_fn=tone_tts_bytes, stt_fn=echo_stt) if fake else {}
        try:
            if not fake and not settings.gnani_api_key:
                await emit({"type": "error", "message": "GNANI_API_KEY missing in .env"})
            elif req.get("type") == "benchmark":
                snrs = tuple(req.get("snr_list") or (None, 20, 10, 5, 0))
                await run_noise_benchmark(settings=settings, emit=emit, noise=st.babble, snr_list=snrs, **fakes)
            else:
                await run_arena(
                    scam_type=req.get("scam_type") or "digital_arrest",
                    turns=max(1, min(12, int(req.get("turns") or 6))),
                    snr_db=req.get("snr_db"),
                    settings=settings,
                    scammer_llm=FakeLLM([]) if fake else LLM(settings),
                    dadi_llm=CyclingLLM(DADI_LINES) if fake else LLM(settings),
                    intel_llm=CyclingLLM([]) if fake else LLM(settings, purpose="intel"),
                    emit=emit, noise=st.babble, persona_key=req.get("persona") or "dadi",
                    scammer_voice=req.get("scammer_voice") or SCAMMER_VOICE, store=store,
                    mission=req.get("mission") if req.get("mission") in MISSIONS else None,
                    embed_fn=None if fake else create_voice_embedding, **fakes,
                )
        except (WebSocketDisconnect, RuntimeError):
            return
        except Exception as e:
            log.exception("arena failed")
            try:
                await emit({"type": "error", "message": repr(e)})
            except Exception:
                return
        try:
            await ws.close()
        except Exception:
            pass

    dist = repo_root() / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")
    return app
