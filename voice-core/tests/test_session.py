"""VoiceAgentSession hardening: dead air, start-up failures, barge-in, echo, reconnects (offline fakes only)."""

import asyncio
import random

from voice_core.config import Settings
from voice_core.session import VoiceAgentSession
from voice_core.testing import FakeStt, ev, fake_tts
from voice_core.types import Turn


class StubAgent:
    """Minimal Agent: replies are scripted lists of sentences; a reply may be an Exception to raise."""

    user_label, agent_label = "caller", "agent"
    voice, tts_language, speed = "v", "hi-IN", 1.0
    stt_language_code, keyterms = "hi-IN", []

    def __init__(self, replies=None, *, greeting="", fillers=None, fallbacks=None, analyse=None):
        self.replies = list(replies or [])
        self._greeting = greeting
        self._fillers = list(fillers or [])
        if fallbacks is not None:
            self.fallback_texts = lambda: list(fallbacks)
        self.analyse = analyse
        self.recorded: list[Turn] = []
        self.analysed: list[int] = []
        self.ended = None

    def greeting(self):
        return self._greeting

    def filler_texts(self):
        return self._fillers

    def on_language(self, code):
        return None

    async def reply_sentences(self, history):
        r = self.replies.pop(0) if self.replies else []
        if isinstance(r, BaseException):
            raise r
        if callable(r):
            async for s in r():
                yield s
            return
        for s in r:
            await asyncio.sleep(0)
            yield s

    async def on_user_turn(self, history):
        self.analysed.append(len(history))
        if self.analyse:
            return await self.analyse(history)
        return None

    async def record(self, turn):
        self.recorded.append(turn)

    def end(self, secs):
        self.ended = secs


def make(agent, *, streams=None, factory=None, tts=fake_tts, filler_audio=None, delays=(0.01,), **kw):
    out_json, out_audio = [], []
    streams = list(streams or [])

    async def sj(m):
        out_json.append(m)

    async def sa(b):
        out_audio.append(b)

    sess = VoiceAgentSession(agent, send_json=sj, send_audio=sa, settings=Settings(sample_rate=8000),
                             stt_factory=factory or (lambda: streams.pop(0)), tts_fn=tts, rng=random.Random(0),
                             filler_audio=filler_audio, reconnect_delays=delays, **kw)
    return sess, out_json, out_audio


def turns(out_json, speaker):
    return [m for m in out_json if m.get("type") == "turn" and m.get("speaker") == speaker]


CLIP = b"\x00\x01" * 800  # 0.2 s at 8 kHz


# ---------------------------------------------------------------- 1. dead air when the LLM fails

async def test_llm_error_speaks_a_fallback_line():
    agent = StubAgent([RuntimeError("Groq 429")], fillers=["hmm", "ek minute"], fallbacks=["phir se bolo?"])
    stt = FakeStt([ev("transcript", "hello madam CBI se")], gap=0.01)
    sess, out_json, out_audio = make(agent, streams=[stt], filler_audio={"hmm": CLIP, "phir se bolo?": CLIP})
    await sess.start()
    await asyncio.sleep(0.1)
    await sess.wait_idle()
    said = [m["text"] for m in turns(out_json, "agent")]
    assert said == ["phir se bolo?"]
    assert CLIP in out_audio
    await sess.hangup()


async def test_empty_reply_falls_back_to_fillers_never_twice_in_a_row():
    agent = StubAgent([[], [], []], fillers=["a", "b", "not-rendered"])
    stt = FakeStt([ev("transcript", "pehli baat"), ev("transcript", "doosri baat"), ev("transcript", "teesri baat")],
                  gap=0.05)
    sess, out_json, _ = make(agent, streams=[stt], filler_audio={"a": CLIP, "b": CLIP})
    await sess.start()
    await asyncio.sleep(0.3)
    await sess.wait_idle()
    said = [m["text"] for m in turns(out_json, "agent")]
    assert len(said) == 3 and set(said) <= {"a", "b"}
    assert all(x != y for x, y in zip(said, said[1:]))
    await sess.hangup()


async def test_slow_first_sentence_times_out_into_fallback():
    async def hang():
        await asyncio.sleep(10)
        yield "too late"

    agent = StubAgent([hang], fillers=["hmm"])
    stt = FakeStt([ev("transcript", "hello ji")], gap=0.01)
    sess, out_json, _ = make(agent, streams=[stt], filler_audio={"hmm": CLIP}, first_sentence_timeout=0.1)
    await sess.start()
    await asyncio.sleep(0.4)
    await sess.wait_idle()
    assert [m["text"] for m in turns(out_json, "agent")] == ["hmm"]
    await sess.hangup()


async def test_no_fallback_when_reply_spoke_or_was_cancelled():
    agent = StubAgent([["theek hai."]], fillers=["hmm"])
    stt = FakeStt([ev("transcript", "hello ji")], gap=0.01)
    sess, out_json, _ = make(agent, streams=[stt], filler_audio={"hmm": CLIP})
    await sess.start()
    await asyncio.sleep(0.1)
    await sess.wait_idle()
    assert [m["text"] for m in turns(out_json, "agent")] == ["theek hai."]
    await sess.hangup()
