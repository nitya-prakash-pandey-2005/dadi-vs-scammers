"""Regression tests for the 10 Nov domain-logic review (number merging, tactics, fake slips, regex, LLM IDs)."""

from voice_core.testing import FakeLLM
from voice_core.types import Turn

from dadi.intel import IntelReport, extract_intel
from dadi.intel_rules import find_entities
from dadi.numwords import words_to_digits


def _ids(text: str) -> dict:
    e = find_entities(text)
    return {"phones": e["phones"], "accounts": e["accounts"]}


# --- 1. number merging -------------------------------------------------------------------------

def test_amount_next_to_phone_does_not_swallow_the_phone():
    assert _ids("total 50000 9876543210 pe GPay karo") == {"phones": ["9876543210"], "accounts": []}
    assert _ids("दस हज़ार 9876543210 पर भेजो") == {"phones": ["9876543210"], "accounts": []}
    assert _ids("mera badge number 4521 9876543210 pe call karo") == {"phones": ["9876543210"], "accounts": []}
    # a spoken round amount next to a phone read out in 5-digit groups
    assert _ids("दस हज़ार 98765 43210 पर भेजो") == {"phones": ["9876543210"], "accounts": []}
    assert _ids("total 50000 98765 43210 pe GPay karo") == {"phones": ["9876543210"], "accounts": []}
    assert _ids("badge 4521 98765 43210") == {"phones": ["9876543210"], "accounts": []}


def test_phone_split_unevenly_is_still_joined():
    assert _ids("number 987654 3210 hai") == {"phones": ["9876543210"], "accounts": []}
    assert _ids("nine eight 76543210") == {"phones": ["9876543210"], "accounts": []}
    assert _ids("+91 98765 43210") == {"phones": ["9876543210"], "accounts": []}


def test_multiplier_amounts_are_never_accounts():
    assert _ids("दस करोड़ का case है") == {"phones": [], "accounts": []}
    assert _ids("दस हज़ार, बीस हज़ार लगेंगे") == {"phones": [], "accounts": []}
    assert _ids("fine 100000000 lagega") == {"phones": [], "accounts": []}  # 10 crore said as digits
    assert words_to_digits("बीस पच्चीस हज़ार लगेंगे") == "20 25000 लगेंगे"  # 20-25 thousand, not 45000


def test_precomposed_nukta_is_parsed():
    assert words_to_digits("पांच हज़ार") == "5000"  # हज़ार with U+095B
    assert words_to_digits("दो करोड़") == "20000000"  # करोड़ with U+095C


def test_spoken_numbers_still_work():
    e = find_entities("Suresh निन्यानवे हज़ार आठ सौ सत्तासी, छिहत्तर हज़ार छह सौ पचपन, अब OTP दो")
    assert e["phones"] == ["9988776655"] and e["accounts"] == []
    assert words_to_digits("एक बात सुनिए, दो मिनट रुकिए, सौ बार बोला") == "एक बात सुनिए, दो मिनट रुकिए, सौ बार बोला"
    assert words_to_digits("nau aath saat chhe paanch chaar teen do ek shunya") == "9876543210"
    assert words_to_digits("double five triple nine") == "55999"
    assert _ids("account 1234 5678 9012") == {"phones": [], "accounts": ["123456789012"]}
    assert _ids("call 98765 43210") == {"phones": ["9876543210"], "accounts": []}


def test_turn_boundaries_are_kept():
    assert _ids("Fine amount hai 50000 \n 98765 43210 pe GPay kar dijiye") == {"phones": ["9876543210"], "accounts": []}


async def test_extract_intel_does_not_merge_numbers_across_turns():
    hist = [Turn("scammer", "Fine amount hai 50000", 3.0), Turn("dadi", "हाय राम", 5.0),
            Turn("scammer", "9876543210 pe GPay kar dijiye", 9.0)]
    out = await extract_intel(FakeLLM(["not json"]), hist, IntelReport())
    assert out.phones == ["9876543210"] and out.accounts == []
    assert out.validated.get("phones") == ["9876543210"] and "accounts" not in out.validated
