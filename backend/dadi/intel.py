"""Scam intelligence: LLM extraction (names, agencies, scam type, red flags) merged with
deterministic regex extraction (UPI, phones, accounts, IFSC, apps, URLs, amounts). Never raises."""

from __future__ import annotations

import json
import re
import logging

from pydantic import BaseModel, Field

from voice_core.llm import parse_json_loose
from voice_core.types import Turn

from .intel_rules import find_entities
from .taxonomy import RED_FLAGS, SCAM_TYPES

log = logging.getLogger(__name__)
LIST_FIELDS = ("upi_ids", "phones", "accounts", "ifsc", "urls", "apps", "amounts", "names", "agencies_claimed")
ID_FIELDS = ("upi_ids", "phones", "accounts", "ifsc", "urls", "apps")


class RedFlag(BaseModel):
    flag: str
    quote: str = ""
    t: float = 0.0


class IntelReport(BaseModel):
    upi_ids: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    accounts: list[str] = Field(default_factory=list)
    ifsc: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    apps: list[str] = Field(default_factory=list)
    amounts: list[str] = Field(default_factory=list)
    names: list[str] = Field(default_factory=list)
    agencies_claimed: list[str] = Field(default_factory=list)
    scam_type: str = "other"
    scam_confidence: float = 0.0
    red_flags: list[RedFlag] = Field(default_factory=list)
    validated: dict[str, list[str]] = Field(default_factory=dict)  # identifiers confirmed by regex


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for x in items:
        x = str(x).strip()
        k = x.lower()
        if x and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _numbers(data: dict[str, list[str]]) -> None:
    """Phones/accounts in any format ('98765 43210', '+91 98765 43210') -> digits, sorted into phones or
    accounts by the same rules as the regex path, so one number is counted (and ring-linked) once."""
    if not (data.get("phones") or data.get("accounts")):
        return
    found = [find_entities(str(x)) for x in [*data.get("phones", []), *data.get("accounts", [])]]
    data["phones"] = _dedupe([p for e in found for p in e["phones"]])
    data["accounts"] = _dedupe([a for e in found for a in e["accounts"]])


def merge_intel(old: IntelReport, new: IntelReport) -> IntelReport:
    data = {f: _dedupe(getattr(old, f) + getattr(new, f)) for f in LIST_FIELDS}
    _numbers(data)
    if new.scam_type != "other" and (new.scam_confidence > old.scam_confidence or old.scam_type == "other"):
        data["scam_type"], data["scam_confidence"] = new.scam_type, new.scam_confidence
    else:
        data["scam_type"], data["scam_confidence"] = old.scam_type, max(old.scam_confidence, 0.0)
    flags: dict[str, RedFlag] = {}
    for f in old.red_flags + new.red_flags:
        if f.flag not in flags or f.t < flags[f.flag].t:
            flags[f.flag] = f
    data["red_flags"] = sorted(flags.values(), key=lambda f: f.t)
    validated = {k: _dedupe(old.validated.get(k, []) + new.validated.get(k, [])) for k in ID_FIELDS}
    _numbers(validated)
    data["validated"] = {k: v for k, v in validated.items() if v}
    return IntelReport(**data)


PROMPT = (
    "You analyse a phone call in which a suspected scammer talks to an elderly woman. Using ONLY the scammer's "
    "lines, extract JSON with exactly these keys: "
    '{"upi_ids": [], "phones": [], "accounts": [], "ifsc": [], "urls": [], "apps": [], "amounts": [], '
    '"names": [], "agencies_claimed": [], "scam_type": "", "scam_confidence": 0.0, '
    '"red_flags": [{"flag": "", "quote": "", "t": 0.0}]}. '
    f"scam_type must be one of {SCAM_TYPES}. Each red flag must be one of {sorted(RED_FLAGS)}; quote is a short "
    "exact quote and t is the [t=..] time of that line. Convert spoken numbers to digits. "
    "Only include what was actually said. names = only the names the caller gives for HIMSELF or his colleagues, "
    "never names of the woman's family he repeats back. Reply with the JSON only."
)


def _sanitise(d: dict) -> IntelReport:
    data: dict = {}
    for f in LIST_FIELDS:
        v = d.get(f) or []
        data[f] = [str(x) for x in v] if isinstance(v, list) else []
    for f in ("upi_ids", "ifsc"):  # LLM IDs must pass the same format rules as the regex
        data[f] = [x for item in data[f] for x in find_entities(item)[f]]
    _numbers(data)  # ... and an LLM "account" that is really a phone (or vice versa) is re-sorted
    data["amounts"] = [a for a in data["amounts"] if not re.fullmatch(r"[\d,.\s]+", a)]  # bare numbers are guesses
    st = d.get("scam_type") or "other"
    data["scam_type"] = st if st in SCAM_TYPES else "other"
    try:
        data["scam_confidence"] = max(0.0, min(1.0, float(d.get("scam_confidence") or 0.0)))
    except (TypeError, ValueError):
        data["scam_confidence"] = 0.0
    flags = []
    for f in d.get("red_flags") or []:
        if isinstance(f, dict) and f.get("flag") in RED_FLAGS:
            try:
                flags.append(RedFlag(flag=f["flag"], quote=str(f.get("quote", ""))[:160], t=float(f.get("t") or 0.0)))
            except (TypeError, ValueError):
                continue
    data["red_flags"] = flags
    return IntelReport(**data)


async def extract_intel(llm, history: list[Turn], previous: IntelReport) -> IntelReport:
    scammer = [t for t in history if t.speaker == "scammer"]
    regex: dict[str, list[str]] = {}
    for turn in scammer:  # per turn, so a number never merges with one from the next turn
        for k, v in find_entities(turn.text).items():
            regex[k] = _dedupe(regex.get(k, []) + v)
    rx = IntelReport(**{k: v for k, v in regex.items()}, validated={k: v for k, v in regex.items() if k in ID_FIELDS and v})
    llm_part = IntelReport()
    if scammer:
        transcript = "\n".join(f"[t={t.t:.1f}s] {t.text}" for t in scammer[-20:])
        try:
            raw = await llm.complete(
                [{"role": "system", "content": PROMPT}, {"role": "user", "content": transcript}],
                temperature=0.1, max_tokens=350, json_mode=True,
            )
            llm_part = _sanitise(parse_json_loose(raw))
        except Exception as e:  # bad JSON, network, rate limit: keep what we have
            log.warning("intel LLM failed: %r", e)
    return merge_intel(previous, merge_intel(rx, llm_part))


def intel_json(intel: IntelReport) -> dict:
    return json.loads(intel.model_dump_json())
