import random

from voice_core.testing import FakeLLM
from voice_core.turns import split_sentences
from voice_core.types import Turn

from dadi.brain import DadiBrain, build_messages, clean_reply
from dadi.intel import IntelReport, extract_intel, merge_intel
from dadi.personas import PERSONAS
from dadi.report import build_report
from dadi.tactics import CallState, Tactic


def test_split_sentences():
    done, rest = split_sentences("हाँ बेटा। रुको ज़रा… चश्मा कहाँ है? मैं")
    assert done == ["हाँ बेटा।", "रुको ज़रा…", "चश्मा कहाँ है?"] and rest == "मैं"


def test_build_messages_includes_tactic_and_wallet():
    p = PERSONAS["dadi"]
    t = Tactic(phase="stall_pay", move="slow_digits", instruction="read slowly", fake_field="otp")
    msgs = build_messages(p, t, [Turn("scammer", "OTP batao", 3.0)], {"otp": "104729"})
    sys = msgs[0]["content"]
    assert "Kamla" in sys and "read slowly" in sys and "104729" in sys
    assert msgs[-1] == {"role": "user", "content": "OTP batao"}


def test_build_messages_maps_roles_and_limits_history():
    p = PERSONAS["dadi"]
    t = Tactic(phase="confused", move="mishear", instruction="x")
    hist = [Turn("scammer" if i % 2 == 0 else "dadi", f"line {i}", float(i)) for i in range(30)]
    msgs = build_messages(p, t, hist, {})
    assert len(msgs) == 1 + 12
    assert msgs[-1]["role"] == "assistant" and msgs[-2]["role"] == "user"


def test_clean_reply_removes_stage_directions_and_unknown_tags():
    assert clean_reply("Dadi: हाँ बेटा <laugh> (smiles) <dance> ठीक है") == "हाँ बेटा <laugh> ठीक है"


async def test_brain_yields_sentences_and_records_move():
    brain = DadiBrain(FakeLLM(["हाँ बेटा। <coughs> रुको ज़रा, चश्मा ढूँढ रही हूँ।"]), PERSONAS["dadi"], seed=1)
    st = CallState()
    out = [s async for s in brain.reply_sentences([Turn("scammer", "Main CBI se", 1.0)], st, random.Random(0))]
    assert out == ["हाँ बेटा।", "<coughs> रुको ज़रा, चश्मा ढूँढ रही हूँ।"]
    assert len(st.recent_moves) == 1 and st.turn == 1


async def test_extract_intel_survives_bad_json():
    prev = IntelReport(upi_ids=["a@okaxis"])
    out = await extract_intel(FakeLLM(["not json"]), [Turn("scammer", "send to b.kumar@ybl now", 5.0)], prev)
    assert set(out.upi_ids) == {"a@okaxis", "b.kumar@ybl"}


async def test_extract_intel_parses_llm_json():
    js = ('{"scam_type":"digital_arrest","scam_confidence":0.9,"names":["Vijay Kumar"],"agencies_claimed":["CBI"],'
          '"red_flags":[{"flag":"threat_of_arrest","quote":"aapko arrest karenge","t":4.0},{"flag":"made_up","quote":"x","t":1}]}')
    out = await extract_intel(
        FakeLLM([js]), [Turn("scammer", "Main CBI se Vijay Kumar, aapko arrest karenge", 4.0)], IntelReport()
    )
    assert out.scam_type == "digital_arrest" and [f.flag for f in out.red_flags] == ["threat_of_arrest"]
    assert out.names == ["Vijay Kumar"] and out.agencies_claimed == ["CBI"]


def test_merge_intel_keeps_best_type_and_dedupes():
    a = IntelReport(upi_ids=["X@ybl"], scam_type="kyc_bank_block", scam_confidence=0.4)
    b = IntelReport(upi_ids=["x@ybl", "y@okaxis"], scam_type="digital_arrest", scam_confidence=0.8)
    m = merge_intel(a, b)
    assert m.upi_ids == ["X@ybl", "y@okaxis"] and m.scam_type == "digital_arrest"


def test_report_has_disclaimer_and_identifiers():
    r = build_report({"id": "c1", "started_at": 0, "ended_at": 125, "persona": "dadi"},
                     [Turn("scammer", "hi", 0.0)], IntelReport(upi_ids=["x@ybl"]))
    assert "Simulated" in r["disclaimer"] and r["suspect_identifiers"] == {"upi_ids": ["x@ybl"]}
    assert r["duration_seconds"] == 125 and "cybercrime.gov.in" in r["where_to_report"]
    ch = build_report({"id": "c1", "started_at": 0, "persona": "dadi"}, [],
                      IntelReport(scam_type="digital_arrest", upi_ids=["x@ybl"]))["chakshu"]
    assert ch["medium"] == "Call" and "Impersonation" in ch["category"] and "x@ybl" in ch["description"]


def test_sanitise_drops_malformed_llm_identifiers():
    from dadi.intel import _sanitise
    r = _sanitise({"accounts": ["99087565", "624655", "1234 5678 9012"], "phones": ["99887", "+91 98765 43210"],
                   "upi_ids": ["bijli office", "rathore.cbi@okax.in"], "amounts": ["990875", "₹980", "5 lakh"]})
    assert r.accounts == ["123456789012"] and r.phones == ["9876543210"]
    assert r.upi_ids == ["rathore.cbi@okaxis"] and r.amounts == ["₹980", "5 lakh"]


def test_system_prompt_pins_the_persona_language():
    from dadi.brain import system_prompt
    t = Tactic(phase="confused", move="glasses", instruction="x")
    for key, lang, sample in (("ajji", "Kannada", "ಯಾರಪ್ಪ"), ("ammamma", "Telugu", "నాయనా"), ("dadi", "Hinglish", "बेटा")):
        sp = system_prompt(PERSONAS[key], t, {})
        assert f"always reply in {lang}" in sp and sample in sp and "<coughs>" not in sp.split("Example")[1].split("\n")[0]
