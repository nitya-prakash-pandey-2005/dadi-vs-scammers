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
    # Bunty, the grandson (family hand-off): eager to pay, hopeless with apps, always needs it spelled out
    "spell_upi": "Say you are ready to pay right now, but the app says 'invalid UPI ID': ask him to spell his UPI ID "
                 "letter by letter, then read it back with one letter wrong so he has to correct you.",
    "spell_account": "Say UPI is failing 'for security', so you'll do a bank transfer: ask for the account number "
                     "and IFSC, character by character, 'for the payment to go through'; repeat the IFSC back slowly.",
    "app_fumble": "You opened the wrong app (Instagram / the calculator / the cricket app); narrate the fumble and "
                  "ask him to repeat what exactly to press, and where the money goes.",
    "beneficiary_name": "The bank app asks for the beneficiary name and branch before it allows the transfer: ask him "
                        "for the full account-holder name and bank branch.",
}

POOLS: dict[str, list[str]] = {
    "confused": ["mishear", "repeat_please", "glasses", "door_bell"],
    "scared": ["ask_name_badge", "ask_police_station", "grandson", "health_tangent"],
    "stall_pay": ["wrong_button", "battery_low", "pressure_cooker", "glasses", "door_bell", "neighbour", "tv_serial"],
    "extract": ["ask_upi", "ask_account_ifsc", "ask_whatsapp", "ask_name_badge"],
    "loop": ["repeat_please", "wrong_button", "grandson", "health_tangent", "tv_serial", "neighbour",
             "ask_whatsapp", "ask_account_ifsc", "ask_upi"],
    "bunty": ["spell_upi", "spell_account", "app_fumble", "beneficiary_name"],
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
    "bunty": "You are Bunty, the grandson: Dadi handed you the phone. You want to pay quickly, but you need every "
             "detail spelled out 'for the payment to go through'.",
}

# Family hand-off: once per call, when the pressure peaks, Dadi passes the phone to her grandson for BUNTY_TURNS
# scammer turns, then he gives it back. More time wasted, and Bunty asks for every payment detail letter by letter.
HANDOFF_MIN_TURN = 3  # Dadi replies before the earliest hand-off (she must have been on the line a while)
HANDOFF_LATEST_TURN = 7  # if the pressure never peaks, she still hands over at this reply
BUNTY_TURNS = 3  # Bunty's own (LLM) replies; he also speaks first in the hand-back turn
_PRESSURE = re.compile(
    r"\b(?:pay\w*|transfer\w*|bhej\w*|paise|paisa|rupa?y\w*|rupees?|rs\.?|fees?|fine|jurmana|deposit|"
    r"arrest\w*|police|jail|fir|warrant|block\w*|freez\w*|seiz\w*|court|case|giraftaar\w*)\b"
    r"|₹|पैस|रुपय|रुपए|पेमेंट|ट्रांसफर|भेज|जमा|फीस|जुर्माना|गिरफ़?्तार|पुलिस|जेल|वारंट|ब्लॉक|फ्रीज़?|केस|कोर्ट|अरेस्ट",
    re.I,
)


def pressure(text: str) -> bool:
    """A payment demand or a threat in the caller's line: the moment Dadi 'can't cope' and calls Bunty."""
    return bool(_PRESSURE.search(text or ""))


_FAKE_PATTERNS = [
    ("aadhaar", re.compile(r"aadha+r|आधार|ஆதார்|আধার|ಆಧಾರ್|ఆధార్", re.I)),
    ("card", re.compile(r"\bcard\b|कार्ड|கார்டு|কার্ড|ಕಾರ್ಡ್|కార్డ్|card number", re.I)),
    ("otp", re.compile(r"\botp\b|o\.t\.p|ओटीपी|ஓடிபி|ওটিপি|ಒಟಿಪಿ|ఓటీపీ|\bpin\b|पिन|\bcvv\b", re.I)),
    ("account", re.compile(r"(your|apna|aapka|aapke|tumhara)\s+(bank\s+)?account|खाता", re.I)),
]
# The caller must actually ASK for the value ("OTP bataiye"), not just mention it ("aapka Aadhaar linked hai").
_REQUEST = re.compile(
    r"\b(?:bata\w*|btao|bol(?:o|iye|ie|na|\s+do)|bhej\w*|di(?:jiye|jie|ye)|de\s?do|dena|dein|share|send|tell|give|"
    r"read|say|provide|confirm|sunao|sunaiye|likhwa\w*|kya\s+hai|what\s+is|what's|"
    r"(?:otp|pin|cvv|number|details?|aadhaa?r|card)\s+(?:jaldi\s+)?do|"
    r"sollu\w*|kudu\w*|kodu\w*|anuppu\w*|bolun|dao|pathan|pathao|heli|helu|kalisi|"
    r"chepp\w*|ivvandi|pampandi)\b"
    r"|बता|बोल|भेज|दीजि|दे\s?दो|(?:ओटीपी|OTP|नंबर|नम्बर|पिन)\s+दो|शेयर|पढ़|सुना|क्या\s+है"
    r"|சொல்லு|கொடு|குடு|அனுப்பு|என்ன|বলুন|বলো|দিন|দাও|পাঠা|ಹೇಳಿ|ಕೊಡಿ|ಕಳಿಸಿ|ಕಳುಹಿಸಿ|ಏನು"
    r"|చెప్ప|ఇవ్వ|పంప|ఏంటి",
    re.I,
)
_CLAUSE = re.compile(r"[,.;!?।|]")
FAKE_COOLDOWN = 4  # turns before the same fake field is read out again


@dataclass
class CallState:
    turn: int = 0
    captured: set[str] = field(default_factory=set)
    recent_moves: list[str] = field(default_factory=list)
    last_scammer_text: str = ""
    mission: str | None = None
    mission_done: bool = False
    fake_served: dict[str, int] = field(default_factory=dict)  # fake field -> turn it was last read out
    family: bool = True  # the family hand-off is allowed on this call (start message "family": false turns it off)
    handoff_turn: int | None = None  # Dadi's reply number when she passed the phone to Bunty
    bunty_left: int = 0  # Bunty replies still to come before he hands back
    handed_back: bool = False


def family_step(state: CallState) -> str | None:
    """Who answers this turn in the family hand-off: "handoff" (Dadi passes the phone), "bunty" (Bunty answers),
    "handback" (Bunty gives it back to Dadi), or None (Dadi as usual). Pure: DadiAgent applies the transition."""
    if state.handoff_turn is not None:
        if state.bunty_left > 0:
            return "bunty"
        return None if state.handed_back else "handback"
    if state.family and state.turn >= HANDOFF_MIN_TURN and (
            pressure(state.last_scammer_text) or state.turn >= HANDOFF_LATEST_TURN):
        return "handoff"
    return None


@dataclass
class Tactic:
    phase: str
    move: str
    instruction: str
    fake_field: str | None = None  # fake detail to read out this turn
    fake_recent: str | None = None  # asked again right after it was read: notes stay up for a correction


def _phase(state: CallState) -> str:
    if state.handoff_turn is not None and not state.handed_back:  # Bunty holds the phone
        return "bunty"
    if state.turn <= 1:
        return "confused"
    if state.turn <= 3:
        return "scared"
    if state.captured & {"upi_ids", "accounts"}:
        return "loop"
    return "extract" if state.turn % 2 == 0 else "stall_pay"


def _fake_field(text: str) -> str | None:
    """The personal detail the caller asks for in this line, if any: the field and a request word must be
    in the same clause ("aapka account freeze hoga, OTP bataiye" -> otp; "aapka Aadhaar linked hai" -> None)."""
    for clause in _CLAUSE.split(text or ""):
        if not _REQUEST.search(clause):
            continue
        for name, pat in _FAKE_PATTERNS:
            if pat.search(clause):
                return name
    return None


def next_tactic(state: CallState, rng: random.Random) -> Tactic:
    """Picks this turn's move. Records in state.fake_served when a fake detail is handed out, so a caller who
    keeps nagging for the OTP gets it at most once every FAKE_COOLDOWN turns and the call still moves on
    to extraction (ask_upi, ask_account_ifsc, ...)."""
    phase = _phase(state)
    recent = set(state.recent_moves[-3:])
    fake = _fake_field(state.last_scammer_text)
    recent_fake = None
    if fake and state.turn - state.fake_served.get(fake, -FAKE_COOLDOWN) < FAKE_COOLDOWN:
        recent_fake, fake = fake, None  # read out just now: stall or extract instead of reading it again
    if fake:
        state.fake_served[fake] = state.turn
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
        instruction += f" They asked for your {fake}: read the FAKE {fake} from your notes, slowly, digit by digit, exactly as your notes say."
    elif recent_fake:
        instruction += (f" He asks for your {recent_fake} again: only if he says what you read was wrong, read the "
                        "correction from your notes once; otherwise do this turn's task first.")
    return Tactic(phase=phase, move=move, instruction=instruction, fake_field=fake, fake_recent=recent_fake)
