"""DadiAgent: implements the voice-core Agent protocol for the scam-baiting grandmothers."""

from __future__ import annotations

import random
import time
from dataclasses import replace
from typing import AsyncIterator

from voice_core.types import Turn

from .brain import DadiBrain
from .intel import ID_FIELDS, IntelReport, extract_intel, intel_json, merge_intel
from .intel_rules import find_entities
from .personas import FAMILY, HANDBACK_LINES, HANDOFF_LINES, PERSONAS, Persona, persona_for_language
from .store import Store
from .tactics import BUNTY_TURNS, CallState, Tactic, family_step, mission_done
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
        # family hand-off (tactics.family_step): Bunty shares Dadi's fake wallet (same seed), never a real one
        self.speaker: Persona = self.persona  # who is holding the phone right now: voice settings follow them
        self.bunty_brain: DadiBrain | None = None
        self._family_event: str | None = None  # "handoff" / "handback" on the turn it happened
        self._segments: list[dict] = []  # [{persona, name, text}] of the last reply, when two people spoke in it
        self._owner: dict[str, str] = {}  # agent turn text -> "bunty" / "family" (who said it), for the prompts

    @property
    def family(self) -> bool:
        return self.state.family

    @family.setter
    def family(self, on: bool) -> None:
        self.state.family = bool(on)

    # voice settings follow whoever is speaking (Dadi, or Bunty after the hand-off), sentence by sentence
    @property
    def voice(self) -> str:
        return self.speaker.voice

    @property
    def tts_language(self) -> str:
        return self.speaker.language

    @property
    def speed(self) -> float:
        return self.speaker.speed

    def _relative(self) -> Persona | None:
        return FAMILY.get(self.persona.key)

    def session_info(self) -> dict:
        return {"call_id": self.call_id, "persona": self.persona.key, "persona_name": self.persona.name,
                "city": self.persona.city, "auto": self.auto}

    def greeting(self) -> str:
        return self.persona.greeting

    def filler_texts(self) -> list[str]:
        return self.speaker.fillers  # pre-rendered in the voice of whoever holds the phone

    def fallback_texts(self) -> list[str]:
        """Said when a reply fails (LLM down or slow): the "say that again?" fillers, which are pre-rendered."""
        asks = [f for f in self.speaker.fillers if f.rstrip(" .…").endswith("?")]
        return asks or list(self.speaker.fillers)

    def on_language(self, code: str | None) -> dict | None:
        if not self.auto:
            return None
        new = persona_for_language(code)
        if new.key == self.persona.key:
            return None
        self.persona = new
        self.speaker = new
        self.brain.persona = new
        self.brain.story = random.Random(self.seed).choice(new.stories) if new.stories else None
        self.store.set_persona(self.call_id, new.key)
        return {"type": "persona", "persona": new.key, "persona_name": new.name, "city": new.city, "language": code}

    async def reply_sentences(self, history: list[Turn]) -> AsyncIterator[str]:
        last = next((t.text for t in reversed(history) if t.speaker == self.user_label), "")
        self.state.last_scammer_text = last
        self._family_event, self._segments = None, []
        relative = self._relative()
        step = family_step(self.state) if relative else None
        if step == "bunty":  # counted in record(), once he has actually said something
            self.speaker = relative
            if self.bunty_brain is None:
                self.bunty_brain = DadiBrain(self.brain.llm, relative, seed=self.seed)  # same seed: same fake wallet
            async for s in self.bunty_brain.reply_sentences(self._annotated(history, relative.key), self.state, self.rng):
                yield s
            return
        if step in ("handoff", "handback"):
            # fixed, pre-rendered lines (assets.py): instant, no LLM call; each sentence in its speaker's voice
            if step == "handoff":
                self.state.handoff_turn, self.state.bunty_left = self.state.turn, BUNTY_TURNS
            else:
                self.state.handed_back = True
            self.state.turn += 1
            self.state.recent_moves.append(step)
            self.brain.last_tactic = Tactic(phase="family", move=step, instruction="")
            self._family_event = step
            people = {self.persona.key: self.persona, relative.key: relative}
            for who, text in (HANDOFF_LINES if step == "handoff" else HANDBACK_LINES):
                self.speaker = people[who]
                self._segments.append({"persona": who, "name": self.speaker.name, "text": text})
                yield text
            return
        self.speaker = self.persona
        async for s in self.brain.reply_sentences(self._annotated(history, self.persona.key), self.state, self.rng):
            yield s

    def _annotated(self, history: list[Turn], listener: str) -> list[Turn]:
        """The history as the speaker's LLM sees it: lines the other family member said are marked, so Dadi does not
        carry on as Bunty after the hand-back (seen live, 10 Nov) and Bunty does not think he said Dadi's lines."""
        if not self._owner:
            return history
        out = []
        for t in history:
            who = self._owner.get(t.text, "self") if t.speaker == self.agent_label else None
            if who == "family":
                t = replace(t, text=f"(Dadi and Bunty pass the phone) {t.text}")
            elif who == "bunty" and listener != "bunty":
                t = replace(t, text=f"(your grandson Bunty had the phone) {t.text}")
            elif who == "self" and listener == "bunty":
                t = replace(t, text=f"(Dadi said) {t.text}")
            out.append(t)
        return out

    def turn_meta(self) -> dict:
        bunty = self.speaker.key != self.persona.key and self._family_event is None
        brain = self.bunty_brain if bunty and self.bunty_brain else self.brain
        t = brain.last_tactic
        meta = {"tactic": t.move, "phase": t.phase} if t else {}
        meta["speaker_persona"] = self.speaker.key
        meta["speaker_name"] = self.speaker.name
        if self._family_event:
            meta["family"] = self._family_event
            meta["segments"] = list(self._segments)
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
        if turn.speaker == self.agent_label and self._relative():
            if self._family_event:
                self._owner[turn.text] = "family"
            elif self.speaker.key != self.persona.key:
                self._owner[turn.text] = "bunty"
                # one of Bunty's turns is used up only when he said something (a reply cut off before it began
                # does not count: live, a split transcript ate one of his turns)
                self.state.bunty_left = max(0, self.state.bunty_left - 1)
        self.store.add_turn(self.call_id, turn)

    def end(self, seconds: float) -> None:
        self.store.end_call(self.call_id, seconds)
