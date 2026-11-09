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
    assert {p["key"] for p in app_client.get("/api/personas").json()} == {"dadi", "paati", "thakuma", "ajji", "ammamma"}
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


def test_intelligence_routes(app_client):
    assert app_client.get("/api/insights").json()["calls"] == 0
    assert app_client.get("/api/freeze-list").json() == []
    r = app_client.get("/api/freeze-list?format=csv")
    assert r.status_code == 200 and r.text.startswith("kind,id,bank") and "attachment" in r.headers["content-disposition"]
    assert app_client.get("/api/rings").json()["rings"] == []


def test_check_route_needs_text(app_client):
    assert app_client.post("/api/check", json={"text": " "}).status_code == 400


def test_second_call_from_the_same_voice_is_flagged_live(tmp_path):
    import json
    import time

    import numpy as np

    from dadi.fake_mode import fake_embed

    settings = Settings(sample_rate=8000, cache_dir=tmp_path / "cache")
    holder = {}

    def factory(send_json, send_audio, persona):
        store = holder.setdefault("s", Store(settings.cache_dir / "dadi.db"))  # the app's own database
        agent = DadiAgent(store=store, llm=FakeLLM(["हाँ बेटा।"]), intel_llm=FakeLLM([]), persona_key="dadi", seed=1)
        sess = VoiceAgentSession(agent, send_json=send_json, send_audio=send_audio, settings=settings,
                                 stt_factory=lambda: FakeStt([ev("connected")]), tts_fn=fake_tts, rng=random.Random(0))
        return sess, agent

    app = create_app(settings, session_factory=factory, voice_embed_fn=fake_embed)
    speech = (np.sin(np.arange(8000 * 12) / 3) * 8000).astype("<i2").tobytes()

    def one_call(c) -> list[dict]:
        msgs = []
        with c.websocket_connect("/ws/call") as ws:
            ws.send_json({"type": "start", "persona": "dadi"})
            msgs.append(ws.receive_json())
            time.sleep(0.2)  # let the greeting finish: frames that arrive while Dadi speaks are (rightly) skipped
            for i in range(0, len(speech), 1024):
                ws.send_bytes(speech[i : i + 1024])
            time.sleep(0.3)  # the live voice check runs in the background
            ws.send_json({"type": "hangup"})
            for _ in range(100):
                m = ws.receive()
                if m.get("type") == "websocket.close":
                    break
                if m.get("text"):
                    msgs.append(json.loads(m["text"]))
                    if msgs[-1]["type"] == "call_ended":
                        break
        return msgs

    def wait_prints(c, n: int) -> dict:
        for _ in range(60):  # a caller's fingerprint is saved just after hang-up
            rings = c.get("/api/rings").json()
            if sum(node["voiceprint"] for node in rings["nodes"]) >= n:
                break
            time.sleep(0.05)
        return rings

    with TestClient(app) as c:
        first = one_call(c)
        wait_prints(c, 1)
        second = one_call(c)
        rings = wait_prints(c, 2)
    assert not any(m["type"] == "repeat_caller" for m in first)
    rc = [m for m in second if m["type"] == "repeat_caller"]
    assert len(rc) == 1 and rc[0]["match"]["call_id"] == first[0]["call_id"]
    assert any(l["kind"] == "voice" for l in rings["links"]), rings
