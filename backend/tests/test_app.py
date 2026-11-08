import random

import pytest
from fastapi.testclient import TestClient

from voice_core.config import Settings
from voice_core.session import VoiceAgentSession
from voice_core.testing import FakeLLM, FakeStt, ev, fake_tts

from dadi.agent import DadiAgent
from dadi.app import create_app
from dadi.store import Store


@pytest.fixture
def app_client(tmp_path):
    settings = Settings(sample_rate=8000, cache_dir=tmp_path / "cache")
    store_holder = {}

    def factory(send_json, send_audio, persona):
        store = store_holder.setdefault("s", Store(tmp_path / "t.db"))
        agent = DadiAgent(store=store, llm=FakeLLM(["हाँ बेटा।"]), intel_llm=FakeLLM([]), persona_key="dadi", seed=1)
        sess = VoiceAgentSession(agent, send_json=send_json, send_audio=send_audio, settings=settings,
                                 stt_factory=lambda: FakeStt([ev("connected")]), tts_fn=fake_tts, rng=random.Random(0))
        return sess, agent

    app = create_app(settings, session_factory=factory)
    with TestClient(app) as c:
        yield c


def test_health_and_personas(app_client):
    h = app_client.get("/api/health")
    assert h.status_code == 200 and "gnani_key" in h.json()
    assert {p["key"] for p in app_client.get("/api/personas").json()} == {"dadi", "paati", "thakuma"}
    assert app_client.get("/api/totals").json()["calls"] == 0


def test_ws_call_roundtrip(app_client):
    with app_client.websocket_connect("/ws/call") as ws:
        ws.send_json({"type": "start", "persona": "dadi", "noise_snr_db": None})
        first = ws.receive_json()
        assert first["type"] == "session_started" and first["call_id"]
        ws.send_bytes(b"\x00" * 1024)
        ws.send_json({"type": "hangup"})
        msgs = []
        for _ in range(50):
            m = ws.receive()
            if m.get("type") == "websocket.close":
                break
            if m.get("text"):
                import json

                msgs.append(json.loads(m["text"]))
                if msgs[-1].get("type") == "call_ended":
                    break
        assert any(m.get("type") == "call_ended" for m in msgs)


def test_report_404(app_client):
    assert app_client.get("/api/calls/nope/report").status_code == 404
    assert app_client.get("/api/calls/nope").status_code == 404


def test_ws_arena_fake_mode(tmp_path, monkeypatch):
    import json

    monkeypatch.setenv("DADI_FAKE", "1")
    app = create_app(Settings(sample_rate=8000, cache_dir=tmp_path / "c"))
    with TestClient(app) as c, c.websocket_connect("/ws/arena") as ws:
        ws.send_json({"type": "arena", "scam_type": "kyc_bank_block", "turns": 2, "snr_db": 10})
        msgs = []
        for _ in range(40):
            m = ws.receive()
            if m.get("type") == "websocket.close":
                break
            msgs.append(json.loads(m["text"]))
            if msgs[-1]["type"] == "arena_done":
                break
        assert sum(1 for m in msgs if m["type"] == "arena_turn") == 4
        assert msgs[-1]["type"] == "arena_done"
