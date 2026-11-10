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


# --- 2. tactics: fake data only when asked, at most once per few turns -------------------------

def _play(lines, **state):
    import random

    from dadi.tactics import CallState, next_tactic
    st, rng, out = CallState(**state), random.Random(0), []
    for line in lines:
        st.last_scammer_text = line
        t = next_tactic(st, rng)
        st.recent_moves.append(t.move)
        st.turn += 1
        out.append(t)
    return out


def test_mentioning_aadhaar_or_account_is_not_a_request():
    for line in ("Aapka Aadhaar number drugs parcel se linked hai", "aapke account se money laundering hua hai",
                 "Aadhaar verify karna padega madam", "aapka Aadhaar link hai, jaldi paise bhejo"):
        assert _play([line], turn=5)[0].fake_field is None, line


def test_fake_field_needs_a_request_word_in_any_persona_language():
    for line, want in (("OTP batao jaldi", "otp"), ("aapka account freeze hoga, OTP bataiye", "otp"),
                       ("Aadhaar card ki photo bhejiye", "aadhaar"), ("tell me your card number", "card"),
                       ("aapka account number kya hai", "account"), ("ओटीपी बताइए", "otp"),
                       ("OTP sollunga paati", "otp"), ("OTP-ta bolun", "otp"), ("ಆಧಾರ್ ನಂಬರ್ ಹೇಳಿ", "aadhaar"),
                       ("OTP cheppandi", "otp"), ("अब OTP दो", "otp")):
        assert _play([line], turn=5)[0].fake_field == want, line


def test_scammer_nagging_for_otp_does_not_block_extraction():
    lines = ["Aapka Aadhaar number drugs parcel se linked hai", "Aadhaar verify karna padega madam",
             "aapka account freeze hoga, OTP bataiye", "Aadhaar card ki photo bhejiye",
             "aapke account se money laundering hua hai", "OTP aaya hoga, jaldi bataiye"] * 2
    tactics = _play(lines)
    moves = [t.move for t in tactics]
    assert sum(m.startswith("ask_") for m in moves) >= 3, moves
    served = [(i, t.fake_field) for i, t in enumerate(tactics) if t.fake_field]
    assert served, moves
    for f in {f for _, f in served}:  # the same fake field is read out at most once every 4 turns
        turns = [i for i, g in served if g == f]
        assert all(b - a >= 4 for a, b in zip(turns, turns[1:])), served


def test_repeated_otp_request_is_served_again_after_cooldown():
    tactics = _play(["OTP batao"] * 6, turn=4)
    assert [t.fake_field for t in tactics] == ["otp", None, None, None, "otp", None]
    assert tactics[0].move == "slow_digits" and tactics[2].move.startswith("ask_")  # turn 6: extract phase


# --- 3. the deliberate "slip" is precomputed and still provably invalid ------------------------

def test_fake_slips_are_one_digit_off_and_still_invalid():
    from dadi.fakes import fake_wallet, luhn_valid, verhoeff_valid
    for seed in range(300):
        w = fake_wallet(seed)
        for f in ("card", "aadhaar", "otp", "account"):
            good, slip = w[f], w[f + "_slip"]
            assert len(slip) == len(good) and sum(a != b for a, b in zip(good, slip)) == 1, (seed, f)
        assert not luhn_valid(w["card_slip"]) and not luhn_valid(w["card"])
        assert w["aadhaar_slip"][0] in "01" and not verhoeff_valid(w["aadhaar_slip"])


def test_prompt_gives_exact_slip_and_correction_instead_of_free_form_mistake():
    from dadi.brain import system_prompt
    from dadi.fakes import fake_wallet
    from dadi.personas import PERSONAS
    from dadi.tactics import Tactic
    w = fake_wallet(7)
    t = Tactic(phase="stall_pay", move="slow_digits", instruction="read slowly", fake_field="card")
    sp = system_prompt(PERSONAS["dadi"], t, w)
    assert w["card_slip"] in sp and w["card"] in sp
    assert sp.index(w["card_slip"]) < sp.index(w["card"])  # slip first, correction only if he complains
    assert "digit wrong" not in sp and "one mistake" not in _play(["OTP batao"], turn=5)[0].instruction


# --- 4. regex false positives ------------------------------------------------------------------

def test_amount_regex_needs_a_digit_and_a_whole_word_rs():
    for text in ("CBI officers, aapke ghar aa rahe hain", "aapke paas sirf 2 hours 24 minute hain",
                 "Madam, rupees transfer kijiye"):
        assert find_entities(text)["amounts"] == [], text
    e = find_entities("Rs. 500 aur INR 2000 aur 750 rs aur ₹25,000 aur 5 lakh, nau sau assi रुपये")
    assert e["amounts"] == ["Rs. 500", "INR 2000", "750 rs", "₹25,000", "5 lakh"]


def test_at_the_rate_of_only_becomes_at_before_a_handle():
    assert find_entities("loan at the rate of interest milega")["upi_ids"] == []
    assert find_entities("vijay99 at the rate of ok sbi pe bhejo")["upi_ids"] == ["vijay99@oksbi"]
    assert find_entities("ramesh.k at the rate of ybl")["upi_ids"] == ["ramesh.k@ybl"]
    assert find_entities("bhejo vijay99 at the rate ok sbi")["upi_ids"] == ["vijay99@oksbi"]


# --- 5. LLM phone/account formats are normalised ------------------------------------------------

def test_merge_intel_normalises_phone_and_account_formats():
    from dadi.intel import merge_intel
    rx = IntelReport(phones=["9876543210"], validated={"phones": ["9876543210"]})
    llm = IntelReport(phones=["98765 43210", "+91 98765 43210", "098765-43210"], accounts=["1234 5678 9012"])
    m = merge_intel(rx, llm)
    assert m.phones == ["9876543210"] and m.accounts == ["123456789012"]
    assert m.validated == {"phones": ["9876543210"]}
    m2 = merge_intel(m, IntelReport(accounts=["123456789012"], phones=["9876543210"]))
    assert m2.phones == ["9876543210"] and m2.accounts == ["123456789012"]


def test_sanitise_classifies_llm_numbers_with_the_regex_rules():
    from dadi.intel import _sanitise
    r = _sanitise({"accounts": ["98765 43210"], "phones": ["1234 5678 9012", "+91-91234-56789"]})
    assert sorted(r.phones) == ["9123456789", "9876543210"]
    assert r.accounts == ["123456789012"]
