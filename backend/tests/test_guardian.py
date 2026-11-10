"""Guardian mode: risk rules, warnings once per level, the listen-only session, /ws/guard and web/backend parity."""

import asyncio
import json
import random
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from voice_core.config import Settings, repo_root
from voice_core.session import VoiceAgentSession
from voice_core.testing import FakeStt, ev, fake_tts

from dadi.app import create_app
from dadi.guardian import (RULES_PATH, GuardianAgent, RiskTracker, flags_in, level_for, load_rules, score_texts,
                           warning_text)

WEB_RULES = repo_root() / "frontend" / "src" / "lib" / "guardian-rules.json"
WEB_SCORER = repo_root() / "frontend" / "src" / "lib" / "guardian.js"
DEMO_CALL = repo_root() / "frontend" / "public" / "demo" / "ws-call.json"
LANGS = ("hi", "en", "ta", "bn", "kn", "te")


def recorded_caller_lines() -> list[str]:
    """The scammer's side of the real call recorded on Gnani's live servers (the web demo replays the same lines)."""
    rows = json.loads(DEMO_CALL.read_text(encoding="utf-8"))
    return [r["msg"]["text"] for r in rows if r["msg"].get("type") == "turn" and r["msg"].get("speaker") == "scammer"]


# ------------------------------------------------------------------ rules and scoring
def test_flags_and_weighted_explanations():
    assert [k for k, _ in flags_in("Main CBI headquarters se Inspector bol raha hoon")] == ["impersonates_authority"]
    assert flags_in("aap mujhe abhi bataiye kya hua") == []  # an ordinary sentence raises nothing
    assert flags_in("shopping pinky")[:1] == []  # ' pin ' is a whole word, not a substring of 'shopping'
    tr = RiskTracker()
    new = tr.add("Main CBI se bol raha hoon")
    assert tr.score == 30 and new[0]["text"] == "+30: claims to be police, CBI, bank or government"
    assert new[0]["heard"] == "cbi"
    tr.add("Main CBI se hi bol raha hoon")  # the same flag again adds nothing
    assert tr.score == 30 and len(tr.reasons) == 1


def test_diminishing_returns_and_reasons_sum_to_the_score():
    tr = RiskTracker()
    tr.add("CBI officer here, there is an arrest warrant")  # 30 + 30 -> 51, not 60
    assert tr.score == 51 and [r["points"] for r in tr.reasons] == [30, 21]
    tr.add("Install AnyDesk and tell me the OTP. Send money to the safe account, don't tell anyone, jaldi.")
    assert 90 <= tr.score < 100
    assert sum(r["points"] for r in tr.reasons) == tr.score
    pts = [r["points"] for r in tr.reasons]
    assert pts[2] < 35  # a 35-point flag adds less once the risk is already high


def test_payment_identifiers_raise_the_risk():
    assert ("payment_details", "upi") in flags_in("UPI ID likhiye: rathore.cbi@okaxis.")
    assert flags_in("pay to rathore.cbi@okaxis now") == [("payment_details", "rathore.cbi@okaxis")]
    assert [k for k, _ in flags_in("account 1234 5678 9012 3456 mein bhejo")] == ["payment_details"]
    assert flags_in("mera number 98765") == []  # a short number is not an account


def test_levels_and_thresholds():
    th = load_rules()["thresholds"]
    assert (th["caution"], th["stop"]) == (40, 70)
    assert [level_for(s) for s in (0, 39, 40, 69, 70, 100)] == ["safe", "safe", "caution", "caution", "stop", "stop"]


def test_recorded_live_call_rises_to_stop():
    steps = score_texts(recorded_caller_lines())
    scores = [s["score"] for s in steps]
    assert scores == sorted(scores) and scores[0] == 30
    assert steps[1]["level"] == "caution" and steps[-1]["level"] == "stop" and scores[-1] >= 85
    assert any("safe account" in r for r in steps[-1]["reasons"])


def test_warning_sets_per_language():
    rules = load_rules()
    assert set(rules["warnings"]) == set(LANGS) == set(rules["languages"])
    for lang in LANGS:
        caution, stop = warning_text(lang, "caution"), warning_text(lang, "stop")
        assert caution != stop and 10 < len(stop) < 140 and 10 < len(caution) < 140
        assert "CBI" in stop  # every stop line names the impostor
    assert warning_text("hi", "stop") == "रुकिए। CBI या पुलिस कभी फ़ोन पर पैसे नहीं माँगती। फ़ोन काट दीजिए।"
    assert warning_text("xx", "stop") == warning_text("hi", "stop")  # unknown language: Hindi


# ------------------------------------------------------------------ the agent
async def collect(agen):
    return [s async for s in agen]


async def test_agent_warns_once_per_level():
    from voice_core.types import Turn
    a = GuardianAgent(language="ta")
    assert a.greeting() == "" and a.filler_texts() == [] and a.fallback_texts() == []
    h = [Turn("caller", "Main CBI se bol raha hoon", 1.0)]
    assert await collect(a.reply_sentences(h)) == []  # 30: safe, silence
    h.append(Turn("caller", "aapke naam pe arrest warrant hai", 2.0))
    assert await collect(a.reply_sentences(h)) == [warning_text("ta", "caution")]
    assert a.turn_meta() == {"warning": True, "level": "caution"}
    h.append(Turn("caller", "arrest warrant phir se", 3.0))
    assert await collect(a.reply_sentences(h)) == []  # still caution: not again
    h.append(Turn("caller", "safe account mein paisa bhejo, kisi ko mat batana", 4.0))
    assert await collect(a.reply_sentences(h)) == [warning_text("ta", "stop")]
    h.append(Turn("caller", "AnyDesk install karo", 5.0))
    assert await collect(a.reply_sentences(h)) == []  # stop already said
    evt = await a.on_user_turn(h)
    assert evt["type"] == "risk" and evt["level"] == "stop" and len(evt["reasons"]) == 5
    assert a.tracker.turns == 5  # the reply and the analysis share one scoring pass per turn


async def test_jump_straight_to_stop_says_only_the_stop_warning():
    from voice_core.types import Turn
    a = GuardianAgent(language="en")
    h = [Turn("caller", "CBI here. Arrest warrant. Send money to a safe account now, don't tell anyone.", 1.0)]
    assert await collect(a.reply_sentences(h)) == [warning_text("en", "stop")]
    assert a.warned == ["caution", "stop"]


async def test_auto_language_follows_the_call():
    a = GuardianAgent(language="auto")
    assert a.on_language("bn-IN") == {"type": "guardian_language", "language": "bn"}
    assert a.tts_language == "bn-IN" and a.voice == "Chetana"
    assert GuardianAgent(language="hi").on_language("bn-IN") is None  # a chosen language stays


# ------------------------------------------------------------------ through VoiceAgentSession (fakes)
LINES = ["Main CBI se bol raha hoon", "aapke naam pe arrest warrant hai", "haan ji", "theek hai",
         "safe account mein paisa bhejo, kisi ko mat batana", "jaldi kariye"]


def guardian_session(out_json, out_audio, stt, *, filler_audio=None, language="hi"):
    agent = GuardianAgent(language=language)

    async def sj(m):
        out_json.append(m)

    async def sa(b):
        out_audio.append(b)

    sess = VoiceAgentSession(agent, send_json=sj, send_audio=sa, settings=Settings(sample_rate=8000),
                             stt_factory=lambda: stt, tts_fn=fake_tts, rng=random.Random(0), half_duplex=True,
                             filler_audio=filler_audio, first_sentence_timeout=None)
    return sess, agent


async def test_session_speaks_each_warning_once_and_nothing_else():
    out_json, out_audio = [], []
    events = [ev("connected")]
    for line in LINES:
        events += [ev("speech_start"), ev("processing"), ev("transcript", line, "hi-IN")]
    # a filler clip is available: a listen-only agent must still never play it (nor a fallback line)
    sess, agent = guardian_session(out_json, out_audio, FakeStt(events, gap=0.01), filler_audio={"हम्म": b"\x00" * 800})
    await sess.start()
    await asyncio.sleep(0.4)
    await sess.wait_idle()
    guardian = [m for m in out_json if m.get("type") == "turn" and m.get("speaker") == "guardian"]
    assert [m["text"] for m in guardian] == [warning_text("hi", "caution"), warning_text("hi", "stop")]
    assert [m["level"] for m in guardian] == ["caution", "stop"] and all(m.get("warning") for m in guardian)
    assert not any(m.get("fallback") for m in out_json)
    assert len(out_audio) == 4  # two fake TTS chunks per warning; no filler audio
    assert [m for m in out_json if m.get("type") == "stop_audio"] == []  # never cut off
    risks = [m for m in out_json if m.get("type") == "risk"]
    assert risks and risks[-1]["level"] == "stop" and risks[-1]["score"] >= 70
    assert len([m for m in out_json if m.get("type") == "turn" and m.get("speaker") == "caller"]) == len(LINES)
    on = [m for m in out_json if m.get("type") == "agent_speaking" and m["on"]]
    assert len(on) == 2  # speaking indicator only for the two warnings
    await sess.hangup()


async def test_warnings_queue_instead_of_interrupting():
    out_json, out_audio = [], []

    async def slow_tts(*a, **kw):
        async for c in fake_tts(chunk_delay=0.05):
            yield c

    events = [ev("connected"), ev("transcript", "CBI officer, arrest warrant", "en-IN"),
              ev("transcript", "safe account mein paisa bhejo, kisi ko mat batana", "en-IN")]
    sess, agent = guardian_session(out_json, out_audio, FakeStt(events, gap=0.01), language="en")
    sess.tts_fn = slow_tts
    await sess.start()
    await asyncio.sleep(0.05)
    await sess.wait_idle()
    spoken = [m["text"] for m in out_json if m.get("type") == "turn" and m.get("speaker") == "guardian"]
    assert spoken == [warning_text("en", "caution"), warning_text("en", "stop")]
    assert len(out_audio) == 4 and not [m for m in out_json if m.get("type") == "stop_audio"]
    await sess.hangup()


# ------------------------------------------------------------------ /ws/guard end to end
def test_ws_guard_end_to_end(tmp_path):
    settings = Settings(sample_rate=8000, cache_dir=tmp_path)
    events = [ev("connected")] + [ev("transcript", line, "hi-IN") for line in LINES]

    def factory(send_json, send_audio, language):
        agent = GuardianAgent(language=language)
        sess = VoiceAgentSession(agent, send_json=send_json, send_audio=send_audio, settings=settings,
                                 stt_factory=lambda: FakeStt(events, gap=0.02), tts_fn=fake_tts, half_duplex=True,
                                 first_sentence_timeout=None)
        return sess, agent

    app = create_app(settings, guard_factory=factory)
    got = []
    with TestClient(app) as c, c.websocket_connect("/ws/guard") as ws:
        ws.send_json({"type": "start", "language": "kn"})
        while True:
            m = ws.receive()
            if m.get("text"):
                d = json.loads(m["text"])
                got.append(d)
                if d["type"] == "warning" and d["level"] == "stop":
                    break
        ws.send_json({"type": "hangup"})
        while True:
            d = ws.receive_json()
            got.append(d)
            if d["type"] == "call_ended":
                break
    types = [d["type"] for d in got]
    assert types[0] == "session_started" and got[0]["mode"] == "guardian" and got[0]["language"] == "kn"
    warnings = [d for d in got if d["type"] == "warning"]
    assert [w["level"] for w in warnings] == ["caution", "stop"]
    assert warnings[1]["text"] == warning_text("kn", "stop")
    risk = [d for d in got if d["type"] == "risk"]
    assert risk and {"score", "level", "reasons"} <= set(risk[-1])
    assert got[-1]["level"] == "stop" and got[-1]["score"] >= 70


def texts_until(ws, kind: str) -> list[str]:
    """JSON message types received (audio frames skipped) up to and including the first `kind`."""
    seen = []
    while not seen or seen[-1] != kind:
        m = ws.receive()
        if m.get("text"):
            seen.append(json.loads(m["text"])["type"])
    return seen


def test_ws_guard_stores_nothing(tmp_path):
    settings = Settings(sample_rate=8000, cache_dir=tmp_path)
    events = [ev("connected"), ev("transcript", "CBI officer, arrest warrant", "en-IN")]

    def factory(send_json, send_audio, language):
        agent = GuardianAgent(language=language)
        sess = VoiceAgentSession(agent, send_json=send_json, send_audio=send_audio, settings=settings,
                                 stt_factory=lambda: FakeStt(events, gap=0.01), tts_fn=fake_tts, half_duplex=True)
        return sess, agent

    with TestClient(create_app(settings, guard_factory=factory)) as c:
        with c.websocket_connect("/ws/guard") as ws:
            ws.send_json({"type": "start", "language": "en"})
            assert "warning" in texts_until(ws, "warning")
            ws.send_json({"type": "hangup"})
            texts_until(ws, "call_ended")
        assert c.get("/api/calls").json() == []
    assert not (tmp_path / "recordings").exists()


def test_ws_guard_rejects_a_bad_first_message(tmp_path):
    with TestClient(create_app(Settings(sample_rate=8000, cache_dir=tmp_path))) as c:
        with c.websocket_connect("/ws/guard") as ws:
            ws.send_json({"type": "hello"})
            with pytest.raises(Exception):
                ws.receive_json()


# ------------------------------------------------------------------ web demo parity
def test_web_rules_are_the_backend_rules():
    assert json.loads(WEB_RULES.read_text(encoding="utf-8")) == json.loads(RULES_PATH.read_text(encoding="utf-8"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_web_scorer_gives_the_same_scores_as_python(tmp_path):
    lines = recorded_caller_lines() + LINES + [
        "Install AnyDesk and tell me the OTP", "account 1234 5678 9012 3456", "शॉपिंग pinky", "don't tell anyone",
        "আপনার নামে গ্রেফতার পরোয়ানা, পুলিশ বলছি", "ಪೊಲೀಸ್ ಅರೆಸ್ಟ್ ಮಾಡುತ್ತಾರೆ, ಒಟಿಪಿ ಹೇಳಿ"]
    script = tmp_path / "parity.mjs"
    script.write_text(
        "import { readFileSync } from 'node:fs';\n"
        f"import {{ scoreTexts }} from {json.dumps(WEB_SCORER.as_uri())};\n"
        f"const rules = JSON.parse(readFileSync({json.dumps(str(WEB_RULES))}, 'utf8'));\n"
        f"const lines = JSON.parse(readFileSync({json.dumps(str(tmp_path / 'lines.json'))}, 'utf8'));\n"
        "process.stdout.write(JSON.stringify(scoreTexts(lines, rules)));\n", encoding="utf-8")
    (tmp_path / "lines.json").write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    out = subprocess.run(["node", str(script)], capture_output=True, timeout=60, check=True)
    assert json.loads(out.stdout.decode("utf-8")) == score_texts(lines)
