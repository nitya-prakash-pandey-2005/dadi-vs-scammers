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
from fastapi.staticfiles import StaticFiles

from voice_core.audio import pink_noise
from voice_core.config import Settings, get_settings, repo_root
from voice_core.llm import LLM
from voice_core.session import VoiceAgentSession
from voice_core.types import Turn

from .agent import DadiAgent
from .assets import load_or_make_babble, load_or_make_fillers
from .fake_mode import DADI_LINES, CyclingLLM, ScriptedStt, tone_tts
from .intel import IntelReport
from .personas import PERSONAS
from .report import build_report
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
        await sess.start()
        if first.get("noise_snr_db") is not None:
            await sess.set_noise(float(first["noise_snr_db"]))
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
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
            try:
                await send_json({"type": "call_ended", "call_id": agent.call_id, "wasted_seconds": res["session_seconds"]})
            except Exception:
                pass
            alive["v"] = False
            try:
                await ws.close()
            except Exception:
                pass

    dist = repo_root() / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")
    return app
