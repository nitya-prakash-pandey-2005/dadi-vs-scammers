import json
import random

from voice_core.testing import FakeLLM

from dadi.checker import check_message, verdict

MSG = ("CBI Mumbai: aapke Aadhaar se drugs parcel mila hai. Aap digital arrest mein hain, kisi ko mat batana. "
       "Turant 50,000 rupaye rathore.cbi@okaxis par bhejo.")


async def test_check_message_flags_scam_and_writes_dadi_reply():
    intel_llm = FakeLLM([json.dumps({
        "agencies_claimed": ["CBI Mumbai"], "scam_type": "digital_arrest", "scam_confidence": 0.95,
        "red_flags": [{"flag": "threat_of_arrest", "quote": "Aap digital arrest mein hain", "t": 0},
                      {"flag": "demands_secrecy", "quote": "kisi ko mat batana", "t": 0}]})])
    dadi_llm = FakeLLM(["<coughs> Beta, UPI ID dheere se phir likhna, chashma nahi mil raha."])
    r = await check_message(MSG, intel_llm=intel_llm, llm=dadi_llm, rng=random.Random(0))
    assert r["verdict"] == "scam" and r["scam_type"] == "digital_arrest"
    assert r["identifiers"]["upi_ids"] == ["rathore.cbi@okaxis"] and "50,000 rupaye" in r["identifiers"]["amounts"]
    assert "video call" in r["fact"] and r["persona"] == "dadi"
    assert r["dadi_reply"].startswith("Beta") and "<" not in r["dadi_reply"]
    assert "Text message" in dadi_llm.calls[0][0]["content"]


async def test_check_message_survives_llm_failure_and_picks_tamil_paati():
    r = await check_message("உங்கள் மின் இணைப்பு இன்று துண்டிக்கப்படும், OTP அனுப்புங்கள்",
                            intel_llm=FakeLLM(["not json"]), llm=FakeLLM([]), rng=random.Random(0))
    assert r["persona"] == "paati" and r["verdict"] in ("suspicious", "no_signs") and r["dadi_reply"] == ""


def test_verdict_rules():
    assert verdict(0.9, 0, False) == "scam" and verdict(0.1, 2, False) == "scam" and verdict(0.1, 1, True) == "scam"
    assert verdict(0.4, 0, False) == "suspicious" and verdict(0.1, 1, False) == "suspicious"
    assert verdict(0.0, 0, False) == "no_signs"


def test_link_risks_flags_lookalikes_and_spares_official_sites():
    from dadi.checker import link_risks
    r = link_risks(["sbi-kyc-update.top", "https://bit.ly/3xYz", "http://103.21.4.9/pay", "https://onlinesbi.sbi/login",
                    "https://uidai.gov.in"])
    assert [x["url"] for x in r] == ["sbi-kyc-update.top", "https://bit.ly/3xYz", "http://103.21.4.9/pay"]
    assert any("'sbi'" in w for w in r[0]["reasons"]) and any(".top" in w for w in r[0]["reasons"])


async def test_check_message_matches_ids_from_earlier_scam_calls():
    calls = [{"id": "c1", "intel": {"upi_ids": ["rathore.cbi@okaxis"]}}, {"id": "c2", "intel": {"upi_ids": ["x@ybl"]}}]
    r = await check_message(MSG, intel_llm=FakeLLM(["not json"]), llm=FakeLLM([]), rng=random.Random(0), calls=calls)
    assert r["seen_before"] == [{"id": "rathore.cbi@okaxis", "calls": ["c1"]}] and r["verdict"] == "scam"
