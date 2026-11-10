"""Fake mode (DADI_FAKE=1, the keyless path used for UI work and reviewers) and the pre-rendered assets
(fillers, babble). No network: Timbre is replaced by a fake that counts its calls."""

import asyncio
import base64
from pathlib import Path

import numpy as np
import pytest

from dadi import assets, fake_mode
from dadi.personas import PERSONAS
from voice_core.audio import pcm16_to_float
from voice_core.config import Settings
from voice_core.gnani import tts as tts_mod

SR = 8000


# -- fake mode ------------------------------------------------------------------------------------------------------


async def test_cycling_llm_serves_scripted_lines_in_order_and_intel_json():
    dialogue = fake_mode.CyclingLLM(["one", "two"])
    assert [await dialogue.complete([]) for _ in range(3)] == ["one", "two", "one"]
    pieces = [p async for p in fake_mode.CyclingLLM(["a long line of text"]).stream([])]
    assert "".join(pieces) == "a long line of text" and all(len(p) <= 12 for p in pieces)
    intel = await fake_mode.CyclingLLM([]).complete([])
    assert '"scam_type": "digital_arrest"' in intel


async def test_scripted_stt_hears_the_script_and_stops_on_close():
    stt = fake_mode.ScriptedStt(every=0.01)
    await stt.connect()
    assert stt.connected
    await stt.send_audio(b"\x00\x00")  # ignored
    await stt.commit()
    seen = []

    async def listen():
        async for e in stt.events():
            seen.append(e)
            if e.type == "transcript":
                await stt.close()

    await asyncio.wait_for(listen(), 5)
    types = [e.type for e in seen]
    assert types == ["connected", "speech_start", "processing", "transcript", "closed"]
    assert seen[3].text == fake_mode.SCRIPT[0] and seen[3].language == "hi-IN"
    assert not stt.connected


async def test_tone_tts_length_follows_text_and_is_capped():
    short = await fake_mode.tone_tts_bytes("", "haan", sample_rate=SR)
    long = await fake_mode.tone_tts_bytes("", "x" * 500, sample_rate=SR)
    assert len(short) % 2 == 0 and 0 < len(short) < len(long)
    assert len(long) == int(4.0 * SR) * 2  # never longer than 4 s
    x = pcm16_to_float(long)
    assert float(np.max(np.abs(x))) < 0.1  # soft hum, not a blast


async def test_fake_embed_has_gnani_shape_and_unit_norm():
    emb = await fake_mode.fake_embed("", b"wav")
    v = np.frombuffer(base64.b64decode(emb["embedding"]), "<f4")
    assert emb["shape"] == [1, 768] and emb["dtype"] == "float32" and v.shape == (768,)
    assert float(np.linalg.norm(v)) == pytest.approx(1.0, abs=1e-5)


async def test_echo_stt_hears_exactly_what_was_intended():
    ev = await fake_mode.echo_stt("", b"", intended="UPI ID batao")
    assert ev.type == "transcript" and ev.text == "UPI ID batao"
    assert fake_mode.all_audio(b"\x01\x02", SR) == b"\x01\x02"


# -- pre-rendered assets --------------------------------------------------------------------------------------------


@pytest.fixture
def fake_timbre(monkeypatch):
    calls: list[tuple[str, dict]] = []

    async def fake_tts_rest(api_key, text, **kw):
        calls.append((text, kw))
        if "fail" in api_key:
            raise RuntimeError("timbre down")
        return (np.full(SR // 2, 3000, "<i2")).tobytes()  # 0.5 s

    monkeypatch.setattr(tts_mod, "tts_rest", fake_tts_rest)
    return calls


async def test_fillers_without_a_key_use_only_the_disk_cache(tmp_path, fake_timbre):
    settings = Settings(sample_rate=SR, cache_dir=tmp_path)
    assert await assets.load_or_make_fillers(settings, tmp_path) == {}
    assert fake_timbre == []  # no key: never calls Gnani


async def test_fillers_are_rendered_once_then_served_from_cache(tmp_path, fake_timbre):
    settings = Settings(sample_rate=SR, cache_dir=tmp_path, gnani_api_key="k")
    first = await assets.load_or_make_fillers(settings, tmp_path)
    expected = {t for p in PERSONAS.values() for t in [p.greeting, *p.fillers]}
    assert set(first) == expected
    n = len(fake_timbre)
    assert n == len(expected)
    again = await assets.load_or_make_fillers(Settings(sample_rate=SR, cache_dir=tmp_path), tmp_path)
    assert again == first and len(fake_timbre) == n  # cache hit, even without a key


async def test_filler_render_failure_is_logged_not_raised(tmp_path, fake_timbre):
    settings = Settings(sample_rate=SR, cache_dir=tmp_path, gnani_api_key="fail")
    assert await assets.load_or_make_fillers(settings, tmp_path) == {}
    assert fake_timbre  # it tried


async def test_babble_falls_back_to_pink_noise_without_a_key(tmp_path, fake_timbre):
    mix = await assets.load_or_make_babble(Settings(sample_rate=SR), tmp_path, seconds=1.0)
    assert mix.dtype == np.float32 and len(mix) == SR
    assert float(np.max(np.abs(mix))) == pytest.approx(0.8, abs=1e-4)  # normalised
    assert not (Path(tmp_path) / "noise").exists()  # pink noise alone is not cached
    assert fake_timbre == []


async def test_babble_mixes_tts_voices_and_caches_the_result(tmp_path, fake_timbre):
    settings = Settings(sample_rate=SR, gnani_api_key="k")
    mix = await assets.load_or_make_babble(settings, tmp_path, seconds=2.0)
    assert len(fake_timbre) == len(assets.BABBLE_LINES)
    cached = Path(tmp_path) / "noise" / f"babble_{SR}.npy"
    assert cached.exists()
    again = await assets.load_or_make_babble(settings, tmp_path, seconds=2.0)
    assert np.array_equal(again, mix) and len(fake_timbre) == len(assets.BABBLE_LINES)


async def test_babble_survives_every_tts_line_failing(tmp_path, fake_timbre):
    mix = await assets.load_or_make_babble(Settings(sample_rate=SR, gnani_api_key="fail"), tmp_path, seconds=1.0)
    assert len(mix) == SR and not (Path(tmp_path) / "noise").exists()


def test_to_rate_resamples():
    x = np.sin(np.linspace(0, 20, SR)).astype(np.float32)
    assert abs(len(assets.to_rate(x, SR, 16000)) - 2 * SR) <= 1
