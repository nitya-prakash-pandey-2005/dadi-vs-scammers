import asyncio
import random

import pytest

from voice_core.config import Settings
from voice_core.session import VoiceAgentSession
from voice_core.testing import FakeLLM, FakeStt, ev, fake_tts
from voice_core.turns import is_echo, is_meaningful
from voice_core.types import Turn

from dadi.agent import DadiAgent
from dadi.intel import IntelReport
from dadi.personas import PERSONAS
from dadi.store import Store


def test_is_echo_and_meaningful():
    assert is_echo("haan beta ek minute", ["हाँ बेटा <coughs>", "haan beta, ek minute!"])
    assert not is_echo("aapka aadhaar number batao", ["haan beta, ek minute!"])
    assert not is_meaningful("  . ") and is_meaningful("ok")


def make_session(tmp_path, out_json, out_audio, *, streams, dialogue, intel, tts=fake_tts, persona="dadi", delays=(0.01,)):
    store = Store(tmp_path / "d.db")
    agent = DadiAgent(store=store, llm=FakeLLM(dialogue), intel_llm=FakeLLM(intel), persona_key=persona, seed=1)
    streams = list(streams)

    async def sj(m):
        out_json.append(m)

    async def sa(b):
        out_audio.append(b)

    sess = VoiceAgentSession(
        agent, send_json=sj, send_audio=sa, settings=Settings(sample_rate=8000),
        stt_factory=lambda: streams.pop(0), tts_fn=tts, rng=random.Random(0), reconnect_delays=delays,
    )
    return sess, agent, store


def turns_of(out_json, speaker):
    return [m for m in out_json if m.get("type") == "turn" and m.get("speaker") == speaker]


async def test_reply_flow_sends_turns_audio_and_intel(tmp_path):
    out_json, out_audio = [], []
    stt = FakeStt([ev("connected"), ev("transcript", "Main CBI se bol raha hoon, aapka UPI do", "hi-IN")], gap=0.01)
    sess, agent, store = make_session(
        tmp_path, out_json, out_audio, streams=[stt],
        dialogue=["हाँ बेटा। रुको ज़रा।"], intel=['{"scam_type":"digital_arrest","scam_confidence":0.8}'],
    )
    await sess.start()
    await asyncio.sleep(0.1)
    await sess.wait_idle()
    kinds = [m["type"] for m in out_json]
    assert kinds[0] == "session_started" and out_json[0]["call_id"] == agent.call_id
    assert len(turns_of(out_json, "scammer")) == 1 and len(turns_of(out_json, "dadi")) == 2  # greeting + reply
    assert "intel" in kinds and out_json[kinds.index("intel")]["intel"]["scam_type"] == "digital_arrest"
    assert len(out_audio) >= 4
    assert turns_of(out_json, "dadi")[-1]["tactic"]
    await sess.hangup()
    assert store.get_call(agent.call_id)["ended_at"] is not None


async def test_echo_and_silence_do_not_trigger_reply(tmp_path):
    out_json, out_audio = [], []
    greeting = PERSONAS["dadi"].greeting
    stt = FakeStt([ev("transcript", ""), ev("transcript", " . "), ev("transcript", greeting.replace("<clears throat>", ""))], gap=0.01)
    sess, *_ = make_session(tmp_path, out_json, out_audio, streams=[stt], dialogue=["should not be used"], intel=[])
    await sess.start()
    await asyncio.sleep(0.1)
    await sess.wait_idle()
    assert len(turns_of(out_json, "scammer")) == 0
    assert len(turns_of(out_json, "dadi")) == 1  # only the greeting
    await sess.hangup()


async def slow_tts(*a, **k):
    for _ in range(6):
        await asyncio.sleep(0.05)
        yield b"\x00\x01" * 160


async def test_barge_in_sends_stop_audio(tmp_path):
    out_json, out_audio = [], []
    stt = FakeStt([ev("transcript", "hello ji kaun bol raha"), ev("speech_start")], gap=0.06)
    sess, *_ = make_session(tmp_path, out_json, out_audio, streams=[stt], dialogue=["हाँ बेटा, बहुत लंबी बात है।"],
                            intel=[], tts=slow_tts)
    await sess.start()
    await asyncio.sleep(0.25)
    await sess.wait_idle()
    assert {"type": "stop_audio"} in out_json
    await sess.hangup()


async def test_stt_drop_reconnects(tmp_path):
    out_json, out_audio = [], []
    first = FakeStt([ev("transcript", "pehli baat suniye")], gap=0.01, end="close")
    second = FakeStt([ev("transcript", "dobara bolo madam")], gap=0.05)
    sess, *_ = make_session(tmp_path, out_json, out_audio, streams=[first, second],
                            dialogue=["हाँ बेटा।", "अच्छा।"], intel=[])
    await sess.start()
    await asyncio.sleep(0.3)
    await sess.wait_idle()
    statuses = [m.get("stt") for m in out_json if m.get("type") == "status"]
    assert "reconnecting" in statuses and statuses[-1] == "connected"
    assert [t["text"] for t in turns_of(out_json, "scammer")] == ["pehli baat suniye", "dobara bolo madam"]
    await sess.hangup()


async def test_auto_persona_switches_to_paati(tmp_path):
    out_json, out_audio = [], []
    stt = FakeStt([ev("transcript", "Madam naan bank manager pesuren", "ta-IN")], gap=0.01)
    sess, agent, _ = make_session(tmp_path, out_json, out_audio, streams=[stt], dialogue=["ஆமா ஆமா."], intel=[],
                                  persona="auto")
    await sess.start()
    await asyncio.sleep(0.1)
    await sess.wait_idle()
    assert any(m.get("type") == "persona" and m["persona"] == "paati" for m in out_json)
    assert agent.voice == PERSONAS["paati"].voice
    await sess.hangup()


def test_store_totals(tmp_path):
    st = Store(str(tmp_path / "d.db"))
    c = st.create_call("dadi")
    st.add_turn(c, Turn("scammer", "hi", 1.0))
    st.save_intel(c, IntelReport(upi_ids=["a@ybl"], phones=["9876543210"]))
    st.end_call(c, 125.0)
    assert st.totals() == {"calls": 1, "seconds_wasted": 125.0, "mule_ids": 2}
    assert st.get_call(c)["turns"][0]["text"] == "hi"
    assert st.get_call("missing") is None


async def test_speaking_flag_follows_playback_and_barge_in(tmp_path):
    out_json, out_audio = [], []
    sess, *_ = make_session(tmp_path, out_json, out_audio, streams=[FakeStt([])], dialogue=[], intel=[])
    assert not sess.speaking
    await sess._emit_audio(b"\x00\x00" * 4000)  # 0.5 s of audio at 8 kHz is now playing at the caller's end
    assert sess.speaking
    await sess._barge_in()
    assert not sess.speaking


def test_fallback_texts_are_prerenderable_fillers(tmp_path):
    store = Store(tmp_path / "fb.db")
    for key, p in PERSONAS.items():
        agent = DadiAgent(store=store, llm=FakeLLM([]), intel_llm=FakeLLM([]), persona_key=key, seed=1)
        fb = agent.fallback_texts()
        assert fb and set(fb) <= set(p.fillers), key


async def test_dadi_llm_failure_is_not_dead_air(tmp_path):
    out_json, out_audio = [], []

    class DeadLLM:
        async def stream(self, *a, **k):
            raise RuntimeError("Groq 429")
            yield ""  # pragma: no cover

    store = Store(tmp_path / "d.db")
    agent = DadiAgent(store=store, llm=DeadLLM(), intel_llm=FakeLLM([]), persona_key="dadi", seed=1)
    fillers = {t: b"\x00\x01" * 800 for t in PERSONAS["dadi"].fillers}

    async def sj(m):
        out_json.append(m)

    async def sa(b):
        out_audio.append(b)

    stt = FakeStt([ev("transcript", "Hello madam CBI se bol raha hoon")], gap=0.01)
    sess = VoiceAgentSession(agent, send_json=sj, send_audio=sa, settings=Settings(sample_rate=8000),
                             stt_factory=lambda: stt, tts_fn=fake_tts, filler_audio=fillers, rng=random.Random(0))
    await sess.start()
    await asyncio.sleep(0.1)
    await sess.wait_idle()
    dadi = turns_of(out_json, "dadi")
    assert len(dadi) == 2 and dadi[-1]["text"] in agent.fallback_texts() and dadi[-1].get("fallback")
    await sess.hangup()
