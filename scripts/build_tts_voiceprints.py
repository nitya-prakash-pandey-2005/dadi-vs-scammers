"""One-off: fingerprint every Timbre v3.0 voice over an 8 kHz phone line -> backend/dadi/data/tts_voiceprints.json.
Spends ~26 Gnani calls (TTS is cached). Run: uv run python scripts/build_tts_voiceprints.py"""

import asyncio
import base64
import json
import random

import numpy as np

from voice_core.audio import wav_bytes
from voice_core.config import get_settings, repo_root
from voice_core.gnani.tts import create_voice_embedding

from dadi.arena import default_tts, degrade
from dadi.rings import voiceprint_vec

VOICES = ["Shivani", "Lakshmi", "Kalpana", "Chetana", "Vasudha", "Riyaa", "Tarika",
          "Avinash", "Prakash", "Harshad", "Devansh", "Shubham", "Yashraj"]
TEXT = ("नमस्ते, मैं बैंक के ग्राहक सेवा विभाग से बोल रहा हूँ। आपके खाते की जानकारी अपडेट करनी है, "
        "इसलिए कृपया कुछ मिनट लाइन पर बने रहिए।")


async def main():
    s = get_settings()
    tts, rng, out = default_tts(s), random.Random(0), {}
    for v in VOICES:
        pcm = await tts(s.gnani_api_key, TEXT, voice=v, language="hi-IN", sample_rate=s.sample_rate)
        emb = await create_voice_embedding(s.gnani_api_key, wav_bytes(degrade(pcm, s.sample_rate, None, None, rng), s.sample_rate))
        out[v] = base64.b64encode(voiceprint_vec(emb).astype("<f4").tobytes()).decode()
        print(v, round(len(pcm) / 2 / s.sample_rate, 1), "s")
    path = repo_root() / "backend" / "dadi" / "data" / "tts_voiceprints.json"
    path.write_text(json.dumps({"model": "timbre-v3.0", "phone_band_hz": s.sample_rate, "voices": out}, indent=1))
    vecs = {k: np.frombuffer(base64.b64decode(b), "<f4") for k, b in out.items()}
    sims = [float(a @ b / np.linalg.norm(a) / np.linalg.norm(b)) for i, a in enumerate(vecs.values()) for b in list(vecs.values())[i + 1:]]
    print("max cosine between different voices:", round(max(sims), 3))


asyncio.run(main())
