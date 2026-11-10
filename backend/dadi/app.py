"""FastAPI app: browser and phone-line call bridges, live-call monitor, arena, REST for calls, reports and evidence.

Run:  uv run uvicorn dadi.app:create_app --factory --host 127.0.0.1 --port 8765
No keys / bad network:  set DADI_FAKE=1 (scripted scammer, canned Dadi lines, tone audio).
Phone line (Twilio / Exotel): see telephony.py and the README; protect it with DADI_PHONE_TOKEN.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
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
from .calls import CallDeps, CallHub, run_call
from .evidence import build_evidence_pack, feed_csv, mule_feed
from .fake_mode import DADI_LINES, CyclingLLM, ScriptedStt, all_audio, echo_stt, fake_embed, tone_tts, tone_tts_bytes
from .intel import IntelReport
from .personas import PERSONAS
from .report import build_report
from .rings import build_rings, speech_only
from .scammer_scripts import SCAMMER_VOICE
from .store import Store
from .telephony import CODECS, mask_number

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dadi")


def _env(name: str) -> str:
    """Env var, else the repo's .env (for app-only settings that voice-core's Settings does not carry)."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        from dotenv import dotenv_values

        return (dotenv_values(repo_root() / ".env").get(name) or "").strip()
    except Exception:
        return ""


def create_app(settings: Settings | None = None, *, session_factory=None, voice_embed_fn=None,
               phone_token: str | None = None) -> FastAPI:
    """`voice_embed_fn(api_key, wav) -> embedding dict` fingerprints callers (default: Gnani voice-clone embedding).
    `phone_token` (default env DADI_PHONE_TOKEN) must be presented by phone-line streams when set."""
    settings = settings or get_settings()
    fake = os.environ.get("DADI_FAKE") == "1"
    phone_token = _env("DADI_PHONE_TOKEN") if phone_token is None else phone_token
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
        return build_rings(store.list_calls(500), store.voiceprints())

    hub = CallHub()
    deps = CallDeps(settings=settings, store=store, factory=factory, voice_embed_fn=voice_embed_fn,
                    speech_filter=all_audio if fake else speech_only, hub=hub)

    # ------------------------------------------------------------------ browser call
    @app.websocket("/ws/call")
    async def ws_call(ws: WebSocket):
        await ws.accept()
        lock = asyncio.Lock()
        alive = {"v": True}

        async def out_json(m: dict):
            if alive["v"]:
                async with lock:
                    await ws.send_json(m)

        async def out_audio(b: bytes):
            if alive["v"]:
                async with lock:
                    await ws.send_bytes(b)

        async def close():
            alive["v"] = False
            await ws.close()

        try:
            first = await ws.receive_json()
        except Exception:
            return
        if first.get("type") != "start":
            await ws.close(code=1008)
            return

        async def inbound():
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    return
                if msg.get("bytes"):
                    yield "audio", msg["bytes"]
                elif msg.get("text"):
                    d = json.loads(msg["text"])
                    if d.get("type") == "hangup":
                        return
                    if d.get("type") == "set_noise":
                        yield "noise", d.get("snr_db")

        await run_call(deps, persona=first.get("persona") or "auto", inbound=inbound(), out_json=out_json,
                       out_audio=out_audio, noise_snr_db=first.get("noise_snr_db"), channel="web", on_end=close)

    # ------------------------------------------------------------------ real phone line (Twilio / Exotel)
    @app.api_route("/twilio/voice", methods=["GET", "POST"])
    async def twilio_voice(request: Request):
        """Twilio voice webhook: answer with TwiML that streams the call to /ws/twilio."""
        form = parse_qs((await request.body()).decode("utf-8", "replace")) if request.method == "POST" else {}
        persona = request.query_params.get("persona") or "auto"
        persona = persona if persona in PERSONAS else "auto"
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        params = {"persona": persona, "caller": mask_number((form.get("From") or [""])[0])}
        if phone_token:
            params["token"] = phone_token
        tags = "".join(f'<Parameter name="{k}" value="{html.escape(v, quote=True)}"/>' for k, v in params.items())
        xml = ('<?xml version="1.0" encoding="UTF-8"?><Response><Connect>'
               f'<Stream url="wss://{html.escape(host, quote=True)}/ws/twilio">{tags}</Stream></Connect></Response>')
        return Response(xml, media_type="text/xml")

    async def phone_call(ws: WebSocket, provider: str):
        await ws.accept()
        codec = CODECS[provider]()
        try:
            while True:  # Twilio sends "connected" first; the call starts with "start"
                d = json.loads(await ws.receive_text())
                if d.get("event") == "start":
                    start = codec.on_start(d)
                    break
                if d.get("event") == "stop":
                    return
        except Exception:
            return
        params = start.get("params") or {}
        if phone_token and phone_token not in (params.get("token"), ws.query_params.get("token")):
            log.warning("%s stream rejected: bad or missing token", provider)
            await ws.close(code=1008)
            return
        lock = asyncio.Lock()
        alive = {"v": True}

        async def send(msgs: list[str]):
            if alive["v"] and msgs:
                async with lock:
                    for m in msgs:
                        await ws.send_text(m)

        async def out_audio(b: bytes):
            await send(codec.encode(b))

        async def out_json(m: dict):
            if m.get("type") == "stop_audio":
                await send(codec.clear())
            elif m.get("type") == "agent_speaking" and not m.get("on"):
                await send(codec.flush())

        async def close():
            alive["v"] = False
            await ws.close()

        async def inbound():
            while True:
                d = json.loads(await ws.receive_text())
                ev = d.get("event")
                if ev == "media":
                    yield "audio", codec.decode(d)
                elif ev == "stop":
                    return

        persona = params.get("persona") if params.get("persona") in PERSONAS else "auto"
        caller = params.get("caller") or mask_number(start.get("from"))
        await run_call(deps, persona=persona, inbound=inbound(), out_json=out_json, out_audio=out_audio,
                       channel=provider, channel_info={"caller": caller} if caller else None, on_end=close)

    @app.websocket("/ws/twilio")
    async def ws_twilio(ws: WebSocket):
        await phone_call(ws, "twilio")

    @app.websocket("/ws/exotel")
    async def ws_exotel(ws: WebSocket):
        await phone_call(ws, "exotel")

    # ------------------------------------------------------------------ live-call monitor (war room for phone calls)
    @app.websocket("/ws/monitor")
    async def ws_monitor(ws: WebSocket):
        await ws.accept()
        q = hub.subscribe()

        async def pump():
            while True:
                await ws.send_json(await q.get())

        async def drain():  # returns when the viewer goes away
            while True:
                if (await ws.receive()).get("type") == "websocket.disconnect":
                    return

        tasks = [asyncio.create_task(pump()), asyncio.create_task(drain())]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            hub.unsubscribe(q)
            for t in tasks:
                t.cancel()

    @app.get("/api/live")
    async def live():
        return hub.live_calls()

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
