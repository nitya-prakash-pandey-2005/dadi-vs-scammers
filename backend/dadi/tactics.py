"""Tactic planner: decides what Dadi tries to do on each turn, so calls stay long and drift
towards the scammer revealing where the money should go (mule UPI IDs / accounts)."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

MOVES: dict[str, str] = {
    # stalling
    "glasses": "You can't find your glasses, so you can't read the screen; look for them out loud.",
    "door_bell": "Someone rings the doorbell (milkman / vegetable seller); excuse yourself briefly, then come back confused.",
    "pressure_cooker": "The pressure cooker whistles in the kitchen; you must go and turn it off, then ask where you were.",
    "mishear": "Mishear a key word funnily (e.g. CBI -> CID TV serial, KYC -> KFC, UPI -> UP) and ask if that's right.",
    "repeat_please": "Say the line was unclear and ask them to repeat slowly, word by word.",
    "slow_digits": "Read out the number you're asked for VERY slowly, digit by digit, lose your place and restart once.",
    "battery_low": "Worry that the phone battery is low and look for the charger, keep talking while searching.",
    "grandson": "Mention your grandson who handles your phone; say you'll ask him, or ask the caller to wait for him.",
    "health_tangent": "Drift into a short story about your health (knees, BP) before coming back to the topic.",
    "tv_serial": "Get distracted by the TV serial or radio for a moment and describe what's happening.",
    "wrong_button": "Pretend you pressed the wrong button / the app closed / the screen went dark; ask what to do again.",
    "neighbour": "Mention the neighbour (who says these calls are fraud, but you trust the caller) and ask a naive question.",
    # extraction
    "ask_upi": "Agree to pay but ask them to say their UPI ID slowly so you can write it on paper; read it back once.",
    "ask_account_ifsc": "Say UPI doesn't work for you; ask for their bank account number and IFSC to give at the bank, slowly.",
    "ask_name_badge": "Respectfully ask their full name, designation and badge/employee number 'for your diary'.",
    "ask_whatsapp": "Ask for their WhatsApp number so your grandson can send the 'documents' there.",
    "ask_police_station": "Ask which police station / office and city they are calling from, and their senior's name.",
}

POOLS: dict[str, list[str]] = {
    "confused": ["mishear", "repeat_please", "glasses", "door_bell"],
    "scared": ["ask_name_badge", "ask_police_station", "grandson", "health_tangent"],
    "stall_pay": ["wrong_button", "battery_low", "pressure_cooker", "glasses", "door_bell", "neighbour", "tv_serial"],
    "extract": ["ask_upi", "ask_account_ifsc", "ask_whatsapp", "ask_name_badge"],
    "loop": ["repeat_please", "wrong_button", "grandson", "health_tangent", "tv_serial", "neighbour",
             "ask_whatsapp", "ask_account_ifsc", "ask_upi"],
}

MISSIONS: dict[str, dict] = {  # operator-set goal for a call: which intel to get first
    "upi": {"label": "Get the UPI ID", "field": "upi_ids", "moves": ["ask_upi"]},
    "account": {"label": "Get the bank account + IFSC", "field": "accounts", "moves": ["ask_account_ifsc"]},
    "whatsapp": {"label": "Get the WhatsApp number", "field": "phones", "moves": ["ask_whatsapp"]},
    "identity": {"label": "Get name, badge and office", "field": "names", "moves": ["ask_name_badge", "ask_police_station"]},
}


def mission_done(mission: str | None, intel: dict) -> bool:
    return bool(mission in MISSIONS and intel.get(MISSIONS[mission]["field"]))


PHASE_GOALS = {
    "confused": "You just picked up; you are confused and slow. Do not agree to anything yet.",
    "scared": "You are getting scared and want to cooperate, but you're slow and ask innocent questions.",
    "stall_pay": "You are 'trying' to do what they ask, but keep failing at it in believable ways.",
    "extract": "You are ready to pay or share details, but you need THEIR details first, said slowly.",
    "loop": "You already wrote down their payment details; keep them on the line: confirm wrongly, ask again, drift.",
}

_FAKE_PATTERNS = [
    ("aadhaar", re.compile(r"aadha+r|आधार|ஆதார்|আধার", re.I)),
    ("card", re.compile(r"\bcard\b|कार्ड|கார்டு|কার্ড|card number", re.I)),
    ("otp", re.compile(r"\botp\b|o\.t\.p|ओटीपी|\bpin\b|पिन|\bcvv\b", re.I)),
    ("account", re.compile(r"(your|apna|aapka|aapke|tumhara)\s+(bank\s+)?account|खाता", re.I)),
]


@dataclass
class CallState:
    turn: int = 0
    captured: set[str] = field(default_factory=set)
    recent_moves: list[str] = field(default_factory=list)
    last_scammer_text: str = ""
    mission: str | None = None
    mission_done: bool = False


@dataclass
class Tactic:
    phase: str
    move: str
    instruction: str
    fake_field: str | None = None


def _phase(state: CallState) -> str:
    if state.turn <= 1:
        return "confused"
    if state.turn <= 3:
        return "scared"
    if state.captured & {"upi_ids", "accounts"}:
        return "loop"
    return "extract" if state.turn % 2 == 0 else "stall_pay"


def _fake_field(text: str) -> str | None:
    for name, pat in _FAKE_PATTERNS:
        if pat.search(text or ""):
            return name
    return None


def next_tactic(state: CallState, rng: random.Random) -> Tactic:
    phase = _phase(state)
    recent = set(state.recent_moves[-3:])
    fake = _fake_field(state.last_scammer_text)
    if fake:
        move = "slow_digits" if "slow_digits" not in recent else "wrong_button"
        if move in recent:
            move = next((m for m in POOLS["stall_pay"] if m not in recent), "glasses")
    elif state.mission in MISSIONS and not state.mission_done and state.turn >= 2 and state.turn % 2 == 0:
        moves = MISSIONS[state.mission]["moves"]
        move = moves[(state.turn // 2) % len(moves)]
    else:
        options = [m for m in POOLS[phase] if m not in recent]
        if not options:
            options = [m for m in MOVES if m not in recent and m != "slow_digits"]
        move = rng.choice(options)
    instruction = f"{PHASE_GOALS[phase]} This turn: {MOVES[move]}"
    if state.mission in MISSIONS and not state.mission_done:
        instruction += f" Your hidden aim for this call: {MISSIONS[state.mission]['label'].lower()}."
    if fake:
        instruction += f" They asked for your {fake}: give the FAKE {fake} from your notes, slowly, with one mistake."
    return Tactic(phase=phase, move=move, instruction=instruction, fake_field=fake)
