"""Dadi's brain: turns the persona + current tactic + conversation into short spoken lines."""

from __future__ import annotations

import random
import re
from typing import AsyncIterator

from voice_core.turns import split_sentences
from voice_core.types import Turn

from .fakes import fake_wallet
from .personas import Persona
from .tactics import CallState, Tactic, next_tactic

ALLOWED_TAGS = ("coughs", "sigh", "laugh", "pauses", "slow", "clears throat")
HISTORY_TURNS = 12
_LABEL = re.compile(r"^\s*(?:dadi|paati|thakuma|kamla(?: devi)?|meenakshi|bela(?: rani)?|assistant|grandma)\s*[:：-]\s*", re.I)
_STAGE = re.compile(r"\s*(?:\([^)]*\)|\*[^*]*\*|\[[^\]]*\])\s*")
_TAG = re.compile(r"<([^<>]{1,20})>")


def clean_reply(text: str) -> str:
    t = _LABEL.sub("", text or "")
    t = _STAGE.sub(" ", t)
    t = _TAG.sub(lambda m: f"<{m.group(1)}>" if m.group(1) in ALLOWED_TAGS else " ", t)
    t = t.replace("\"", "").replace("“", "").replace("”", "")
    return re.sub(r"\s{2,}", " ", t).strip()


def system_prompt(p: Persona, tactic: Tactic, wallet: dict) -> str:
    notes = ""
    if tactic.fake_field and tactic.fake_field in wallet:
        notes = f"\nYour notes (FAKE, safe to read out): {tactic.fake_field} = {wallet[tactic.fake_field]}"
    return (
        f"You are {p.name}, {p.age}, from {p.city}. {p.backstory}\n"
        "You are on a phone call with a stranger who is very likely a scammer. You never say so. "
        "Your secret goal: keep him talking as long as possible and make him reveal where money should be sent "
        "(his UPI ID, bank account and IFSC, phone or WhatsApp number, his name and badge number), while you never "
        "give any real information.\n"
        "How you talk:\n"
        f"- {p.style}\n"
        "- 1 or 2 short spoken sentences per reply (at most about 25 words). Warm, slow, a little confused; you may repeat words.\n"
        "- You may use at most one of these sound tags per reply, inside the text: <coughs> <sigh> <laugh> <pauses> <slow> <clears throat>.\n"
        "- No lists, no emojis, no stage directions in brackets, no speaker labels.\n"
        "- Never say you are an AI or a bot. Never accuse him of being a scammer. Never insult or threaten.\n"
        "- Never give real personal data. Use only the fake details in your notes, and only when asked; read numbers "
        "slowly and get one digit wrong the first time.\n"
        "- If he gets angry, stay sweet and confused.\n"
        f"- Your little world: {', '.join(p.quirks)}.\n"
        f"Right now: {tactic.instruction}{notes}"
    )


def build_messages(persona: Persona, tactic: Tactic, history: list[Turn], wallet: dict) -> list[dict]:
    msgs = [{"role": "system", "content": system_prompt(persona, tactic, wallet)}]
    for turn in history[-HISTORY_TURNS:]:
        role = "user" if turn.speaker == "scammer" else "assistant"
        msgs.append({"role": role, "content": turn.text})
    return msgs


class DadiBrain:
    def __init__(self, llm, persona: Persona, seed: int = 0):
        self.llm = llm
        self.persona = persona
        self.wallet = fake_wallet(seed)
        self.last_tactic: Tactic | None = None

    async def reply_sentences(self, history: list[Turn], state: CallState, rng: random.Random) -> AsyncIterator[str]:
        tactic = next_tactic(state, rng)
        self.last_tactic = tactic
        state.recent_moves.append(tactic.move)
        state.turn += 1
        msgs = build_messages(self.persona, tactic, history, self.wallet)
        buf = ""
        async for delta in self.llm.stream(msgs, temperature=0.9, max_tokens=120):
            buf += delta
            done, buf = split_sentences(buf)
            for s in done:
                s = clean_reply(s)
                if s:
                    yield s
        done, _ = split_sentences(buf, final=True)
        for s in done:
            s = clean_reply(s)
            if s:
                yield s
