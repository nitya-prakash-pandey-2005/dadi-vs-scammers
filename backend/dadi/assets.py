"""Pre-rendered audio: greetings + filler clips per persona, and synthetic call-centre babble.
Rendered once with Gnani Timbre and cached on disk, so calls start instantly and cost nothing extra."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from voice_core.audio import pcm16_to_float, pink_noise, resample
from voice_core.config import Settings
from voice_core.gnani import TtsCache

from .personas import PERSONAS

log = logging.getLogger(__name__)

BABBLE_LINES = [
    ("Haan ji sir, aapka KYC update karna padega, warna account band ho jayega.", "Harshad", "hi-IN"),
    ("Madam please hold, main senior officer se baat karwata hoon.", "Devansh", "hi-IN"),
    ("Sir your parcel has been seized by customs at Mumbai airport.", "Avinash", "en-IN"),
    ("Ungal account block aagidum, OTP sollunga.", "Shubham", "ta-IN"),
    ("Apnar electricity line aaj raat kete debe.", "Prakash", "bn-IN"),
    ("Aapke naam pe FIR register hui hai, abhi verify kariye.", "Yashraj", "hi-IN"),
    ("Sir aap lottery jeet gaye hain, processing fee bhejiye.", "Riyaa", "hi-IN"),
    ("Please don't disconnect, this is a recorded line.", "Kalpana", "en-IN"),
]


def _render_kwargs(p, sr: int) -> dict:
    return dict(voice=p.voice, language=p.language, speed=p.speed, sample_rate=sr)


async def load_or_make_fillers(settings: Settings, cache_dir: Path) -> dict[str, bytes]:
    """text -> PCM16 at settings.sample_rate, for every persona's greeting and fillers. Never raises."""
    cache = TtsCache(cache_dir)
    out: dict[str, bytes] = {}
    for p in PERSONAS.values():
        kw = _render_kwargs(p, settings.sample_rate)
        for text in [p.greeting, *p.fillers]:
            key = cache.key(text, **kw)
            hit = cache.get(key)
            if hit is None and settings.gnani_api_key:
                try:
                    hit = await cache.get_or_make(settings.gnani_api_key, text, **kw)
                except Exception as e:
                    log.warning("filler render failed (%s): %r", text[:20], e)
            if hit:
                out[text] = hit
    return out


async def load_or_make_babble(settings: Settings, cache_dir: Path, seconds: float = 30.0) -> np.ndarray:
    """Call-centre babble built from Gnani TTS voices (cached). Falls back to pink noise."""
    sr = settings.sample_rate
    path = Path(cache_dir) / "noise" / f"babble_{sr}.npy"
    if path.exists():
        return np.load(path)
    n = int(seconds * sr)
    mix = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(7)
    cache = TtsCache(cache_dir)
    got = 0
    if settings.gnani_api_key:
        for text, voice, lang in BABBLE_LINES:
            try:
                pcm = await cache.get_or_make(settings.gnani_api_key, text, voice=voice, language=lang, sample_rate=sr)
            except Exception as e:
                log.warning("babble line failed: %r", e)
                continue
            x = pcm16_to_float(pcm) * rng.uniform(0.3, 0.7)
            for _ in range(3):  # scatter each voice a few times
                start = int(rng.integers(0, max(1, n - len(x))))
                seg = x[: n - start]
                mix[start : start + len(seg)] += seg
            got += 1
    mix += pink_noise(n, seed=3) * 0.3
    peak = float(np.max(np.abs(mix))) or 1.0
    mix = (mix / peak * 0.8).astype(np.float32)
    if got:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, mix)
    return mix


def to_rate(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    return resample(x, src, dst)
