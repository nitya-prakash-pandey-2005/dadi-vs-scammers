"""Turn spoken digits ("nau aath saat", "double five", "नौ आठ", "rendu moonu") into ASCII digits.

Only runs of two or more digit tokens are converted, so a lone "do" (Hindi "give") or "ek"
("one" as in "ek minute") stays a word. Native-script numerals (०-९, ০-৯) are always converted.

Spoken digits are joined into one number; numbers already written as numerals stay separate groups, and
`intel_rules.find_entities` decides which groups form one phone/account, so an amount said next to a phone
("50000 9876543210") never swallows it. A number built with सौ/हज़ार/लाख/करोड़ that is round or in lakhs
(दस हज़ार, दस करोड़) is an amount: `words_to_digits(..., mask_amounts=True)` hides it from identifier extraction.
"""

from __future__ import annotations

import re
import unicodedata

_WORDS = {
    # English
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9",
    # Hindi / Hinglish (romanised)
    "shunya": "0", "shoonya": "0", "sunya": "0", "ek": "1", "do": "2", "teen": "3", "tin": "3",
    "char": "4", "chaar": "4", "paanch": "5", "panch": "5", "paach": "5", "chhe": "6", "che": "6",
    "chah": "6", "chhah": "6", "chhah": "6", "saat": "7", "sat": "7", "aath": "8", "aat": "8", "nau": "9",
    # Devanagari
    "शून्य": "0", "ज़ीरो": "0", "जीरो": "0", "एक": "1", "दो": "2", "तीन": "3", "चार": "4", "पांच": "5",
    "पाँच": "5", "छह": "6", "छः": "6", "छे": "6", "सात": "7", "आठ": "8", "नौ": "9",
    # Tamil (romanised + script)
    "poojyam": "0", "onnu": "1", "ondru": "1", "rendu": "2", "moonu": "3", "naalu": "4", "anju": "5",
    "aaru": "6", "ezhu": "7", "ettu": "8", "ombodhu": "9", "ombathu": "9",
    "பூஜ்யம்": "0", "ஒன்று": "1", "ஒண்ணு": "1", "இரண்டு": "2", "ரெண்டு": "2", "மூன்று": "3", "மூணு": "3",
    "நான்கு": "4", "நாலு": "4", "ஐந்து": "5", "அஞ்சு": "5", "ஆறு": "6", "ஏழு": "7", "எட்டு": "8",
    "ஒன்பது": "9",
    # Bengali (romanised + script)
    "shunno": "0", "dui": "2", "chhoy": "6", "noy": "9",
    "শূন্য": "0", "এক": "1", "দুই": "2", "তিন": "3", "চার": "4", "পাঁচ": "5", "ছয়": "6", "সাত": "7",
    "আট": "8", "নয়": "9",
    # Kannada script
    "ಸೊನ್ನೆ": "0", "ಒಂದು": "1", "ಎರಡು": "2", "ಮೂರು": "3", "ನಾಲ್ಕು": "4", "ಐದು": "5", "ಆರು": "6", "ಏಳು": "7",
    "ಎಂಟು": "8", "ಒಂಬತ್ತು": "9",
    # Telugu script
    "సున్నా": "0", "ఒకటి": "1", "రెండు": "2", "మూడు": "3", "నాలుగు": "4", "ఐదు": "5", "ఆరు": "6", "ఏడు": "7",
    "ఎనిమిది": "8", "తొమ్మిది": "9",
}
_MULT = {"double": 2, "dabal": 2, "dubble": 2, "triple": 3, "tripal": 3, "डबल": 2, "ट्रिपल": 3}
_NATIVE = str.maketrans("०१२३४५६७८९০১২৩৪৫৬৭৮৯௦௧௨௩௪௫௬௭௮௯೦೧೨೩೪೫೬೭೮೯౦౧౨౩౪౫౬౭౮౯", "0123456789" * 5)
_TRAIL = re.compile(r"^(.*?)([,.;:!?।|\"')\]]*)$", re.S)
_LEAD = re.compile(r"^([\"'(\[]*)(.*)$", re.S)


_HI_1_99 = (
    "एक दो तीन चार पांच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस इक्कीस बाईस "
    "तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अडतीस "
    "उनतालीस चालीस इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अडतालीस उनचास पचास इक्यावन बावन "
    "तिरेपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सडसठ अडसठ उनहत्तर "
    "सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उनासी अस्सी इक्यासी बयासी तिरासी "
    "चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे "
    "अट्ठानवे निन्यानवे"
).split()
_HI_N = {w: i for i, w in enumerate(_HI_1_99, 1)} | {"छः": 6, "छे": 6}
_HI_MULT = {"सौ": 100, "हजार": 1000, "लाख": 100_000, "करोड": 10_000_000}


MAX_GROUP = 5  # longest digit group that is joined with its neighbours
AMOUNT_MARK = "<amount>"


def _hi_key(tok: str) -> str:
    tok = unicodedata.normalize("NFC", tok)  # precomposed U+095B / U+095C (za, Ra) -> letter + nukta
    return tok.replace("\u093c", "").replace("\u0901", "\u0902")  # drop nukta, chandrabindu -> anusvara


def _is_amount(value: int) -> bool:
    """A number said with a multiplier is an amount when it is round or in lakhs (das hazaar, das crore).
    Non-round 5-digit groups (99887 said as words) can still be half of a phone number."""
    return value >= 100_000 or value % 100 == 0


def _hindi_compounds(text: str) -> list[tuple[str, bool]]:
    """'निन्यानवे हज़ार आठ सौ सत्तासी' -> '99887', 'पचपन' -> '55'. Single digits are left for the digit-run rule.
    Returns (token, is_amount) pairs."""
    out: list[tuple[str, bool]] = []
    group: list[tuple[str, str, str]] = []  # (kind, key, trail)

    def flush() -> None:
        if not group:
            return
        if any(k == "m" for k, _, _ in group):
            total = cur = 0
            for kind, key, _ in group:
                if kind == "n":
                    cur += _HI_N[key]
                elif _HI_MULT[key] == 100:
                    cur = (cur or 1) * 100
                else:
                    total, cur = total + (cur or 1) * _HI_MULT[key], 0
            out.append((str(total + cur) + group[-1][2], _is_amount(total + cur)))
        else:
            out.extend((str(_HI_N[key]) + tr if _HI_N[key] >= 10 else raw, False)
                       for (_, key, tr), raw in zip(group, raws))
        group.clear()
        raws.clear()

    raws: list[str] = []
    for tok in text.split():
        core, trail = _TRAIL.match(tok).groups()
        key = _hi_key(core)
        kind = "n" if key in _HI_N else "m" if key in _HI_MULT else None
        # two number words in a row start a new number: 'बीस पच्चीस हज़ार' is 20-25 thousand, not 45000
        if kind is None or (kind == "n" and group and group[-1][0] == "n") or (kind == "m" and not group):
            flush()
            if kind is None or kind == "m":
                out.append((tok, False))
                continue
        group.append((kind, key, trail))
        raws.append(tok)
        if trail:
            flush()
    flush()
    return out


def _digit_value(core: str) -> str | None:
    c = core.translate(_NATIVE)
    if c.isascii() and c.isdigit():
        return c
    return _WORDS.get(core.lower())


def words_to_digits(text: str, *, mask_amounts: bool = False) -> str:
    """Spoken/native digits -> ASCII digits. Spoken digits are joined into one number ('nau aath' -> '98');
    numbers already written as numerals stay separate groups ('50000 98765 43210'): `find_entities` decides
    which groups belong together. With mask_amounts=True, numbers said as amounts ('दस हज़ार') become
    AMOUNT_MARK so they can never be read as a phone or account number."""
    out: list[str] = []
    run: list[str] = []  # digit strings
    raw: list[str] = []  # original tokens of the run
    typed = False  # the run is one group of numerals (STT output or a parsed Hindi compound)

    def flush(trail: str = "") -> None:
        nonlocal typed
        if run and (len(run) >= 2 or len(run[0]) > 1 or any(r.translate(_NATIVE) != r for r in raw)):
            out.append("".join(run) + trail)
        elif raw:
            raw[-1] = raw[-1] + trail if trail else raw[-1]
            out.extend(raw)
        elif trail:
            out.append(trail)
        run.clear()
        raw.clear()
        typed = False

    mult: int | None = None
    for tok, amount in _hindi_compounds(text):
        if amount:
            flush()
            mult = None
            out.append(AMOUNT_MARK + _TRAIL.match(tok).group(2) if mask_amounts else tok)
            continue
        lead, rest = _LEAD.match(tok).groups()
        core, trail = _TRAIL.match(rest).groups()
        low = core.lower()
        if low in _MULT and not lead:
            if typed:
                flush()
            mult = _MULT[low]
            raw.append(tok)
            continue
        val = _digit_value(core) if not lead else None
        if val is not None:
            if mult:
                val, mult = val * mult, None
            numeral = core.isascii() and core.isdigit()
            if run and (numeral or typed or len(val) > MAX_GROUP or len(run[-1]) > MAX_GROUP):
                flush()  # '50000 9876543210' stays two numbers
            typed = numeral
            run.append(val)
            raw.append(core)
            if trail:
                flush(trail)
            continue
        flush()
        mult = None
        out.append(tok)
    flush()
    return " ".join(out)
