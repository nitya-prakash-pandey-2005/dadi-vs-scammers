"""FastAPI app: WebSocket call bridge + REST for calls, totals and complaint reports.

Run:  uv run uvicorn dadi.app:create_app --factory --host 127.0.0.1 --port 8765
No keys / bad network:  set DADI_FAKE=1 (scripted scammer, canned Dadi lines, tone audio).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from voice_core.audio import pink_noise
from voice_core.config import Settings, get_settings, repo_root
from voice_core.gnani.tts import create_voice_embedding
from voice_core.llm import LLM
from voice_core.session import VoiceAgentSession
from voice_core.types import Turn

from voice_core.testing import FakeLLM

from .agent import DadiAgent
from .arena import run_arena, run_noise_benchmark
from .assets import load_or_make_babble, load_or_make_fillers
from .evidence import CallRecorder, build_evidence_pack, feed_csv, mule_feed
from .fake_mode import DADI_LINES, CyclingLLM, ScriptedStt, all_audio, echo_stt, fake_embed, tone_tts, tone_tts_bytes
from .intel import IntelReport
from .personas import PERSONAS
from .checker import check_message
from .insights import freeze_csv, freeze_list, insights
from .report import build_report
from .rings import build_rings, speech_only, tts_catalog
from .scammer_scripts import SCAMMER_VOICE
from .tactics import MISSIONS
from .store import Store
from .voicewatch import VoiceWatch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dadi")


def create_app(settings: Settings | None = None, *, session_factory=None, voice_embed_fn=None) -> FastAPI:
    """`voice_embed_fn(api_key, wav) -> embedding dict` fingerprints callers (default: Gnani voice-clone embedding)."""
    settings = settings or get_settings()
    fake = os.environ.get("DADI_FAKE") == "1"
    if voice_embed_fn is None:
        voice_embed_fn = fake_embed if fake else (create_voice_embedding if settings.gnani_api_key else None)
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
            # realtime: no SDK retries (a 429 Retry-After means minutes of silence) and a 5 s first-token limit;
            # the session then says a pre-rendered "say that again?" line instead of dead air
            llm = LLM(settings, max_retries=0, first_token_timeout=5.0)
            agent = DadiAgent(store=store, llm=llm, intel_llm=LLM(settings, purpose="intel"), persona_key=persona)
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

    def _report_parts(call_id: str):
        c = store.get_call(call_id)
        if not c:
            raise HTTPException(404, "call not found")
        turns = [Turn(t["speaker"], t["text"], t["t"] or 0.0, t.get("lang")) for t in c["turns"]]
        r = build_report(c, turns, IntelReport(**(c.get("intel") or {})))
        rec = store.recording(call_id)
        if rec and not Path(rec["path"]).exists():
            rec = None
        r["recording"] = ({k: v for k, v in rec.items() if k != "path"} | {"url": f"/api/calls/{call_id}/audio"}
                          if rec else None)
        return r, turns, rec

    @app.get("/api/calls/{call_id}/report")
    async def report(call_id: str):
        return _report_parts(call_id)[0]

    @app.get("/api/calls/{call_id}/audio")
    async def call_audio(call_id: str):
        rec = store.recording(call_id)
        if not rec or not Path(rec["path"]).exists():
            raise HTTPException(404, "no recording for this call")
        return FileResponse(rec["path"], media_type="audio/wav", filename=f"dadi-call-{call_id}.wav")

    @app.get("/api/calls/{call_id}/evidence.zip")
    async def evidence(call_id: str):
        r, turns, rec = _report_parts(call_id)
        wav = Path(rec["path"]).read_bytes() if rec else None
        return Response(build_evidence_pack(r, turns, wav, rec), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="dadi-evidence-{call_id}.zip"'})

    def _feed() -> list[dict]:
        calls = store.list_calls(5000)
        ring_of = {n["id"]: n["ring"] for n in build_rings(calls, store.voiceprints())["nodes"] if n["ring"]}
        return mule_feed(calls, ring_of)

    @app.get("/api/feed/mule-ids.json")
    async def feed_json():
        return {"generated_at": time.time(), "note": "Identifiers revealed by suspected scam callers. Leads, not proof.",
                "rows": _feed()}

    @app.get("/api/feed/mule-ids.csv")
    async def feed_csv_file():
        return Response(feed_csv(_feed()), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="dadi-mule-ids.csv"'})

    @app.get("/api/rings")
    async def rings():
        return build_rings(store.list_calls(500), store.voiceprints(), catalog=tts_catalog())

    @app.post("/api/check")
    async def check(body: dict):
        text = str(body.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "text is required")
        if fake:
            return await check_message(text, intel_llm=CyclingLLM([]), llm=CyclingLLM(DADI_LINES), calls=store.list_calls(500))
        return await check_message(text, intel_llm=LLM(settings, purpose="intel"), llm=LLM(settings),
                                   calls=store.list_calls(500))

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

    # ------------------------------------------------------------------ WebSocket call
    @app.websocket("/ws/call")
    async def ws_call(ws: WebSocket):
        await ws.accept()
        lock = asyncio.Lock()
        alive = {"v": True}
        recorder = CallRecorder(settings.sample_rate)  # two-track evidence recording (caller | Dadi as played)
        t0 = {"v": time.monotonic()}

        def now() -> float:
            return time.monotonic() - t0["v"]

        async def send_json(m: dict):
            if m.get("type") == "stop_audio":
                recorder.stop_agent(now())
            if alive["v"]:
                async with lock:
                    await ws.send_json(m)

        async def send_audio(b: bytes):
            recorder.agent(b, now())
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

        async def on_repeat_caller(match: dict):
            if hasattr(agent, "recognise"):
                await send_json(agent.recognise(match))

        # Dadi never forgets a voice: fingerprint the caller live, tease a repeat caller, save it for the ring radar
        watch = VoiceWatch(store=getattr(agent, "store", store), call_id=agent.call_id, sample_rate=settings.sample_rate,
                           embed_fn=voice_embed_fn, api_key=settings.gnani_api_key, on_match=on_repeat_caller,
                           speech_filter=all_audio if fake else speech_only)
        t0["v"] = time.monotonic()
        try:
            await sess.start()
            if first.get("noise_snr_db") is not None:
                await sess.set_noise(float(first["noise_snr_db"]))
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    recorder.caller(msg["bytes"], now())
                    if not getattr(sess, "speaking", False):  # keep Dadi's own echoed voice out of his fingerprint
                        watch.feed(msg["bytes"])
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
        except Exception as e:  # never lose the call row, recording or voiceprint because of one bad message
            log.warning("call loop failed: %r", e)
        finally:
            res = await sess.hangup()
            call_store = getattr(agent, "store", store)
            try:
                meta = recorder.save(settings.cache_dir / "recordings", agent.call_id)
                if meta:
                    call_store.save_recording(agent.call_id, meta)
            except Exception as e:
                log.warning("saving the call recording failed: %r", e)
            try:
                await send_json({"type": "call_ended", "call_id": agent.call_id, "wasted_seconds": res["session_seconds"]})
            except Exception:
                pass
            alive["v"] = False
            try:
                await ws.close()
            except Exception:
                pass
            await watch.finish()  # after the caller has the result: saves his voice fingerprint (one Gnani call)

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
                    embed_fn=None if fake else voice_embed_fn, **fakes,
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
