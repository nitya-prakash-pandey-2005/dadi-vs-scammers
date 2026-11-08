"""Deterministic extraction of scam identifiers from (code-mixed) transcripts.
Runs on every scammer turn; the LLM extractor adds names, agencies, scam type and red flags."""

from __future__ import annotations

import difflib
import re

from .numwords import words_to_digits

_UPI = re.compile(r"(?<![\w.@-])([a-zA-Z0-9][a-zA-Z0-9._-]{1,255}@[a-zA-Z]{2,64})(?![\w@]|\.[a-zA-Z])")
_IFSC = re.compile(r"\b([A-Za-z]{4}0[A-Za-z0-9]{6})\b")
_URL = re.compile(r"(https?://\S+|\b[a-z0-9-]+\.(?:com|in|net|org|xyz|top|online|site|app|co|info|live|ly|icu|click|shop|buzz|link|cc|gd|gy)\b(?:/\S*)?)", re.I)
_DIGIT_GROUPS = re.compile(r"(?:\+?91[\s-]?)?\d+(?:(?:[\s-]|,\s)\d+)*")
_AMOUNT = re.compile(
    r"(₹\s?[\d,]+(?:\.\d+)?|(?:rs\.?|inr)\s?[\d,]+|[\d,]+(?:\.\d+)?\s?(?:rupees|rupaye|rupay|rs|lakh|lac|crore|hazaar|hazar|thousand|रुपये|रुपए|रुपया|हजार|हज़ार|लाख))",
    re.I,
)
_APPS = {
    "anydesk": "AnyDesk", "any desk": "AnyDesk", "teamviewer": "TeamViewer", "team viewer": "TeamViewer",
    "quicksupport": "QuickSupport", "quick support": "QuickSupport", "rustdesk": "RustDesk", "rust desk": "RustDesk",
}
_AT_RATE = re.compile(r"\s*(?:at the rate(?: of)?|attherate|एट द रेट)\s*", re.I)
_DOT = re.compile(r"\s+(?:dot|डॉट)\s+", re.I)
UPI_HANDLES = [
    "okaxis", "oksbi", "okhdfcbank", "okicici", "ybl", "ibl", "axl", "paytm", "upi", "apl", "ptyes", "ptaxis",
    "pthdfc", "ptsbi", "axisbank", "sbi", "icici", "hdfcbank", "kotak", "idfcbank", "yesbank", "freecharge",
    "jupiteraxis", "naviaxis", "superyes", "fam", "airtel", "jio", "cnrb", "barodampay", "pnb", "indus",
]
_HANDLE = re.compile(r"@([a-zA-Z]+)(?:([\s.])([a-zA-Z]+))?")


def _repair_handle(m: re.Match) -> str:
    """Snaps a misheard UPI handle to a known one: "@okax.in" -> "@okaxis", "@ok sbi" -> "@oksbi"."""
    one, sep, two = m.group(1).lower(), m.group(2), m.group(3)
    if one in UPI_HANDLES:
        return m.group(0)
    if two:
        hit = difflib.get_close_matches(one + two.lower(), UPI_HANDLES, n=1, cutoff=0.8)
        if hit:
            return "@" + hit[0]
    prefixed = [h for h in UPI_HANDLES if len(one) >= 2 and h.startswith(one)]
    if len(prefixed) == 1:
        return "@" + prefixed[0] + (sep + two if two else "")
    hit = difflib.get_close_matches(one, UPI_HANDLES, n=1, cutoff=0.8)
    return "@" + hit[0] + (sep + two if two else "") if hit else m.group(0)


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for x in items:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _classify_number(digits: str) -> tuple[str, str] | None:
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return "phones", digits[2:]
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return "phones", digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return "phones", digits
    if 9 <= len(digits) <= 18:
        return "accounts", digits
    return None


def find_entities(text: str) -> dict[str, list[str]]:
    t = words_to_digits(text or "")
    t = _AT_RATE.sub("@", t)
    t = _DOT.sub(".", t)
    t = _HANDLE.sub(_repair_handle, t)
    out: dict[str, list[str]] = {k: [] for k in ("upi_ids", "phones", "accounts", "ifsc", "urls", "apps", "amounts")}

    for m in _UPI.finditer(t):
        out["upi_ids"].append(m.group(1).lower())
    for m in _IFSC.finditer(t):
        code = m.group(1).upper()
        if any(ch.isdigit() for ch in code[5:]) or code[5:].isalpha():
            out["ifsc"].append(code)
    no_upi = _UPI.sub(" ", t)
    for m in _URL.finditer(no_upi):
        if "@" not in m.group(1):
            out["urls"].append(m.group(1))

    for m in _DIGIT_GROUPS.finditer(_IFSC.sub(" ", no_upi)):
        group = m.group(0)
        parts = re.findall(r"\d+", group)
        has_cc = bool(re.match(r"\+?91[\s-]", group))
        if len(parts) > 1 and (has_cc or all(len(p) <= 5 for p in parts)):
            candidates = ["".join(parts)]
        else:
            candidates = parts
        for c in candidates:
            got = _classify_number(c)
            if got:
                out[got[0]].append(got[1])

    low = t.lower()
    for k, name in _APPS.items():
        if k in low:
            out["apps"].append(name)
    out["amounts"] = [m.group(1).strip() for m in _AMOUNT.finditer(t)]
    return {k: _dedupe(v) for k, v in out.items()}
