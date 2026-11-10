"""Real phone line: Twilio Media Streams / Exotel Voicebot bridges, the TwiML webhook, and the live-call monitor."""

import base64
import json
import random
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from voice_core.config import Settings
from voice_core.session import VoiceAgentSession
from voice_core.testing import FakeLLM, FakeStt, ev, fake_tts

from dadi.agent import DadiAgent
from dadi.app import create_app
from dadi.calls import CallHub
from dadi.store import Store
from dadi.telephony import ExotelCodec, TwilioCodec, mask_number, mulaw_decode, mulaw_encode


def test_mulaw_known_values_and_roundtrip():
    assert mulaw_encode(np.array([0], "<i2").tobytes()) == b"\xff"
    assert np.frombuffer(mulaw_decode(b"\xff\x7f\x00\x80"), "<i2").tolist() == [0, 0, -32124, 32124]
    x = (np.sin(np.arange(800) / 5) * 12000).astype("<i2")
    y = np.frombuffer(mulaw_decode(mulaw_encode(x.tobytes())), "<i2").astype(float)
    assert len(y) == 800 and np.max(np.abs(y - x)) < 0.04 * 12000  # G.711 is ~2-3% at this level


def test_twilio_codec_messages():
    c = TwilioCodec()
    info = c.on_start({"event": "start", "streamSid": "MZ1", "start": {"streamSid": "MZ1", "callSid": "CA1",
                       "customParameters": {"persona": "paati", "caller": "+91******3210"}}})
    assert c.stream_sid == "MZ1" and info["params"]["persona"] == "paati" and info["call_sid"] == "CA1"
    ulaw = mulaw_encode(np.full(160, 4000, "<i2").tobytes())
    media = {"event": "media", "media": {"track": "inbound", "payload": base64.b64encode(ulaw).decode()}}
    assert len(c.decode(media)) == 320
    assert c.decode({"event": "media", "media": {"track": "outbound", "payload": "AAAA"}}) == b""
    [out] = c.encode(np.zeros(400, "<i2").tobytes())
    m = json.loads(out)
    assert m["event"] == "media" and m["streamSid"] == "MZ1" and len(base64.b64decode(m["media"]["payload"])) == 400
    assert json.loads(c.clear()[0]) == {"event": "clear", "streamSid": "MZ1"}


def test_exotel_codec_sends_320_byte_multiples_and_flushes():
    c = ExotelCodec()
    c.on_start({"event": "start", "stream_sid": "S1", "start": {"stream_sid": "S1", "call_sid": "C1",
                "custom_parameters": {"persona": "dadi"}}})
    assert c.stream_sid == "S1"
    pcm = b"\x01\x00" * 500  # 1000 bytes
    out = [json.loads(m) for m in c.encode(pcm)]
    assert [len(base64.b64decode(m["media"]["payload"])) for m in out] == [960]  # 40 bytes wait in the carry
    assert out[0]["stream_sid"] == "S1"
    [f] = [json.loads(m) for m in c.flush()]
    assert len(base64.b64decode(f["media"]["payload"])) == 320  # padded with silence
    assert c.flush() == []
    c.encode(b"\x01\x00" * 10)
    assert json.loads(c.clear()[0]) == {"event": "clear", "stream_sid": "S1"} and c.flush() == []
    raw = np.full(160, 99, "<i2").tobytes()
    assert c.decode({"event": "media", "media": {"payload": base64.b64encode(raw).decode()}}) == raw


def test_mask_number():
    assert mask_number("+919876543210") == "+91******3210"
    assert mask_number("09876543210") == "*******3210" and mask_number("") == "" and mask_number(None) == ""


# ---------------------------------------------------------------- app level

async def _long_tts(*args, **kw):  # 1 s of audio: still "playing" when the scammer starts talking
    yield bytes([1, 0]) * 8000


def _app(tmp_path, *, stt_events=None, phone_token=None, tts=fake_tts):
    settings = Settings(sample_rate=8000, cache_dir=tmp_path / "cache")
    holder = {}

    def factory(send_json, send_audio, persona):
        store = holder.setdefault("s", Store(settings.cache_dir / "dadi.db"))
        agent = DadiAgent(store=store, llm=FakeLLM(["हाँ बेटा, बोलो।"] * 3), intel_llm=FakeLLM([]),
                          persona_key=persona, seed=1)
        stt = FakeStt(stt_events or [ev("connected")], gap=0.05)
        sess = VoiceAgentSession(agent, send_json=send_json, send_audio=send_audio, settings=settings,
                                 stt_factory=lambda: stt, tts_fn=tts, rng=random.Random(0))
        return sess, agent

    return create_app(settings, session_factory=factory, phone_token=phone_token), holder


def _twilio_start(params=None):
    return {"event": "start", "sequenceNumber": "1", "streamSid": "MZ9",
            "start": {"streamSid": "MZ9", "callSid": "CA9", "accountSid": "AC1", "tracks": ["inbound"],
                      "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
                      "customParameters": params or {"persona": "dadi", "caller": "+91******3210"}}}


def _media(seconds=1.0):
    ulaw = mulaw_encode((np.sin(np.arange(int(8000 * seconds)) / 3) * 6000).astype("<i2").tobytes())
    return [{"event": "media", "streamSid": "MZ9",
             "media": {"track": "inbound", "chunk": str(i), "payload": base64.b64encode(ulaw[i : i + 160]).decode()}}
            for i in range(0, len(ulaw), 160)]


def test_twilio_call_end_to_end_with_monitor(tmp_path):
    app, holder = _app(tmp_path, stt_events=[ev("connected"), ev("transcript", "Main SBI se bol raha hoon")])
    with TestClient(app) as c, c.websocket_connect("/ws/monitor") as mon:
        with c.websocket_connect("/ws/twilio") as ph:
            ph.send_text(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
            ph.send_text(json.dumps(_twilio_start()))
            got = []
            for m in _media(0.5):
                ph.send_text(json.dumps(m))
            for _ in range(4):  # greeting + reply (2 fake TTS chunks each) come back as Twilio media messages
                got.append(json.loads(ph.receive_text()))
            time.sleep(0.2)
            ph.send_text(json.dumps({"event": "stop", "streamSid": "MZ9", "stop": {"callSid": "CA9"}}))
        seen = []
        for _ in range(40):
            seen.append(mon.receive_json())
            if seen[-1]["type"] == "call_ended":
                break
    assert all(g["event"] == "media" and g["streamSid"] == "MZ9" for g in got)
    started = next(m for m in seen if m["type"] == "session_started")
    assert started["channel"] == "twilio" and started["caller"] == "+91******3210" and started["call_id"]
    assert any(m["type"] == "turn" and m["speaker"] == "scammer" for m in seen)
    assert seen[-1]["type"] == "call_ended" and all(m["call_id"] == started["call_id"] for m in seen)
    store = holder["s"]
    call = store.get_call(started["call_id"])
    assert call["ended_at"] and store.recording(started["call_id"])["seconds"] > 0


def test_barge_in_on_the_phone_sends_clear(tmp_path):
    app, _ = _app(tmp_path, stt_events=[ev("connected"), ev("speech_start")], tts=_long_tts)
    with TestClient(app) as c, c.websocket_connect("/ws/twilio") as ph:
        ph.send_text(json.dumps(_twilio_start()))
        msgs = []
        for _ in range(10):
            msgs.append(json.loads(ph.receive_text()))
            if msgs[-1]["event"] == "clear":
                break
        ph.send_text(json.dumps({"event": "stop"}))
    assert msgs[-1] == {"event": "clear", "streamSid": "MZ9"}


def test_phone_token_is_enforced(tmp_path):
    app, _ = _app(tmp_path, phone_token="s3cret")
    with TestClient(app) as c:
        with c.websocket_connect("/ws/twilio") as ph:
            ph.send_text(json.dumps(_twilio_start({"persona": "dadi"})))
            with pytest.raises(WebSocketDisconnect) as e:
                ph.receive_text()
        assert e.value.code == 1008
        with c.websocket_connect("/ws/exotel?token=s3cret") as ph:
            ph.send_text(json.dumps({"event": "start", "stream_sid": "S1", "start": {"stream_sid": "S1"}}))
            assert json.loads(ph.receive_text())["event"] == "media"  # the greeting: accepted
            ph.send_text(json.dumps({"event": "stop"}))


def test_twiml_webhook_masks_the_caller_and_points_at_the_stream(tmp_path):
    app, _ = _app(tmp_path, phone_token="s3cret")
    with TestClient(app) as c:
        r = c.post("/twilio/voice?persona=paati", data={"From": "+919876543210", "CallSid": "CA1"},
                   headers={"host": "dadi.example.org"})
        bad = c.post("/twilio/voice?persona=<x>", data={})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/xml")
    x = r.text
    assert '<Stream url="wss://dadi.example.org/ws/twilio">' in x
    assert '<Parameter name="persona" value="paati"/>' in x and '<Parameter name="token" value="s3cret"/>' in x
    assert "+91******3210" in x and "9876543210" not in x
    assert '<Parameter name="persona" value="auto"/>' in bad.text  # unknown persona -> auto, nothing injected


async def test_hub_replays_live_calls_to_late_viewers_and_forgets_ended_ones():
    hub = CallHub()
    hub.publish("c1", {"type": "session_started", "call_id": "c1"})
    hub.publish("c1", {"type": "turn", "speaker": "scammer", "text": "hello"})
    q = hub.subscribe()
    assert [q.get_nowait()["type"] for _ in range(2)] == ["session_started", "turn"]
    hub.publish("c1", {"type": "call_ended"})
    assert q.get_nowait()["type"] == "call_ended" and hub.live_calls() == []
    late = hub.subscribe()
    assert late.empty()
    hub.unsubscribe(q)
    hub.publish("c2", {"type": "session_started"})
    assert q.empty() and late.get_nowait()["call_id"] == "c2"
