"""Scam Message Checker: paste an SMS / WhatsApp / 'notice' -> verdict, red flags, mule IDs, the true fact,
and a reply in Dadi's voice that baits the sender into revealing their payment details."""

from __future__ import annotations

import logging
import random
import re

from voice_core.gnani.tts import strip_audio_tags
from voice_core.types import Turn

from .brain import build_messages, clean_reply
from .fakes import fake_wallet
from .intel import ID_FIELDS, IntelReport, extract_intel
from .personas import persona_for_language
from .tactics import MOVES, Tactic
from .taxonomy import RED_FLAG_LABELS, SCAM_TYPE_LABELS

log = logging.getLogger(__name__)
MAX_CHARS = 2000
FACTS = {
    "digital_arrest": "Police, CBI, ED and customs never arrest anyone over a video call and never ask you to move "
                      "money to a 'safe account'. 'Digital arrest' does not exist in Indian law.",
    "courier_parcel": "Courier companies and customs never ask you to pay over a call to release a parcel 'with drugs'.",
    "kyc_bank_block": "Banks never ask for your OTP, PIN, CVV or a screen-sharing app, and never block accounts over a call.",
    "electricity_bill": "Electricity boards do not cut your power after an SMS or call from a mobile number. "
                        "Pay only in the official app or office.",
    "lottery_prize": "A real prize never asks you to pay a fee or tax first.",
    "job_task": "A real job never asks you to pay to start or to 'complete tasks' with your own money.",
    "investment": "Guaranteed high returns are a red flag. Check that the company is registered with SEBI.",
}
DEFAULT_FACT = "Never share an OTP or PIN and never pay a stranger. If money was lost, call 1930 at once."
_SCRIPT_LANG = (("ta-IN", r"[஀-௿]"), ("bn-IN", r"[ঀ-৿]"), ("hi-IN", r"[ऀ-ॿ]"))


def verdict(confidence: float, n_flags: int, has_ids: bool) -> str:
    if confidence >= 0.6 or n_flags >= 2 or (has_ids and n_flags >= 1):
        return "scam"
    if confidence >= 0.3 or n_flags == 1:
        return "suspicious"
    return "no_signs"


def _lang(text: str) -> str:
    return next((code for code, rx in _SCRIPT_LANG if re.search(rx, text)), "hi-IN")


async def _dadi_reply(llm, text: str, lang: str, rng: random.Random) -> str:
    persona = persona_for_language(lang)
    move = rng.choice(["ask_upi", "ask_account_ifsc", "ask_whatsapp"])
    tactic = Tactic("extract", move, MOVES[move] + " Text message: you are typing a reply in a chat, not speaking; "
                                                   "no sound tags, at most 2 short sentences.")
    msgs = build_messages(persona, tactic, [Turn("scammer", text, 0.0)], fake_wallet(rng.randrange(10**6)))
    try:
        return clean_reply(strip_audio_tags(await llm.complete(msgs, temperature=0.9, max_tokens=120))).strip()
    except Exception as e:
        log.info("dadi text reply failed: %r", e)
        return ""


async def check_message(text: str, *, intel_llm, llm, rng: random.Random | None = None) -> dict:
    text = (text or "").strip()[:MAX_CHARS]
    rng = rng or random.Random()
    intel = await extract_intel(intel_llm, [Turn("scammer", text, 0.0)], IntelReport())
    ids = {k: getattr(intel, k) for k in (*ID_FIELDS, "amounts") if getattr(intel, k)}
    v = verdict(intel.scam_confidence, len(intel.red_flags), any(k in ids for k in ("upi_ids", "phones", "accounts", "urls")))
    lang = _lang(text)
    return {
        "verdict": v,
        "scam_type": intel.scam_type,
        "scam_type_label": SCAM_TYPE_LABELS.get(intel.scam_type, "Not yet clear"),
        "confidence": intel.scam_confidence,
        "claimed": intel.agencies_claimed + intel.names,
        "red_flags": [{"flag": f.flag, "label": RED_FLAG_LABELS.get(f.flag, f.flag), "quote": f.quote} for f in intel.red_flags],
        "identifiers": ids,
        "fact": FACTS.get(intel.scam_type, DEFAULT_FACT),
        "persona": persona_for_language(lang).key,
        "dadi_reply": await _dadi_reply(llm, text, lang, rng) if v != "no_signs" else "",
        "report_at": ["sancharsaathi.gov.in (Chakshu)", "cybercrime.gov.in", "Helpline 1930"],
    }
