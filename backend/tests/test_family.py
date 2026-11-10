"""Family hand-off: Dadi passes the phone to her grandson Bunty once per call, then he hands it back."""

import asyncio
import random
import re

from voice_core.config import Settings
from voice_core.session import VoiceAgentSession
from voice_core.testing import FakeLLM, FakeStt, ev
from voice_core.types import Turn

from dadi.agent import DadiAgent
from dadi.brain import system_prompt
from dadi.fakes import fake_wallet
from dadi.personas import BUNTY, FAMILY, HANDBACK_LINES, HANDOFF_LINES, PERSONAS
from dadi.report import build_report
from dadi.intel import IntelReport
from dadi.store import Store
from dadi.tactics import BUNTY_TURNS, HANDOFF_LATEST_TURN, HANDOFF_MIN_TURN, CallState, family_step, pressure

CALM = "Namaste madam, main bank se bol raha hoon, aapka KYC update hai."
PUSH = "Abhi 5000 rupees transfer karo warna arrest ho jayega, payment jaldi karo."
SPELL = "Mera UPI ID hai sbi.officer@ybl, likh lo, payment karo."


def make_agent(tmp_path, replies=None, persona="dadi", family=True):
    store = Store(tmp_path / "f.db")
    llm = FakeLLM(replies if replies is not None else [f"जवाब नंबर {i}।" for i in range(40)])
    agent = DadiAgent(store=store, llm=llm, intel_llm=FakeLLM([]), persona_key=persona, seed=3)
    agent.family = family
    return agent, llm


async def say(agent, history, text):
    """One scammer line -> (sentences with the voice each one was spoken in, turn_meta)."""
    history.append(Turn("scammer", text, float(len(history))))
    out = []
    async for s in agent.reply_sentences(list(history)):
        out.append((s, agent.voice, agent.speed))
    history.append(Turn("dadi", " ".join(s for s, _, _ in out), float(len(history))))
    return out, agent.turn_meta()


def test_bunty_persona_is_a_young_male_timbre_voice_not_a_scammer_voice():
    assert BUNTY.age == 19 and BUNTY.city == "Kanpur" and BUNTY.language == "hi-IN"
    assert BUNTY.voice in {"Devansh", "Shubham"} and abs(BUNTY.speed - 1.05) < 1e-9
    assert BUNTY.voice not in {"Harshad", "Avinash", "Yashraj"}  # the arena's scammer voices
    assert FAMILY == {"dadi": BUNTY} and "bunty" not in PERSONAS  # not a selectable grandmother
    assert len(BUNTY.fillers) == 2
    assert [w for w, _ in HANDOFF_LINES] == ["dadi", "bunty"] and [w for w, _ in HANDBACK_LINES] == ["bunty", "dadi"]


def test_pressure_detects_payment_demands_and_threats():
    assert pressure(PUSH) and pressure("आपके नाम पर वारंट है") and pressure("Pay ₹2000 fine now")
    assert not pressure(CALM) and not pressure("") and not pressure("aap kaisi hain amma ji")


def test_family_step_waits_for_turn_and_pressure_and_fires_once():
    st = CallState(turn=HANDOFF_MIN_TURN - 1, last_scammer_text=PUSH)
    assert family_step(st) is None  # too early, even under pressure
    st.turn = HANDOFF_MIN_TURN
    st.last_scammer_text = CALM
    assert family_step(st) is None  # no pressure yet
    st.last_scammer_text = PUSH
    assert family_step(st) == "handoff"
    st.handoff_turn, st.bunty_left = st.turn, BUNTY_TURNS
    assert family_step(st) == "bunty"
    st.bunty_left = 0
    assert family_step(st) == "handback"
    st.handed_back = True
    assert family_step(st) is None  # once per call
    late = CallState(turn=HANDOFF_LATEST_TURN, last_scammer_text=CALM)
    assert family_step(late) == "handoff"  # the pressure never peaked: she still calls him in
    assert family_step(CallState(turn=9, last_scammer_text=PUSH, family=False)) is None


async def test_handoff_then_n_bunty_turns_then_handback_with_voices(tmp_path):
    agent, llm = make_agent(tmp_path)
    h: list[Turn] = []
    for _ in range(HANDOFF_MIN_TURN):
        out, meta = await say(agent, h, CALM)
        assert meta["speaker_persona"] == "dadi" and "family" not in meta
        assert all(v == "Lakshmi" for _, v, _ in out)
    llm_calls = len(llm.calls)
    out, meta = await say(agent, h, PUSH)
    assert [s for s, _, _ in out] == [HANDOFF_LINES[0][1], HANDOFF_LINES[1][1]]
    assert [v for _, v, _ in out] == ["Lakshmi", BUNTY.voice]  # each sentence in its speaker's voice
    assert [sp for _, _, sp in out] == [PERSONAS["dadi"].speed, 1.05]
    assert meta["family"] == "handoff" and meta["tactic"] == "handoff" and meta["speaker_persona"] == "bunty"
    assert [s["persona"] for s in meta["segments"]] == ["dadi", "bunty"]
    assert len(llm.calls) == llm_calls  # fixed lines: no LLM call, instant
    assert agent.filler_texts() == BUNTY.fillers  # thinking fillers now in Bunty's voice
    for _ in range(BUNTY_TURNS):
        out, meta = await say(agent, h, SPELL)
        assert out and all(v == BUNTY.voice for _, v, _ in out)
        assert meta["speaker_persona"] == "bunty" and meta["speaker_name"] == "Bunty" and meta["phase"] == "bunty"
        assert "You are Bunty, 19, from Kanpur" in llm.calls[-1][0]["content"]  # his prompt, not Dadi's
    out, meta = await say(agent, h, PUSH)
    assert [s for s, _, _ in out] == [HANDBACK_LINES[0][1], HANDBACK_LINES[1][1]]
    assert [v for _, v, _ in out] == [BUNTY.voice, "Lakshmi"]
    assert meta["family"] == "handback" and meta["speaker_persona"] == "dadi"
    for _ in range(6):  # never again in this call, however hard he pushes
        out, meta = await say(agent, h, PUSH)
        assert "family" not in meta and meta["speaker_persona"] == "dadi"
        assert all(v == "Lakshmi" for _, v, _ in out)
        assert "You are Kamla Devi" in llm.calls[-1][0]["content"]
    moves = agent.state.recent_moves
    assert moves.count("handoff") == 1 and moves.count("handback") == 1


async def test_family_switch_off_keeps_dadi_on_the_phone(tmp_path):
    agent, llm = make_agent(tmp_path, family=False)
    h: list[Turn] = []
    for _ in range(HANDOFF_LATEST_TURN + 3):
        out, meta = await say(agent, h, PUSH)
        assert "family" not in meta and meta["speaker_persona"] == "dadi"
        assert all(v == "Lakshmi" for _, v, _ in out)
    assert all("You are Bunty" not in c[0]["content"] for c in llm.calls)


async def test_other_grandmothers_have_no_handoff(tmp_path):
    agent, _ = make_agent(tmp_path, persona="paati")
    h: list[Turn] = []
    for _ in range(HANDOFF_LATEST_TURN + 2):
        _, meta = await say(agent, h, PUSH)
        assert "family" not in meta and meta["speaker_persona"] == "paati"


async def test_bunty_uses_only_the_fake_wallet_with_slip_rules(tmp_path):
    agent, llm = make_agent(tmp_path)
    h: list[Turn] = []
    for _ in range(HANDOFF_MIN_TURN):
        await say(agent, h, CALM)
    await say(agent, h, PUSH)  # hand-off
    await say(agent, h, "Apna Aadhaar number bataiye jaldi.")
    prompt = llm.calls[-1][0]["content"]
    wallet = fake_wallet(agent.seed)
    assert "You are Bunty" in prompt and "FAKE" in prompt
    assert wallet["aadhaar"] in prompt and wallet["aadhaar_slip"] in prompt  # same provably invalid fakes as Dadi
    assert agent.bunty_brain.wallet == agent.brain.wallet
    assert "Never say you are an AI" in prompt and "never make up digits" in prompt


def test_bunty_prompt_stays_in_character():
    from dadi.tactics import Tactic

    p = system_prompt(BUNTY, Tactic("bunty", "spell_upi", "Ask him to spell it."), {})
    assert "You are Bunty, 19, from Kanpur" in p and "Never say you are an AI or a bot" in p
    assert "tired old person" not in p and "Warm, slow" not in p


async def test_intel_continues_across_the_handoff(tmp_path):
    agent, _ = make_agent(tmp_path)
    h: list[Turn] = []
    for _ in range(HANDOFF_MIN_TURN):
        await say(agent, h, CALM)
        await agent.on_user_turn(h)
    await say(agent, h, PUSH)
    h.append(Turn("scammer", SPELL, 99.0))
    data = await agent.on_user_turn(h)  # Bunty is on the phone now
    assert "sbi.officer@ybl" in data["intel"]["upi_ids"]
    await say(agent, h, "Account number 123456789012 IFSC SBIN0001234 mein bhejo.")
    data = await agent.on_user_turn(h)
    assert "sbi.officer@ybl" in data["intel"]["upi_ids"] and data["intel"]["accounts"]


async def test_persona_never_says_ai_in_fixed_lines():
    for _, text in (*HANDOFF_LINES, *HANDBACK_LINES, *[("bunty", f) for f in BUNTY.fillers]):
        assert not re.search(r"\b(?:AI|bot|robot|assistant)\b", text, re.I)


def test_report_credits_both_after_a_handoff():
    call = {"id": "c1", "persona": "dadi", "started_at": 0, "ended_at": 120}
    turns = [Turn("scammer", PUSH, 1.0), Turn("dadi", " ".join(t for _, t in HANDOFF_LINES), 2.0)]
    rep = build_report(call, turns, IntelReport())
    assert rep["decoys"] == ["Kamla Devi", "Bunty"] and "grandson 'Bunty'" in rep["summary"]
    rep = build_report(call, turns[:1], IntelReport())
    assert rep["decoys"] == ["Kamla Devi"] and "Bunty" not in rep["summary"]


async def test_session_voices_each_sentence_and_plays_prerendered_handoff(tmp_path):
    """Through VoiceAgentSession: the voice passed to TTS follows the speaker; cached hand-off lines skip TTS."""
    store = Store(tmp_path / "s.db")
    agent = DadiAgent(store=store, llm=FakeLLM([f"ठीक है {i}।" for i in range(20)]), intel_llm=FakeLLM([]),
                      persona_key="dadi", seed=3)
    tts_calls: list[tuple[str, str]] = []

    async def rec_tts(key, text, **kw):
        tts_calls.append((text, kw["voice"]))
        await asyncio.sleep(0)
        yield b"\x00\x01" * 160

    out_json: list[dict] = []

    async def sj(m):
        out_json.append(m)

    async def sa(b):
        pass

    lines = [CALM] * HANDOFF_MIN_TURN + [PUSH] + [SPELL] * BUNTY_TURNS + [PUSH, CALM]
    stt = FakeStt([ev("connected"), *[ev("transcript", t + f" {i}", "hi-IN") for i, t in enumerate(lines)]], gap=0.15)
    handoff_text = HANDOFF_LINES[1][1]
    fillers = {handoff_text: b"\x00\x02" * 400, HANDBACK_LINES[0][1]: b"\x00\x02" * 400}
    sess = VoiceAgentSession(agent, send_json=sj, send_audio=sa, settings=Settings(sample_rate=8000),
                             stt_factory=lambda: stt, tts_fn=rec_tts, rng=random.Random(0), filler_audio=fillers,
                             filler_delay=5.0)
    await sess.start()
    await asyncio.sleep(0.15 * (len(lines) + 2))
    await sess.wait_idle()
    await sess.hangup()
    voices = {text: v for text, v in tts_calls}
    assert voices[HANDOFF_LINES[0][1]] == "Lakshmi" and voices[HANDBACK_LINES[1][1]] == "Lakshmi"
    assert handoff_text not in voices and HANDBACK_LINES[0][1] not in voices  # pre-rendered: no TTS request
    bunty_said = [v for t, v in tts_calls if v == BUNTY.voice]
    assert len(bunty_said) == BUNTY_TURNS  # his three LLM replies, in his voice
    dadi_turns = [m for m in out_json if m.get("type") == "turn" and m.get("speaker") == "dadi"]
    fam = [m.get("family") for m in dadi_turns if m.get("family")]
    assert fam == ["handoff", "handback"]
    assert [m.get("speaker_persona") for m in dadi_turns].count("bunty") == BUNTY_TURNS + 1
