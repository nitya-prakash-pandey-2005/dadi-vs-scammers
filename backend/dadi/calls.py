"""One live call, whatever carries it (the browser phone or a real phone line), plus the live-call monitor.

`run_call` wires a VoiceAgentSession to a transport: inbound audio and controls in, JSON events and agent audio out.
Around the session it keeps the two-track evidence recording, the live voice fingerprint (repeat callers) and,
at hang-up, saves both. Every JSON event also goes to the `CallHub`, so a war-room viewer can watch any live call
(e.g. a real phone call on the laptop screen) without being part of it.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable

from .evidence import CallRecorder
from .voicewatch import VoiceWatch

log = logging.getLogger(__name__)

SendJson = Callable[[dict], Awaitable[None]]
SendAudio = Callable[[bytes], Awaitable[None]]
Inbound = AsyncIterator[tuple[str, Any]]  # ("audio", pcm16 bytes) | ("noise", snr_db or None)


class CallHub:
    """Fan-out of live calls' JSON events (never audio) to monitor viewers; replays live calls to late joiners."""

    MAX_EVENTS = 500
    QUEUE = 2000

    def __init__(self):
        self._subs: set[asyncio.Queue] = set()
        self._live: dict[str, list[dict]] = {}

    def publish(self, call_id: str, msg: dict) -> None:
        m = {**msg, "call_id": msg.get("call_id") or call_id}
        if m.get("type") == "call_ended":
            self._live.pop(call_id, None)
        else:
            evts = self._live.setdefault(call_id, [])
            if len(evts) < self.MAX_EVENTS:
                evts.append(m)
        for q in list(self._subs):
            try:
                q.put_nowait(m)
            except asyncio.QueueFull:  # a stuck viewer must never slow a call down
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(self.QUEUE)
        for evts in self._live.values():
            for m in evts:
                q.put_nowait(m)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def live_calls(self) -> list[dict]:
        return [evts[0] for evts in self._live.values() if evts]


@dataclass
class CallDeps:
    settings: Any
    store: Any
    factory: Callable  # (send_json, send_audio, persona) -> (session, agent)
    voice_embed_fn: Callable | None
    speech_filter: Callable[[bytes, int], bytes]
    hub: CallHub


async def run_call(deps: CallDeps, *, persona: str, inbound: Inbound, out_json: SendJson, out_audio: SendAudio,
                   noise_snr_db: float | None = None, channel: str = "web", channel_info: dict | None = None,
                   on_end: Callable[[], Awaitable[None]] | None = None) -> dict:
    settings = deps.settings
    recorder = CallRecorder(settings.sample_rate)
    t0 = time.monotonic()
    extra = {"channel": channel, **(channel_info or {})}
    ids: dict[str, str] = {}

    def now() -> float:
        return time.monotonic() - t0

    async def send_json(m: dict) -> None:
        if m.get("type") == "stop_audio":
            recorder.stop_agent(now())
        if m.get("type") == "session_started":
            m = {**m, **extra}
        deps.hub.publish(ids.get("call", ""), m)
        try:
            await out_json(m)
        except Exception as e:  # the transport went away; the call still ends cleanly
            log.info("out_json failed: %r", e)

    async def send_audio(b: bytes) -> None:
        recorder.agent(b, now())
        await out_audio(b)

    sess, agent = deps.factory(send_json, send_audio, persona)
    ids["call"] = agent.call_id
    call_store = getattr(agent, "store", deps.store)

    async def on_repeat_caller(match: dict) -> None:
        if hasattr(agent, "recognise"):
            await send_json(agent.recognise(match))

    # Dadi never forgets a voice: fingerprint the caller live, tease a repeat caller, save it for the ring radar
    watch = VoiceWatch(store=call_store, call_id=agent.call_id, sample_rate=settings.sample_rate,
                       embed_fn=deps.voice_embed_fn, api_key=settings.gnani_api_key, on_match=on_repeat_caller,
                       speech_filter=deps.speech_filter)
    t0 = time.monotonic()
    await sess.start()
    if noise_snr_db is not None:
        await sess.set_noise(float(noise_snr_db))
    try:
        async for kind, data in inbound:
            if kind == "audio" and data:
                recorder.caller(data, now())
                if not getattr(sess, "speaking", False):  # keep Dadi's own echoed voice out of his fingerprint
                    watch.feed(data)
                await sess.on_audio(data)
            elif kind == "noise":
                await sess.set_noise(None if data is None else float(data))
    except Exception as e:  # WebSocketDisconnect, network errors: hang up normally
        log.info("call %s transport ended: %r", agent.call_id, e)
    finally:
        res = await sess.hangup()
        try:
            meta = recorder.save(settings.cache_dir / "recordings", agent.call_id)
            if meta:
                call_store.save_recording(agent.call_id, meta)
        except Exception as e:
            log.warning("saving the call recording failed: %r", e)
        await send_json({"type": "call_ended", "call_id": agent.call_id, "wasted_seconds": res["session_seconds"]})
        if on_end is not None:
            try:
                await on_end()
            except Exception:
                pass
        await watch.finish()  # after the caller has the result: saves his voice fingerprint (one Gnani call)
    return {"call_id": agent.call_id, **res}
