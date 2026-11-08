"""Dadi never forgets a voice: live repeat-caller detection.

During a call the caller's speech is collected (the call bridge feeds it only while Dadi is silent, so her own
voice coming back through a speakerphone is not mixed in). Once there are MIN_LIVE_SPEECH_S seconds of speech,
Gnani's voice-clone embedding fingerprints the caller once and compares it with every earlier call's fingerprint
(cosine; live check 8 Nov over an 8 kHz line: same voice 0.93-0.95, different voices <= 0.63, see rings.py).
On a match Dadi is told, and teases him in character; the war room shows the earlier call. A match is a lead for
investigators, not proof. At hang-up the fingerprint is saved for the Scam Ring Radar (re-made from all the speech
when much more arrived after the live check).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

import numpy as np

from voice_core.audio import wav_bytes

from .rings import VOICE_MATCH, speech_only, voiceprint_vec

log = logging.getLogger(__name__)

MIN_LIVE_SPEECH_S = 8.0  # enough for a stable fingerprint, early enough to matter in the call
MIN_SAVE_SPEECH_S = 5.0  # Gnani's embedding endpoint wants 5-30 s
CHECK_EVERY_S = 2.0  # raw audio between speech-length checks (keeps the per-frame cost tiny)
MAX_BUFFER_S = 120.0
REFINGERPRINT_RATIO = 1.5

EmbedFn = Callable[[str, bytes], Awaitable[dict]]
OnMatch = Callable[[dict], Awaitable[None]]


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def best_match(vec: np.ndarray, prints: dict[str, np.ndarray], *, exclude: str | None = None,
               threshold: float = VOICE_MATCH) -> tuple[str, float] | None:
    """The earlier call whose voice is closest to `vec`, if it clears the threshold."""
    best: tuple[str, float] | None = None
    for cid, p in prints.items():
        if cid == exclude or len(p) != len(vec):
            continue
        s = _cos(vec, p)
        if s >= threshold and (best is None or s > best[1]):
            best = (cid, s)
    return best


def match_info(store, call_id: str, similarity: float) -> dict:
    c = store.get_call(call_id) or {}
    intel = c.get("intel") or {}
    st = intel.get("scam_type")
    return {
        "call_id": call_id,
        "similarity": round(float(similarity), 3),
        "names": list(intel.get("names") or []),
        "agencies": list(intel.get("agencies_claimed") or []),
        "scam_type": st if st and st != "other" else None,
        "ids": sorted({str(v) for k in ("upi_ids", "phones", "accounts") for v in intel.get(k) or []}),
        "started_at": c.get("started_at"),
    }


class VoiceWatch:
    def __init__(self, *, store, call_id: str, sample_rate: int, embed_fn: EmbedFn | None, api_key: str,
                 on_match: OnMatch, min_speech_s: float = MIN_LIVE_SPEECH_S, threshold: float = VOICE_MATCH,
                 speech_filter: Callable[[bytes, int], bytes] = speech_only):
        self.store = store
        self.call_id = call_id
        self.sr = sample_rate
        self.embed_fn = embed_fn
        self.api_key = api_key
        self.on_match = on_match
        self.min_speech_s = min_speech_s
        self.threshold = threshold
        self.speech_filter = speech_filter
        self.buf = bytearray()
        self.vec: np.ndarray | None = None
        self.vec_speech_s = 0.0
        self.match: dict | None = None
        self._max_bytes = int(MAX_BUFFER_S * sample_rate) * 2
        self._step = int(CHECK_EVERY_S * sample_rate) * 2
        self._next_check = self._step
        self._task: asyncio.Task | None = None
        self._checked = False
        self._closed = False

    def _speech(self) -> bytes:
        return self.speech_filter(bytes(self.buf), self.sr)

    def feed(self, pcm16: bytes) -> None:
        """Adds caller audio; starts the one live check once there is enough speech."""
        if self.embed_fn is None or self._closed:
            return
        room = self._max_bytes - len(self.buf)
        if room > 0:
            self.buf.extend(pcm16[:room])
        if self._checked or len(self.buf) < self._next_check:
            return
        self._next_check = len(self.buf) + self._step
        speech = self._speech()
        if len(speech) / 2 / self.sr >= self.min_speech_s:
            self._checked = True
            self._task = asyncio.create_task(self._check(speech))

    async def _embed(self, speech: bytes) -> np.ndarray | None:
        try:
            return voiceprint_vec(await self.embed_fn(self.api_key, wav_bytes(speech, self.sr)))
        except Exception as e:
            log.info("voice fingerprint failed: %r", e)
            return None

    async def _check(self, speech: bytes) -> None:
        vec = await self._embed(speech)
        if vec is None:
            return
        self.vec, self.vec_speech_s = vec, len(speech) / 2 / self.sr
        hit = best_match(vec, self.store.voiceprints(), exclude=self.call_id, threshold=self.threshold)
        if not hit:
            return
        self.match = match_info(self.store, *hit)
        log.info("repeat caller: %s matches %s (%.2f)", self.call_id, hit[0], hit[1])
        try:
            await self.on_match(self.match)
        except Exception as e:
            log.warning("on_match failed: %r", e)

    async def wait(self) -> None:
        """Waits for a running live check (tests, and finish())."""
        if self._task is not None:
            try:
                await self._task
            except Exception as e:  # _check never raises; belt and braces
                log.info("voice check failed: %r", e)

    async def finish(self) -> None:
        """After hang-up: saves this caller's fingerprint for future calls and the Scam Ring Radar."""
        self._closed = True
        await self.wait()
        if self.embed_fn is None:
            return
        speech = self._speech()
        secs = len(speech) / 2 / self.sr
        if secs < MIN_SAVE_SPEECH_S:
            return
        vec = self.vec
        if vec is None or secs > self.vec_speech_s * REFINGERPRINT_RATIO:
            fresh = await self._embed(speech)  # more speech, better fingerprint; keep the live one if this fails
            if fresh is not None:
                vec = fresh
        if vec is not None:
            self.store.save_voiceprint(self.call_id, vec)
