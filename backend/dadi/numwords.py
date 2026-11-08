"""Turn spoken digits ("nau aath saat", "double five", "नौ आठ", "rendu moonu") into ASCII digits.

Only runs of two or more digit tokens are converted, so a lone "do" (Hindi "give") or "ek"
("one" as in "ek minute") stays a word. Native-script numerals (०-९, ০-৯) are always converted.
"""

from __future__ import annotations

import re

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
}
_MULT = {"double": 2, "dabal": 2, "dubble": 2, "triple": 3, "tripal": 3, "डबल": 2, "ट्रिपल": 3}
_NATIVE = str.maketrans("०१२३४५६७८९০১২৩৪৫৬৭৮৯௦௧௨௩௪௫௬௭௮௯", "0123456789" * 3)
_TRAIL = re.compile(r"^(.*?)([,.;:!?।|\"')\]]*)$", re.S)
_LEAD = re.compile(r"^([\"'(\[]*)(.*)$", re.S)


def _digit_value(core: str) -> str | None:
    c = core.translate(_NATIVE)
    if c.isascii() and c.isdigit():
        return c
    return _WORDS.get(core.lower())


def words_to_digits(text: str) -> str:
    out: list[str] = []
    run: list[str] = []  # digit strings
    raw: list[str] = []  # original tokens of the run
    mult: int | None = None

    def flush(trail: str = "") -> None:
        nonlocal mult
        if run and (len(run) >= 2 or len(run[0]) > 1 or any(r.translate(_NATIVE) != r for r in raw)):
            out.append("".join(run) + trail)
        elif raw:
            raw[-1] = raw[-1] + trail if trail else raw[-1]
            out.extend(raw)
        elif trail:
            out.append(trail)
        run.clear()
        raw.clear()
        mult = None

    for tok in text.split():
        lead, rest = _LEAD.match(tok).groups()
        core, trail = _TRAIL.match(rest).groups()
        low = core.lower()
        if low in _MULT and not lead:
            mult = _MULT[low]
            raw.append(tok)
            continue
        val = _digit_value(core) if not lead else None
        if val is not None:
            if mult:
                val, mult = val * mult, None
            run.append(val)
            raw.append(core)
            if trail:
                flush(trail)
            continue
        flush()
        out.append(tok)
    flush()
    return " ".join(out)
