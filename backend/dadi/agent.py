"""DadiAgent: implements the voice-core Agent protocol for the scam-baiting grandmothers."""

from __future__ import annotations

import random
import time
from typing import AsyncIterator

from voice_core.types import Turn

from .brain import DadiBrain
from .intel import ID_FIELDS, IntelReport, extract_intel, intel_json, merge_intel
from .intel_rules import find_entities
from .personas import PERSONAS, Persona, persona_for_language
from .store import Store
from .tactics import CallState, mission_done
from .taxonomy import SCAM_KEYTERMS

AUTO_STT_HINT = "hi-IN,en-IN,ta-IN,bn-IN,kn-IN,te-IN"
INTEL_MIN_GAP_S = 30.0  # see on_user_turn


class DadiAgent:
    user_label = "scammer"
    agent_label = "dadi"

    def __init__(self, *, store: Store, llm, intel_llm, persona_key: str = "auto", seed: int | None = None):
        self.auto = persona_key not in PERSONAS
        self.persona: Persona = PERSONAS["dadi"] if self.auto else PERSONAS[persona_key]
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.brain = DadiBrain(llm, self.persona, seed=self.seed)
        self.intel_llm = intel_llm
        self.store = store
        self.state = CallState()
        self.intel = IntelReport()
        self._intel_llm_at: int | None = None  # scammer-turn count at the last intel LLM call
        self._intel_llm_t = 0.0
        self.rng = random.Random(self.seed)
        self.call_id = store.create_call(self.persona.key)
        self.keyterms = SCAM_KEYTERMS
        self.stt_language_code = AUTO_STT_HINT if self.auto else self.persona.stt_hint

    # voice settings follow the current persona
    @property
    def voice(self) -> str:
        return self.persona.voice

    @property
    def tts_language(self) -> str:
        return self.persona.language

    @property
    def speed(self) -> float:
        return self.persona.speed

    def session_info(self) -> dict:
        return {"call_id": self.call_id, "persona": self.persona.key, "persona_name": self.persona.name,
                "city": self.persona.city, "auto": self.auto}

    def greeting(self) -> str:
        return self.persona.greeting

    def filler_texts(self) -> list[str]:
        return self.persona.fillers

    def fallback_texts(self) -> list[str]:
        """Said when a reply fails (LLM down or slow): the "say that again?" fillers, which are pre-rendered."""
        asks = [f for f in self.persona.fillers if f.rstrip(" .…").endswith("?")]
        return asks or list(self.persona.fillers)

    def on_language(self, code: str | None) -> dict | None:
        if not self.auto:
            return None
        new = persona_for_language(code)
        if new.key == self.persona.key:
            return None
        self.persona = new
        self.brain.persona = new
        self.brain.story = random.Random(self.seed).choice(new.stories) if new.stories else None
        self.store.set_persona(self.call_id, new.key)
        return {"type": "persona", "persona": new.key, "persona_name": new.name, "city": new.city, "language": code}

    async def reply_sentences(self, history: list[Turn]) -> AsyncIterator[str]:
        last = next((t.text for t in reversed(history) if t.speaker == self.user_label), "")
        self.state.last_scammer_text = last
        async for s in self.brain.reply_sentences(history, self.state, self.rng):
            yield s

    def turn_meta(self) -> dict:
        t = self.brain.last_tactic
        meta = {"tactic": t.move, "phase": t.phase} if t else {}
        if self.brain.known_caller:
            meta["recognised"] = True
        return meta

    def recognise(self, match: dict) -> dict:
        """The caller's voice matches an earlier call (voicewatch.py): Dadi will tease him about it in character."""
        self.brain.known_caller = match
        return {"type": "repeat_caller", "call_id": self.call_id, "match": match}

    def _regex_intel(self, scammer: list[Turn]) -> tuple[IntelReport, bool]:
        """Free, instant identifiers from all of the scammer's lines, and whether any of them is new."""
        found = find_entities(" \n ".join(t.text for t in scammer))
        rx = IntelReport(**found, validated={k: v for k, v in found.items() if k in ID_FIELDS and v})
        new = any(str(v).lower() not in {str(x).lower() for x in getattr(self.intel, k, [])}
                  for k, vals in found.items() for v in vals)
        return rx, new

    async def on_user_turn(self, history: list[Turn]) -> dict | None:
        # Groq free tier is ~8k tokens/min and a reply + an intel call cost ~1.5k: run the regex on every turn, the
        # intel LLM only on the first turn, when the regex found a new identifier, or every 2nd scammer turn
        scammer = [t for t in history if t.speaker == self.user_label]
        rx, new = self._regex_intel(scammer)
        self.intel = merge_intel(self.intel, rx)
        # Groq's free tier also caps OUTPUT tokens at ~1,000/min for qwen3.8-27b (live, 10 Nov): keep the intel LLM at
        # least INTEL_MIN_GAP_S apart unless a new identifier appeared, so Dadi's own replies keep their budget
        now = time.monotonic()
        due = self._intel_llm_at is None or new or (len(scammer) - self._intel_llm_at >= 2
                                                    and now - self._intel_llm_t >= INTEL_MIN_GAP_S)
        if due:
            self._intel_llm_at, self._intel_llm_t = len(scammer), now
            self.intel = await extract_intel(self.intel_llm, history, self.intel)
        self.store.save_intel(self.call_id, self.intel)
        self.state.captured = {k for k in ("upi_ids", "accounts", "phones") if getattr(self.intel, k)}
        data = intel_json(self.intel)
        self.state.mission_done = self.state.mission_done or mission_done(self.state.mission, data)
        return {"type": "intel", "call_id": self.call_id, "intel": data,
                "mission": {"key": self.state.mission, "done": self.state.mission_done} if self.state.mission else None}

    async def record(self, turn: Turn) -> None:
        self.store.add_turn(self.call_id, turn)

    def end(self, seconds: float) -> None:
        self.store.end_call(self.call_id, seconds)
