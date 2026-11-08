"""DADI_FAKE=1: run the whole app with no API keys (for UI work on bad networks).
A scripted 'scammer' speaks every few seconds and Dadi answers with canned lines and a soft tone."""

from __future__ import annotations

import asyncio
import itertools

import numpy as np

from voice_core.audio import float_to_pcm16
from voice_core.gnani.stt_stream import SttEvent

SCRIPT = [
    "Hello madam, main CBI headquarters se Inspector Vijay Rathore bol raha hoon.",
    "Aapke Aadhaar card se ek parcel mein drugs mile hain, aapke naam pe arrest warrant hai.",
    "Ye baat kisi ko mat batana, warna aapko abhi digital arrest kiya jayega.",
    "Aapko verification ke liye apna paisa safe account mein transfer karna hoga.",
    "UPI ID likhiye: rathore.cbi@okaxis, aur mera WhatsApp number hai nau aath saat chhe paanch chaar teen do ek shunya.",
    "Madam jaldi kariye, AnyDesk app install kariye abhi.",
]
DADI_LINES = [
    "हाँ बेटा? <coughs> कौन बोल रहा है, ज़रा ज़ोर से बोलो।",
    "CBI? अरे वो TV वाला CID? मुझे तो वो बहुत पसंद है बेटा।",
    "हाय राम, मैंने तो कुछ नहीं किया। रुको, चश्मा ढूँढ रही हूँ।",
    "अच्छा बेटा, पैसे भेज दूँगी। अपना UPI ID धीरे धीरे बोलो, लिख रही हूँ।",
    "rathore… dot… cbi… <pauses> बेटा, ये 'at the rate' कहाँ लगाते हैं?",
    "अरे, कुकर की सीटी बज गई, एक मिनट रुकना।",
]


class CyclingLLM:
    provider = "fake"
    model = "fake"

    def __init__(self, lines: list[str]):
        self._it = itertools.cycle(lines)

    async def complete(self, messages, **kw) -> str:
        return '{"scam_type": "digital_arrest", "scam_confidence": 0.9, "agencies_claimed": ["CBI"], "names": ["Vijay Rathore"]}'

    async def stream(self, messages, **kw):
        text = next(self._it)
        for i in range(0, len(text), 12):
            await asyncio.sleep(0.03)
            yield text[i : i + 12]


class ScriptedStt:
    """Ignores audio; 'hears' the next scripted scammer line every `every` seconds."""

    def __init__(self, every: float = 7.0):
        self.every = every
        self.connected = False
        self._closed = asyncio.Event()

    async def connect(self):
        self.connected = True

    async def send_audio(self, pcm16: bytes):
        pass

    async def commit(self):
        pass

    async def events(self):
        yield SttEvent("connected")
        for line in itertools.cycle(SCRIPT):
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=self.every)
                break
            except asyncio.TimeoutError:
                pass
            yield SttEvent("speech_start")
            await asyncio.sleep(1.0)
            yield SttEvent("processing")
            await asyncio.sleep(0.3)
            yield SttEvent("transcript", text=line, language="hi-IN", latency_ms=180.0)
        yield SttEvent("closed")

    async def close(self):
        self.connected = False
        self._closed.set()


async def tone_tts(api_key, text, sample_rate: int = 8000, **kw):
    """A soft 220 Hz hum whose length follows the text (stands in for Timbre audio)."""
    secs = min(4.0, 0.06 * len(text) + 0.4)
    t = np.arange(int(secs * sample_rate)) / sample_rate
    x = 0.08 * np.sin(2 * np.pi * 220 * t) * np.minimum(1, np.minimum(t, secs - t) * 8)
    pcm = float_to_pcm16(x.astype(np.float32))
    step = sample_rate // 5 * 2
    for i in range(0, len(pcm), step):
        await asyncio.sleep(0.02)
        yield pcm[i : i + step]
