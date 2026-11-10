"""A real phone line for Dadi: Twilio Media Streams and Exotel Voicebot (AgentStream) over WebSocket.

Both send the caller's audio as base64 JSON "media" messages and accept Dadi's audio the same way; "clear" flushes
what is still queued (barge-in). Twilio uses 8 kHz mu-law (G.711) in 20 ms frames; Exotel uses 8 kHz 16-bit PCM and
wants outgoing chunks in multiples of 320 bytes (20 ms). The call itself runs through the same engine as the browser
call (`calls.run_call`), so everything (barge-in, fillers, intel, voice fingerprint, recording) works on the phone.

Setup: README "Real phone line". Twilio: point the number's voice webhook at `https://<host>/twilio/voice`.
Exotel: a Voicebot applet with URL `wss://<host>/ws/exotel?token=<DADI_PHONE_TOKEN>`.
"""

from __future__ import annotations

import base64
import json

import numpy as np

_BIAS, _CLIP = 0x84, 32635


def mulaw_encode(pcm16: bytes) -> bytes:
    """PCM16 little-endian -> G.711 mu-law bytes (one per sample)."""
    x = np.frombuffer(pcm16[: len(pcm16) // 2 * 2], "<i2").astype(np.int32)
    sign = (x < 0).astype(np.int32) << 7
    mag = np.minimum(np.abs(x), _CLIP) + _BIAS
    exp = np.clip(np.floor(np.log2(mag)).astype(np.int32) - 7, 0, 7)
    mant = (mag >> (exp + 3)) & 0x0F
    return (~(sign | (exp << 4) | mant) & 0xFF).astype(np.uint8).tobytes()


def mulaw_decode(ulaw: bytes) -> bytes:
    """G.711 mu-law bytes -> PCM16 little-endian."""
    u = ~np.frombuffer(ulaw, np.uint8).astype(np.int32) & 0xFF
    exp = (u >> 4) & 0x07
    mag = (((u & 0x0F) << 3) + _BIAS << exp) - _BIAS
    return np.where(u & 0x80, -mag, mag).astype("<i2").tobytes()


def mask_number(number: str | None) -> str:
    """'+919876543210' -> '+91******3210' (the UI never shows a full caller number)."""
    s = (number or "").strip()
    if not s:
        return ""
    prefix, rest = (s[:3], s[3:]) if s.startswith("+") else ("", s)
    return prefix + "*" * max(0, len(rest) - 4) + rest[-4:]


class TwilioCodec:
    name = "twilio"

    def __init__(self):
        self.stream_sid: str | None = None

    def on_start(self, d: dict) -> dict:
        st = d.get("start") or {}
        self.stream_sid = d.get("streamSid") or st.get("streamSid")
        return {"call_sid": st.get("callSid"), "params": st.get("customParameters") or {}}

    def decode(self, d: dict) -> bytes:
        media = d.get("media") or {}
        if media.get("track", "inbound") != "inbound":
            return b""
        return mulaw_decode(base64.b64decode(media.get("payload") or ""))

    def encode(self, pcm16: bytes) -> list[str]:
        payload = base64.b64encode(mulaw_encode(pcm16)).decode()
        return [json.dumps({"event": "media", "streamSid": self.stream_sid, "media": {"payload": payload}})]

    def flush(self) -> list[str]:
        return []

    def clear(self) -> list[str]:
        return [json.dumps({"event": "clear", "streamSid": self.stream_sid})]


class ExotelCodec:
    name = "exotel"
    UNIT = 320  # bytes: 20 ms of 8 kHz PCM16; outgoing chunks must be multiples of this

    def __init__(self):
        self.stream_sid: str | None = None
        self._carry = b""

    def on_start(self, d: dict) -> dict:
        st = d.get("start") or {}
        self.stream_sid = d.get("stream_sid") or st.get("stream_sid")
        return {"call_sid": st.get("call_sid"), "params": st.get("custom_parameters") or {},
                "from": st.get("from")}

    def decode(self, d: dict) -> bytes:
        return base64.b64decode((d.get("media") or {}).get("payload") or "")

    def _msg(self, pcm16: bytes) -> str:
        return json.dumps({"event": "media", "stream_sid": self.stream_sid,
                           "media": {"payload": base64.b64encode(pcm16).decode()}})

    def encode(self, pcm16: bytes) -> list[str]:
        data = self._carry + pcm16
        cut = len(data) - len(data) % self.UNIT
        self._carry = data[cut:]
        return [self._msg(data[:cut])] if cut else []

    def flush(self) -> list[str]:
        """End of an utterance: send the last < 20 ms, padded with silence."""
        if not self._carry:
            return []
        data = self._carry + b"\x00" * (self.UNIT - len(self._carry))
        self._carry = b""
        return [self._msg(data)]

    def clear(self) -> list[str]:
        self._carry = b""
        return [json.dumps({"event": "clear", "stream_sid": self.stream_sid})]


CODECS = {"twilio": TwilioCodec, "exotel": ExotelCodec}
