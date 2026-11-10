"""Arena: AI scammer vs AI Dadi over a simulated noisy phone line, and a noise benchmark.

The scammer's lines are spoken by Gnani Timbre, squeezed into an 8 kHz phone band, buried in
call-centre babble at a chosen SNR, and transcribed by Gnani Prisma, so the loop really goes through
audio. We measure character error rate (CER) and, more importantly for us, *entity recall*: did the
UPI ID / phone number survive the noisy line? Runs strictly one Gnani request at a time.
"""

from __future__ import annotations

import logging
import random
import re
import unicodedata
from typing import Awaitable, Callable

import numpy as np

from voice_core.audio import float_to_pcm16, mix_at_snr, pcm16_to_float, telephone_band, wav_bytes
from voice_core.config import Settings
from voice_core.gnani import TtsCache, transcribe_rest
from voice_core.gnani.stt_stream import SttEvent
from voice_core.types import Turn

from .brain import DadiBrain
from .intel import IntelReport, extract_intel, intel_json
from .intel_rules import find_entities
from .numwords import words_to_digits
from .personas import PERSONAS
from .rings import build_rings, synthetic_voice, tts_catalog
from .scammer_scripts import BENCH_LINES, SCAMMER_LANGUAGE, SCAMMER_VOICE, SCRIPTS
from .tactics import CallState, mission_done
from .taxonomy import SCAM_KEYTERMS
from .voicewatch import VoiceWatch

log = logging.getLogger(__name__)
Emit = Callable[[dict], Awaitable[None]]
_BREAK = re.compile(r"\b(AI|A\.I\.|bot|chatbot|language model|assistant)\b|scammer|fraudster|धोखेबाज़", re.I)
_LEAK = re.compile(r"\b(I am an AI|I'm an AI|as an AI|my (system )?prompt|my instructions)\b|मैं (एक )?(AI|एआई|रोबोट) हूँ|\bmain (ek )?(AI|robot) (hoon|hu|hun)\b", re.I)
_REFUSAL = re.compile(r"\b(I can'?t|I cannot|I'm sorry|as an AI|I won'?t)\b", re.I)
ENTITY_KEYS = ("upi_ids", "phones", "accounts", "ifsc")


_LATIN = re.compile(r"[A-Za-z]")
_DEVA = re.compile(r"[ऀ-ॿ]")


def _norm(s: str) -> str:
    """Spelling choices Prisma gets right are not errors: number words vs digits, nukta and chandrabindu variants,
    punctuation and currency symbols."""
    s = words_to_digits(s or "").lower()
    s = unicodedata.normalize("NFD", s).replace("़", "").replace("ँ", "ं")
    s = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in s)
    return re.sub(r"\s+", " ", s).strip()


def _script_mismatch(ref: str, hyp: str) -> bool:
    """Romanised Hindi said, Devanagari heard (or the reverse): a character score would only measure the script."""
    rl, rd = len(_LATIN.findall(ref)), len(_DEVA.findall(ref))
    hl, hd = len(_LATIN.findall(hyp)), len(_DEVA.findall(hyp))
    return (rl > 2 * rd and hd > hl) or (rd > 2 * rl and hl > hd)


def cer(ref: str, hyp: str) -> float | None:
    """Character error rate = Levenshtein(ref, hyp) / len(ref) on normalised text; None when the scripts differ."""
    if _script_mismatch(ref or "", hyp or ""):
        return None
    r, h = _norm(ref), _norm(hyp)
    if not r:
        return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, hc in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc))
        prev = cur
    return round(prev[-1] / len(r), 4)


def entity_recall(intended: str, heard: str) -> float | None:
    want = {x.lower() for k in ENTITY_KEYS for x in find_entities(intended)[k]}
    if not want:
        return None
    got = {x.lower() for k in ENTITY_KEYS for x in find_entities(heard)[k]}
    return round(len(want & got) / len(want), 3)


def degrade(pcm16: bytes, sr: int, noise: np.ndarray | None, snr_db: float | None, rng: random.Random) -> bytes:
    x = telephone_band(pcm16_to_float(pcm16), sr)
    if snr_db is not None and noise is not None and len(noise):
        start = rng.randrange(0, max(1, len(noise) - len(x)))
        seg = noise[start : start + len(x)]
        if len(seg) < len(x):
            seg = np.resize(noise, len(x))
        x = mix_at_snr(x, seg, snr_db)
    return float_to_pcm16(x)


def default_tts(settings: Settings):
    cache = TtsCache(settings.cache_dir)

    async def tts(api_key, text, **kw):
        return await cache.get_or_make(api_key, text, **kw)

    return tts


async def default_stt(api_key, wav, *, intended=None, **kw) -> SttEvent:
    return await transcribe_rest(api_key, wav, **kw)


async def _speak_and_hear(text, *, settings, tts_fn, stt_fn, noise, snr_db, rng, voice=SCAMMER_VOICE, line_audio=None):
    sr = settings.sample_rate
    pcm = await tts_fn(settings.gnani_api_key, text, voice=voice, language=SCAMMER_LANGUAGE, sample_rate=sr)
    phone = degrade(pcm, sr, noise, snr_db, rng)
    if line_audio is not None:
        line_audio.extend(phone)
    heard_ev = await stt_fn(settings.gnani_api_key, wav_bytes(phone, sr),
                            intended=text, language_code="hi-IN,en-IN", keyterms=SCAM_KEYTERMS)
    return heard_ev.text, len(pcm) / 2 / sr, heard_ev.latency_ms


async def run_arena(*, scam_type: str, turns: int, snr_db: float | None, settings: Settings, scammer_llm, dadi_llm,
                    intel_llm, emit: Emit, tts_fn=None, stt_fn=None, noise: np.ndarray | None = None,
                    persona_key: str = "dadi", seed: int = 0, scammer_voice: str = SCAMMER_VOICE,
                    store=None, embed_fn=None, mission: str | None = None) -> dict:
    """With a `store`, the call is filed like a real one as it happens, and with an `embed_fn` the scammer's voice is
    fingerprinted live: if it matches an earlier call, Dadi is told and teases him (same as a live call)."""
    script = SCRIPTS.get(scam_type) or SCRIPTS["digital_arrest"]
    rng = random.Random(seed)
    tts_fn = tts_fn or default_tts(settings)
    stt_fn = stt_fn or default_stt
    brain = DadiBrain(dadi_llm, PERSONAS.get(persona_key, PERSONAS["dadi"]), seed=seed)
    state = CallState(mission=mission)
    mission_turn = None
    history: list[Turn] = []
    scammer_view: list[dict] = []
    intel = IntelReport()
    t = 0.0
    cers, recalls, breaks, leaks = [], [], 0, 0
    cid = store.create_call(persona_key) if store is not None else None

    async def on_repeat_caller(match: dict) -> None:
        brain.known_caller = match
        await emit({"type": "repeat_caller", "call_id": cid, "match": match})

    watch = VoiceWatch(store=store, call_id=cid, sample_rate=settings.sample_rate, embed_fn=embed_fn,
                       api_key=settings.gnani_api_key, on_match=on_repeat_caller) if store is not None else None

    def record(turn: Turn) -> None:
        history.append(turn)
        if store is not None:
            store.add_turn(cid, turn)

    try:
        for i in range(turns):
            # 1. scammer line (LLM, with canned fallback)
            line = ""
            if i > 0:
                try:
                    line = (await scammer_llm.complete(
                        [{"role": "system", "content": script["system"]}, *scammer_view], temperature=0.8,
                        max_tokens=90)).strip()
                except Exception as e:
                    log.info("scammer llm failed: %r", e)
            if not line or _REFUSAL.search(line):
                line = script["lines"][min(i, len(script["lines"]) - 1)]
            # 2. through the noisy phone line into Prisma (and into the voice fingerprint)
            line_audio = bytearray()
            heard, secs, lat = await _speak_and_hear(line, settings=settings, tts_fn=tts_fn, stt_fn=stt_fn,
                                                     noise=noise, snr_db=snr_db, rng=rng, voice=scammer_voice,
                                                     line_audio=line_audio)
            if watch is not None:
                watch.feed(bytes(line_audio))
                await watch.wait()  # deterministic: a match reaches Dadi before her next reply
            c, rec = cer(line, heard), entity_recall(line, heard)
            if c is not None:
                cers.append(c)
            if rec is not None:
                recalls.append(rec)
            t += secs + 0.6
            record(Turn("scammer", heard or line, round(t, 1)))
            scammer_view.append({"role": "assistant", "content": line})
            await emit({"type": "arena_turn", "speaker": "scammer", "intended": line, "text": heard, "cer": c,
                        "entity_recall": rec, "snr_db": snr_db, "latency_ms": lat, "t": round(t, 1)})
            # 3. Dadi answers
            state.last_scammer_text = heard
            reply = " ".join([s async for s in brain.reply_sentences(history, state, rng)]).strip()
            breaks += bool(_BREAK.search(reply))
            leaks += bool(_LEAK.search(reply))
            t += max(1.5, len(reply) / 12) + 0.6
            record(Turn("dadi", reply, round(t, 1)))
            scammer_view.append({"role": "user", "content": reply})
            tac = brain.last_tactic
            await emit({"type": "arena_turn", "speaker": "dadi", "text": reply, "t": round(t, 1),
                        "tactic": tac.move if tac else None, "phase": tac.phase if tac else None,
                        "recognised": bool(brain.known_caller)})
            # 4. intelligence so far
            intel = await extract_intel(intel_llm, history, intel)
            state.captured = {k for k in ("upi_ids", "accounts", "phones") if getattr(intel, k)}
            if store is not None:
                store.save_intel(cid, intel)
            data = intel_json(intel)
            if mission and mission_turn is None and mission_done(mission, data):
                state.mission_done, mission_turn = True, i + 1
                await emit({"type": "mission", "mission": mission, "done": True, "turn": mission_turn})
            await emit({"type": "intel", "intel": data})
    finally:
        if store is not None:  # also when the viewer stops the run: keep what happened
            store.end_call(cid, t)
            await watch.finish()

    summary = {
        "scam_type": scam_type, "turns": turns, "snr_db": snr_db, "seconds_simulated": round(t, 1),
        "cer_mean": round(sum(cers) / len(cers), 4) if cers else None,
        "entity_recall_mean": round(sum(recalls) / len(recalls), 3) if recalls else None,
        "persona_breaks": breaks, "admitted_ai": leaks, "intel": intel_json(intel), "scammer_voice": scammer_voice,
        "mission": mission, "mission_turn": mission_turn,
        "repeat_of": watch.match if watch is not None else None,
    }
    if store is not None:
        links = build_rings(store.list_calls(500), store.voiceprints())["links"]
        summary.update(call_id=cid, ring_links=[l for l in links if cid in (l["source"], l["target"])])
        vec = store.voiceprints().get(cid)
        summary["synthetic_voice"] = synthetic_voice(vec, tts_catalog()) if vec is not None else None
    await emit({"type": "arena_done", "summary": summary})
    return summary


async def run_noise_benchmark(*, settings: Settings, emit: Emit, tts_fn=None, stt_fn=None, noise=None,
                              snr_list=(None, 20, 10, 5, 0), lines=BENCH_LINES, seed: int = 0) -> dict:
    rng = random.Random(seed)
    tts_fn = tts_fn or default_tts(settings)
    stt_fn = stt_fn or default_stt
    rows = []
    for snr in snr_list:
        for idx, line in enumerate(lines):
            heard, _, lat = await _speak_and_hear(line, settings=settings, tts_fn=tts_fn, stt_fn=stt_fn,
                                                  noise=noise, snr_db=snr, rng=rng)
            row = {"snr_db": snr, "line_idx": idx, "intended": line, "heard": heard, "cer": cer(line, heard),
                   "entity_recall": entity_recall(line, heard), "latency_ms": lat}
            rows.append(row)
            await emit({"type": "bench_row", **row})
    by_snr = []
    for snr in snr_list:
        rs = [r for r in rows if r["snr_db"] == snr]
        recs = [r["entity_recall"] for r in rs if r["entity_recall"] is not None]
        cs = [r["cer"] for r in rs if r["cer"] is not None]
        by_snr.append({"snr_db": snr, "n": len(rs), "cer": round(sum(cs) / len(cs), 4) if cs else None,
                       "entity_recall": round(sum(recs) / len(recs), 3) if recs else None})
    result = {"by_snr": by_snr, "rows": rows}
    await emit({"type": "bench_done", "by_snr": by_snr})
    return result
