import random

from dadi.fakes import fake_aadhaar, fake_card, fake_otp, fake_wallet, luhn_valid, verhoeff_valid
from dadi.intel_rules import find_entities
from dadi.numwords import words_to_digits
from dadi.personas import PERSONAS, persona_for_language
from dadi.tactics import CallState, next_tactic
from dadi.taxonomy import RED_FLAGS, SCAM_KEYTERMS, SCAM_TYPES


def test_fakes_are_provably_invalid():
    for s in range(50):
        c = fake_card(s)
        assert len(c) == 16 and c.isdigit() and not luhn_valid(c)
        a = fake_aadhaar(s)
        assert a[0] in "01" and len(a) == 12 and not verhoeff_valid(a)
        assert len(fake_otp(s)) == 6
    assert luhn_valid("4111111111111111") and verhoeff_valid("2363")
    w = fake_wallet(3)
    assert {"card", "aadhaar", "otp", "account", "bank", "balance"} <= set(w)


def test_words_to_digits_hinglish():
    assert words_to_digits("nau aath saat chhe paanch chaar teen do ek shunya") == "9876543210"
    assert words_to_digits("double five triple nine") == "55999"
    assert words_to_digits("नौ आठ सात") == "987"
    assert words_to_digits("UPI ID do jaldi") == "UPI ID do jaldi"  # lone "do" (= give) untouched
    assert words_to_digits("number ९८७ hai") == "number 987 hai"


def test_find_entities():
    e = find_entities(
        "UPI ID hai ramesh.kumar@okaxis aur number nau aath saat chhe paanch chaar teen do ek shunya, "
        "AnyDesk install karo, IFSC SBIN0001234"
    )
    assert e["upi_ids"] == ["ramesh.kumar@okaxis"] and e["phones"] == ["9876543210"]
    assert e["ifsc"] == ["SBIN0001234"] and e["apps"] == ["AnyDesk"]


def test_find_entities_grouped_digits_and_email_not_upi():
    e = find_entities("call 98765 43210 or +91 91234 56789, mail me at boss@gmail.com, account 1234 5678 9012")
    assert e["phones"] == ["9876543210", "9123456789"]
    assert e["upi_ids"] == []
    assert e["accounts"] == ["123456789012"]


def test_hindi_compound_numbers_from_prisma():
    # live arena, 8 Nov: "99887 76655" came back as Hindi number words
    e = find_entities("Suresh निन्यानवे हज़ार आठ सौ सत्तासी, छिहत्तर हज़ार छह सौ पचपन, अब OTP दो")
    assert e["phones"] == ["9988776655"]
    assert find_entities("नंबर लिखो निन्यानवे अट्ठासी सतहत्तर छियासठ पचपन")["phones"] == ["9988776655"]
    assert words_to_digits("नौ सौ अस्सी रुपये भेजो") == "980 रुपये भेजो"
    assert find_entities("नौ सौ अस्सी रुपये भेजो")["amounts"] == ["980 रुपये"]
    assert words_to_digits("दो लाख पचास हजार") == "250000"
    assert words_to_digits("एक मिनट रुको, दो मिनट") == "एक मिनट रुको, दो मिनट"


def test_find_entities_repairs_misheard_upi_handles():
    # Prisma at 10 dB heard "@okaxis" as "@okax.in" (live arena, 8 Nov)
    assert find_entities("transfer kar do rathore.cbi@okax.in")["upi_ids"] == ["rathore.cbi@okaxis"]
    assert find_entities("bhejo vijay99 at the rate ok sbi")["upi_ids"] == ["vijay99@oksbi"]
    assert find_entities("turant bijli.office@pa। A white")["upi_ids"] == ["bijli.office@paytm"]  # cut short
    assert find_entities("vijay@ok pe bhejo")["upi_ids"] == ["vijay@ok"]  # ambiguous prefix: left alone
    e = find_entities("mail boss@gmail.com, site fedex-help.in")
    assert e["upi_ids"] == [] and "fedex-help.in" in e["urls"]


def test_find_entities_amounts_and_apps_variants():
    e = find_entities("Team Viewer download karo aur ₹25,000 bhejo, nahi to 5 lakh fine")
    assert e["apps"] == ["TeamViewer"]
    assert "₹25,000" in e["amounts"] and "5 lakh" in e["amounts"]


def test_tactics_progress_and_fake_field():
    rng = random.Random(0)
    st = CallState()
    assert next_tactic(st, rng).phase == "confused"
    st.turn = 6
    st.last_scammer_text = "OTP batao jaldi"
    t = next_tactic(st, rng)
    assert t.fake_field == "otp" and t.move == "slow_digits"
    st.turn = 7
    st.last_scammer_text = ""
    st.captured = {"upi_ids"}
    assert next_tactic(st, rng).phase == "loop"


def test_moves_do_not_repeat_within_three():
    rng = random.Random(1)
    st = CallState(turn=4)
    for _ in range(12):
        t = next_tactic(st, rng)
        assert t.move not in st.recent_moves[-3:]
        assert t.instruction
        st.recent_moves.append(t.move)
        st.turn += 1


def test_personas_and_language():
    assert set(PERSONAS) == {"dadi", "paati", "thakuma"}
    for p in PERSONAS.values():
        assert len(p.fillers) >= 6 and p.greeting and p.voice
    assert persona_for_language("ta-IN").key == "paati"
    assert persona_for_language("bn-IN").key == "thakuma"
    assert persona_for_language(None).key == "dadi"


def test_taxonomy():
    assert "digital_arrest" in SCAM_TYPES and "other" in SCAM_TYPES
    assert "threat_of_arrest" in RED_FLAGS
    assert 10 <= len(SCAM_KEYTERMS) <= 40


def test_mission_steers_tactics_until_done():
    from dadi.tactics import MISSIONS, mission_done
    rng = random.Random(0)
    st = CallState(mission="account")
    moves = []
    for _ in range(8):
        t = next_tactic(st, rng)
        moves.append(t.move)
        st.recent_moves.append(t.move)
        st.turn += 1
    assert moves.count("ask_account_ifsc") >= 3 and moves[0] != "ask_account_ifsc"  # still confused at first
    assert "account" in MISSIONS and mission_done("account", {"accounts": ["123456789012"]})
    assert not mission_done("identity", {"upi_ids": ["a@ybl"]}) and mission_done("identity", {"names": ["Rahul"]})
