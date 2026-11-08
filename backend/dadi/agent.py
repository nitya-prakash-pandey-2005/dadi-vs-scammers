"""DadiAgent: implements the voice-core Agent protocol for the scam-baiting grandmothers."""

from __future__ import annotations

import random
from typing import AsyncIterator

from voice_core.types import Turn

from .brain import DadiBrain
from .intel import IntelReport, extract_intel, intel_json
from .personas import PERSONAS, Persona, persona_for_language
from .store import Store
from .tactics import CallState, mission_done
from .taxonomy import SCAM_KEYTERMS

AUTO_STT_HINT = "hi-IN,en-IN,ta-IN,bn-IN,kn-IN,te-IN"


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

    def on_language(self, code: str | None) -> dict | None:
        if not self.auto:
            return None
        new = persona_for_language(code)
        if new.key == self.persona.key:
            return None
        self.persona = new
        self.brain.persona = new
        self.store.set_persona(self.call_id, new.key)
        return {"type": "persona", "persona": new.key, "persona_name": new.name, "city": new.city, "language": code}

    async def reply_sentences(self, history: list[Turn]) -> AsyncIterator[str]:
        last = next((t.text for t in reversed(history) if t.speaker == self.user_label), "")
        self.state.last_scammer_text = last
        async for s in self.brain.reply_sentences(history, self.state, self.rng):
            yield s

    def turn_meta(self) -> dict:
        t = self.brain.last_tactic
        return {"tactic": t.move, "phase": t.phase} if t else {}

    async def on_user_turn(self, history: list[Turn]) -> dict | None:
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
