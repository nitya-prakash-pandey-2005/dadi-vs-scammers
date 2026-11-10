"""Guardian mode: protects a REAL elder on her own call (Dadi wastes scammers' time; Guardian warns the victim).

The elder puts a suspicious call on speaker next to a phone or laptop running Guardian. Guardian listens (Prisma, via
the same voice-core session), scores the caller's words for scam red flags on every turn, and when the risk crosses a
threshold it speaks one short, calm warning to HER in her language (Timbre), once per level. It never talks to the
caller and saves nothing (no call row, no recording: it is a real person's private call).

The score is rule based (no LLM: instant and free). The rules live in data/guardian_rules.json, which the web app
mirrors byte for byte (frontend/src/lib/guardian-rules.json) so the static demo scores a replayed call exactly as the
backend does; tests check both.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator, Iterable

from voice_core.types import Turn

from .intel_rules import find_entities
from .taxonomy import SCAM_KEYTERMS

RULES_PATH = Path(__file__).parent / "data" / "guardian_rules.json"
LEVELS = ("safe", "caution", "stop")
AUTO_STT_HINT = "hi-IN,en-IN,ta-IN,bn-IN,kn-IN,te-IN"


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def level_for(score: int, rules: dict | None = None) -> str:
    th = (rules or load_rules())["thresholds"]
    return "stop" if score >= th["stop"] else "caution" if score >= th["caution"] else "safe"


def normalise(text: str, rules: dict | None = None) -> str:
    """Lower-case, punctuation to single spaces, padded with spaces (so ' cbi ' matches the whole word only)."""
    rules = rules or load_rules()
    return " " + re.sub(rules["separators"], " ", text.lower()).strip() + " "


def flags_in(text: str, rules: dict | None = None) -> list[tuple[str, str]]:
    """The red flags one utterance raises, in rule order, as (flag key, what was heard)."""
    rules = rules or load_rules()
    norm, raw = normalise(text, rules), text.lower()
    hits = []
    for f in rules["flags"]:
        heard = next((t.strip() for t in f["terms"] if t in norm), None)
        if heard is None:
            m = next((m for p in f["patterns"] if (m := re.search(p, raw))), None)
            heard = m.group(0) if m else None
        if heard is not None:
            hits.append((f["key"], heard))
    return hits


@dataclass
class RiskTracker:
    """Accumulates red flags over a call. Each flag counts once; the score has diminishing returns:
    100 * (1 - prod(1 - w/100)). Every reason carries the points it actually added, so the reasons sum to the score."""

    rules: dict = field(default_factory=load_rules)
    remaining: float = 1.0  # prod(1 - w/100) over the flags seen so far
    reasons: list[dict] = field(default_factory=list)
    turns: int = 0

    @property
    def score(self) -> int:
        return math.floor(100 * (1 - self.remaining) + 0.5)  # = JavaScript's Math.round (web demo parity)

    @property
    def level(self) -> str:
        return level_for(self.score, self.rules)

    @property
    def flags(self) -> set[str]:
        return {r["flag"] for r in self.reasons}

    def add(self, text: str, extra: Iterable[tuple[str, str]] = ()) -> list[dict]:
        """Scores one caller utterance; returns the new reasons (empty when it raised nothing new)."""
        self.turns += 1
        by_key = {f["key"]: f for f in self.rules["flags"]}
        new = []
        for key, heard in [*flags_in(text, self.rules), *extra]:
            if key in self.flags or key not in by_key:
                continue
            f, before = by_key[key], self.score
            self.remaining *= 1 - f["weight"] / 100
            pts = self.score - before
            r = {"flag": key, "points": pts, "heard": heard, "turn": self.turns,
                 "text": f"+{pts}: {f['reason']}"}
            self.reasons.append(r)
            new.append(r)
        return new

    def event(self) -> dict:
        return {"type": "risk", "score": self.score, "level": self.level, "reasons": list(self.reasons),
                "thresholds": dict(self.rules["thresholds"])}


def score_texts(texts: Iterable[str], rules: dict | None = None) -> list[dict]:
    """Risk after each utterance (pure; the web demo's guardian.js must give the same list)."""
    tr = RiskTracker(rules or load_rules())
    out = []
    for t in texts:
        tr.add(t)
        out.append({"score": tr.score, "level": tr.level, "reasons": [r["text"] for r in tr.reasons]})
    return out


def warning_text(language: str, level: str, rules: dict | None = None) -> str:
    w = (rules or load_rules())["warnings"]
    return w.get(language, w["hi"])[level]


def language_of(code: str | None, rules: dict | None = None) -> str | None:
    """'ta-IN' -> 'ta' when Guardian has warnings in that language."""
    short = (code or "").split("-")[0].lower()
    return short if short in (rules or load_rules())["warnings"] else None


class GuardianAgent:
    """voice-core Agent that only listens: it speaks a warning to the elder when the risk crosses a new level, and
    yields nothing otherwise. `listen_only = True` tells VoiceAgentSession: no fillers, no fallback line, and no
    barge-in (a warning is never cut off by the caller's next words; warnings queue)."""

    user_label = "caller"
    agent_label = "guardian"
    listen_only = True
    speed = 0.9

    def __init__(self, *, language: str = "hi", rules: dict | None = None):
        self.rules = rules or load_rules()
        self.auto = language == "auto"
        self.language = language if language in self.rules["warnings"] else "hi"
        self.tracker = RiskTracker(self.rules)
        self.keyterms = SCAM_KEYTERMS
        self.stt_language_code = AUTO_STT_HINT if self.auto else self.rules["languages"][self.language]["stt"]
        self.warned: list[str] = []  # levels already spoken, in order
        self._pending: str | None = None  # level whose warning is due
        self._last_level: str | None = None
        self._seen = 0  # caller turns already scored

    @property
    def voice(self) -> str:
        return self.rules["languages"][self.language]["voice"]

    @property
    def tts_language(self) -> str:
        return self.rules["languages"][self.language]["tts"]

    def session_info(self) -> dict:
        return {"mode": "guardian", "language": self.language, "auto": self.auto,
                "thresholds": dict(self.rules["thresholds"])}

    def greeting(self) -> str:
        return ""  # silent until there is something to warn about

    def filler_texts(self) -> list[str]:
        return []

    def fallback_texts(self) -> list[str]:
        return []

    def on_language(self, code: str | None) -> dict | None:
        lang = language_of(code, self.rules) if self.auto else None
        if not lang or lang == self.language:
            return None
        self.language = lang
        return {"type": "guardian_language", "language": lang}

    def assess(self, history: list[Turn]) -> None:
        """Scores the caller turns not seen yet (idempotent: the reply and the analysis both call it)."""
        caller = [t for t in history if t.speaker == self.user_label]
        for t in caller[self._seen:]:
            ents = find_entities(t.text)  # the intel regex also reads spoken numbers ("nau aath saat ...")
            extra = [("payment_details", (ents.get("upi_ids") or ents.get("accounts"))[0])] if (
                ents.get("upi_ids") or ents.get("accounts")) else []
            if ents.get("apps"):
                extra.append(("remote_access_app", ents["apps"][0]))
            self.tracker.add(t.text, extra)
            level = self.tracker.level
            if level != "safe" and level not in self.warned:
                # one warning per level; a jump straight to "stop" says only the stop warning
                self.warned.extend(lv for lv in LEVELS[1:LEVELS.index(level) + 1] if lv not in self.warned)
                self._pending = level
        self._seen = len(caller)

    async def reply_sentences(self, history: list[Turn]) -> AsyncIterator[str]:
        self.assess(history)
        level, self._pending = self._pending, None
        if level:
            self._last_level = level
            yield warning_text(self.language, level, self.rules)

    def turn_meta(self) -> dict:
        return {"warning": True, "level": self._last_level}

    async def on_user_turn(self, history: list[Turn]) -> dict:
        self.assess(history)
        return self.tracker.event()

    async def record(self, turn: Turn) -> None:
        pass  # a real elder's call: nothing is stored

    def end(self, seconds: float) -> None:
        pass
