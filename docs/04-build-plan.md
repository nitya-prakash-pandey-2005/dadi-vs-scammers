# Dadi vs Scammers + shared voice engine: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A browser "phone" where a (simulated) scammer talks live to an AI grandmother built on Gnani Prisma + Timbre, with a war-room dashboard that shows time wasted, red flags, extracted mule accounts and a one-click complaint report.

**Architecture:** A FastAPI backend bridges browser audio (PCM16 at 8 kHz over WebSocket) to Prisma's realtime STT WebSocket. Final transcripts drive a persona "brain" (tactic planner + an OpenAI-compatible LLM: Groq now, Evon later) whose reply is spoken through Timbre's WebSocket TTS. In-character filler clips hide latency. Intel extraction runs in the background after each scammer turn and is stored in SQLite. Reusable pieces live in `voice-core/`; Dadi-specific pieces live in ``.

**Tech Stack:** Python 3.12 (uv workspace), FastAPI, websockets, httpx, numpy/scipy, openai SDK; React 19 + Vite 6 + the ui-kit at `D:\Hackathons\ui-kit` (JavaScript/JSX); SQLite.

**Spec:** `docs/03-design.md` (API facts in `docs/01-gnani-api-reference.md`)

## Amendments (Sun 8 Nov, 10:50): these win over anything below
1. **The engine contract is `voice-core/README.md`.** Every `voice_core` name, signature and event in this plan must match it.
2. `Turn` lives in `voice_core/types.py` (created in Task 1). Tasks 5 and 6 import it from there.
3. `split_sentences` lives in `voice_core/turns.py` (Task 6), not in `dadi/brain.py`. `brain.py` imports it.
4. Task 6 is split: the **generic** `VoiceAgentSession` (barge-in, fillers, echo guard, reconnect, noise, TTS fallback) goes in `voice_core/session.py`. `backend/dadi/agent.py` defines `DadiAgent`, which implements the Agent protocol from the contract (persona switching, brain, tactics, intel, store). Event names follow the contract: `session_started` / `session_ended` / `agent_speaking` (the UI shows them as call started / ended / Dadi speaking). `call_id` is added by `DadiAgent` into `session_started`.
5. Settings gain `intel_llm_provider`, `evon_api_key`, `stt_mode` and `cache_dir`. `extract_intel` uses `LLM(settings, purpose="intel")`.
6. Task 2 also creates `create_voice_embedding`, `tts_clone_rest` and `TtsCache` (used by apni-awaaz). Task 3 also creates `scripts/eval_llm.py`. Its prompts: the 3 Dadi personas, 5 intel transcripts, 5 Pukaar flood-call transcripts and 3 Awaaz reply-suggestion cases. It measures time to first token, total time, script correctness and valid-JSON rate, and writes a markdown table to `docs/evon-eval.md`.
7. `voice-core/web` also exports `pcmToWav` and `decodeToPcm16` (contract).

## Global Constraints

- Gnani base URL `https://api.vachana.ai`; REST header `X-API-Key-ID`; WebSocket header `x-api-key-id`.
- STT: `wss://api.vachana.ai/stt/v3/stream`, `model: prisma-v3.0`, `format: codemix`, `language_code: hi-IN,en-IN,ta-IN,bn-IN`, `x-sample-rate: 8000`; audio frames are exactly **1024 bytes** of PCM16 mono LE.
- TTS: `wss://api.vachana.ai/api/v1/tts` and `POST /api/v1/tts/inference`, `model: timbre-v3.0`, `audio_config {sample_rate: 8000, num_channels: 1, sample_width: 2, encoding: linear_pcm, container: raw}`.
- Default call audio is **8 kHz** both ways (phone quality, about 128 kbps; works on a train hotspot).
- LLM through one OpenAI-compatible client. Groq base `https://api.groq.com/openai/v1`, default model from `.env` `GROQ_MODEL`. Evon: `EVON_BASE_URL`, `extra_body={"chat_template_kwargs":{"enable_thinking":false},"repetition_penalty":1.1}`.
- Secrets only in `.env` at the repo root (git-ignored). Never hard-code keys.
- Dadi never outputs real data. Every fake card number **fails Luhn**; every fake Aadhaar starts with 0 or 1 **and fails Verhoeff**.
- Every call screen and report shows the label **"Simulated scam call: scammer played by an actor or our AI"**.
- Frontend in JavaScript/JSX to match the ui-kit (this replaces "TypeScript" in the design doc).
- Commits: no `Co-Authored-By` or "Generated with Claude" lines (user's global rule).
- Run Python with `uv run`; tests with `uv run pytest`.

## Review Focus

1. **Echo loop:** Dadi's own voice leaks from speakers into the mic, Prisma transcribes it as the scammer, and Dadi answers herself. Expected: transcripts that closely match Dadi's last 2 lines are dropped (test in Task 6), and the UI tells the scammer actor to use earphones.
2. **Network drop mid-call (train):** Prisma WebSocket closes unexpectedly. Expected: the session reconnects STT up to 5 times with backoff, the UI shows "reconnecting", the call and timer continue (test in Task 6).
3. **Barge-in:** the scammer talks while Dadi speaks. Expected: Dadi's current reply task is cancelled and the client gets `stop_audio` within one TTS chunk (test in Task 6).
4. **Silence or noise transcripts:** empty or one-character transcripts must not trigger a reply (test in Task 6).
5. **Numbers spoken as words** ("nau aath saat…", "double five"): intel must still capture the digits (test in Task 4).

---

### Task 1: Workspace, config and audio utilities

**Files:**
- Create: `voice-core/voice_core/config.py`, `voice-core/voice_core/audio.py`
- Test: `voice-core/tests/test_audio.py`, `voice-core/tests/test_config.py`
- Already present: root `pyproject.toml` (uv workspace), `voice-core/pyproject.toml`, `backend/pyproject.toml`, `.env.example`, `.gitignore`

**Interfaces:**
- Produces:
  - `Settings` (dataclass: `gnani_api_key: str`, `groq_api_key: str`, `llm_provider: str`, `groq_model: str`, `evon_base_url: str`, `evon_model: str`, `sample_rate: int = 8000`) and `get_settings() -> Settings` (reads repo-root `.env`, cached; `reload=True` arg bypasses the cache).
  - `audio.pcm16_to_float(b: bytes) -> np.ndarray`, `audio.float_to_pcm16(x: np.ndarray) -> bytes` (clips to [-1, 1])
  - `audio.resample(x, src_hz: int, dst_hz: int) -> np.ndarray` (scipy `resample_poly`)
  - `audio.telephone_band(x, hz: int) -> np.ndarray` (300 to 3400 Hz Butterworth band-pass, order 4)
  - `audio.mix_at_snr(signal, noise, snr_db: float) -> np.ndarray` (noise tiled or trimmed to signal length)
  - `audio.pink_noise(n: int, seed: int = 0) -> np.ndarray`
  - `audio.FrameBuffer(frame_bytes: int = 1024)` with `.push(b: bytes) -> list[bytes]` (returns only complete frames, keeps remainder) and `.flush() -> bytes | None` (zero-padded last frame)
  - `audio.wav_bytes(pcm16: bytes, hz: int) -> bytes`, `audio.read_wav(b: bytes) -> tuple[np.ndarray, int]` (stdlib `wave`)

- [ ] **Step 1: Write failing tests**
```python
def test_framebuffer_emits_exact_1024_byte_frames():
    fb = FrameBuffer(1024)
    assert fb.push(b"\x00" * 1000) == []
    frames = fb.push(b"\x01" * 1100)
    assert [len(f) for f in frames] == [1024, 1024] or [len(f) for f in frames] == [1024]
    assert all(len(f) == 1024 for f in frames)
    last = fb.flush()
    assert last is None or len(last) == 1024

def test_mix_at_snr_hits_target_ratio():
    sig = np.sin(np.linspace(0, 2000, 8000)).astype(np.float32) * 0.5
    noise = pink_noise(3000, seed=1)
    mixed = mix_at_snr(sig, noise, 10.0)
    n = mixed - sig
    snr = 20 * np.log10(np.sqrt(np.mean(sig**2)) / np.sqrt(np.mean(n**2)))
    assert abs(snr - 10.0) < 0.2 and len(mixed) == len(sig)

def test_pcm_roundtrip_and_resample_length():
    x = np.linspace(-0.9, 0.9, 1600).astype(np.float32)
    assert np.allclose(pcm16_to_float(float_to_pcm16(x)), x, atol=1e-4)
    assert len(resample(x, 16000, 8000)) == 800

def test_wav_roundtrip():
    pcm = float_to_pcm16(np.zeros(800, dtype=np.float32))
    data, hz = read_wav(wav_bytes(pcm, 8000))
    assert hz == 8000 and len(data) == 800

def test_settings_reads_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "k1"); monkeypatch.setenv("LLM_PROVIDER", "groq")
    s = get_settings(reload=True)
    assert s.gnani_api_key == "k1" and s.sample_rate == 8000
```
- [ ] **Step 2:** `uv run pytest voice-core/tests -v` fails (ImportError).
- [ ] **Step 3:** Implement `config.py` and `audio.py` with the signatures above.
- [ ] **Step 4:** `uv run pytest voice-core/tests -v` passes.
- [ ] **Step 5:** Commit `feat(core): workspace, settings and audio utilities`.

---

### Task 2: Gnani clients (Prisma STT stream + REST, Timbre TTS) and live smoke test

**Files:**
- Create: `voice-core/voice_core/gnani/stt_stream.py`, `voice-core/voice_core/gnani/stt_rest.py`, `voice-core/voice_core/gnani/tts.py`, `voice-core/scripts/smoke_gnani.py`
- Test: `voice-core/tests/test_gnani_protocol.py`

**Interfaces:**
- Consumes: `Settings`, `audio.FrameBuffer`, `audio.wav_bytes`
- Produces:
  - `SttEvent` (dataclass: `type: str` in {"connected","speech_start","processing","transcript","error","closed"}, `text: str = ""`, `language: str | None = None`, `latency_ms: float | None = None`, `raw: dict`)
  - `build_stt_headers(api_key: str, *, language_code: str, model: str = "prisma-v3.0", sample_rate: int = 8000, fmt: str = "codemix", keyterms: list[str] | None = None, vad: dict[str, str] | None = None) -> dict[str, str]` (keyterms sent as a JSON array string; vad keys are the raw header names such as `x-min-silence-ms`)
  - `parse_stt_message(msg: str) -> SttEvent` (maps `detected_language_code` → `language`, `latency` → `latency_ms`; unknown types → `type="error"` with `raw`)
  - `class PrismaStream(api_key, **header_kwargs)`: `async connect()`, `async send_audio(pcm16: bytes)` (re-chunks to 1024-byte frames), `async send_pcm_realtime(pcm16: bytes, sample_rate: int)` (paces 1024-byte frames at 512/sample_rate s each; for synthetic audio), `async commit()`, `events() -> AsyncIterator[SttEvent]` (ends with a `closed` event), `async close()`, `connected: bool`
  - `async transcribe_rest(api_key: str, wav: bytes, *, language_code: str = "hi-IN,en-IN", model: str = "prisma-v3.0", fmt: str = "codemix", keyterms: list[str] | None = None) -> SttEvent` (type "transcript")
  - `build_tts_body(text: str, *, voice: str, model: str = "timbre-v3.0", language: str = "hi-IN", speed: float = 1.0, sample_rate: int = 8000, container: str = "raw") -> dict`
  - `async tts_rest(api_key: str, text: str, **body_kwargs) -> bytes` (raw PCM16)
  - `tts_stream(api_key: str, text: str, **body_kwargs) -> AsyncIterator[bytes]` (WebSocket; yields decoded PCM chunks; raises `TtsError(message)` on an `error` message)
  - `strip_audio_tags(text: str) -> str` (removes the 13 Timbre v3.0 tags, for the v2.5 fallback)

- [ ] **Step 1: Write failing tests (offline, pure functions)**
```python
def test_stt_headers_contain_required_fields():
    h = build_stt_headers("KEY", language_code="hi-IN,en-IN", keyterms=["CBI", "UPI"], vad={"x-min-silence-ms": "500"})
    assert h["x-api-key-id"] == "KEY" and h["model"] == "prisma-v3.0"
    assert h["x-sample-rate"] == "8000" and h["format"] == "codemix"
    assert json.loads(h["keyterms"]) == ["CBI", "UPI"] and h["x-min-silence-ms"] == "500"

def test_parse_transcript_message():
    e = parse_stt_message(json.dumps({"type": "transcript", "text": "aap CBI se ho?", "latency": 180, "detected_language_code": "hi-IN", "is_final": True}))
    assert (e.type, e.text, e.language, e.latency_ms) == ("transcript", "aap CBI se ho?", "hi-IN", 180)

def test_tts_body_defaults():
    b = build_tts_body("नमस्ते <coughs> बेटा", voice="Lakshmi")
    assert b["model"] == "timbre-v3.0" and b["audio_config"]["sample_rate"] == 8000
    assert b["audio_config"]["container"] == "raw" and b["audio_config"]["encoding"] == "linear_pcm"

def test_strip_audio_tags():
    assert strip_audio_tags("हाँ <coughs> बेटा <clears throat>बोलो") == "हाँ बेटा बोलो"
```
- [ ] **Step 2:** Run, see FAIL. **Step 3:** Implement. **Step 4:** Run, see PASS.
- [ ] **Step 5: Live smoke script** `voice-core/scripts/smoke_gnani.py` (needs `GNANI_API_KEY`; prints PASS/FAIL per check with latency):
  1. `tts_rest` of a Hindi sentence → non-empty PCM; save `cache/smoke_tts.wav`.
  2. `transcribe_rest` of that WAV → non-empty text.
  3. `tts_stream` first-chunk latency.
  4. `PrismaStream` + `send_pcm_realtime` of the TTS audio → a `transcript` event.
  5. **Concurrency check:** while a `PrismaStream` is open, call `tts_stream`; print whether it succeeds or returns 429. The result decides whether Task 6 needs the turn-based fallback.
- [ ] **Step 6:** Commit `feat(core): Gnani Prisma and Timbre clients with smoke test`.

---

### Task 3: LLM adapter (Groq now, Evon later)

**Files:**
- Create: `voice-core/voice_core/llm.py`
- Test: `voice-core/tests/test_llm.py`

**Interfaces:**
- Produces:
  - `class LLM(settings: Settings, provider: str | None = None)`: `async complete(messages: list[dict], *, temperature: float = 0.8, max_tokens: int = 220, json_mode: bool = False) -> str`; `stream(messages, *, temperature=0.8, max_tokens=220) -> AsyncIterator[str]` (text deltas); `provider: str`; `model: str`
  - `parse_json_loose(text: str) -> dict` (strips ``` fences and `<think>…</think>`, returns the first balanced `{…}` object; raises `ValueError` if none)
  - `class FakeLLM` (in `voice_core/testing.py`): constructor takes a list of canned replies; `complete` pops one and `stream` yields it in 3 pieces. Used by later tests.

- [ ] **Step 1: Failing tests:**
```python
def test_parse_json_loose_handles_fences_and_think():
    assert parse_json_loose('<think>x</think>```json\n{"a": 1, "b": {"c": 2}}\n```') == {"a": 1, "b": {"c": 2}}
    with pytest.raises(ValueError): parse_json_loose("no json here")

def test_provider_selection():
    s = Settings(gnani_api_key="", groq_api_key="g", llm_provider="groq", groq_model="m", evon_base_url="http://x/v1", evon_model="e")
    assert LLM(s).model == "m" and LLM(s, provider="evon").model == "e"

async def test_fake_llm_stream():
    f = FakeLLM(["हाँ बेटा, बोलो।"])
    assert "".join([c async for c in f.stream([])]) == "हाँ बेटा, बोलो।"
```
- [ ] **Step 2–4:** FAIL → implement (`openai.AsyncOpenAI`; Evon adds `extra_body` from Global Constraints) → PASS.
- [ ] **Step 5:** Add `--llm` check to `smoke_gnani.py`: one Groq completion with first-token latency printed.
- [ ] **Step 6:** Commit `feat(core): OpenAI-compatible LLM adapter for Groq and Evon`.

---

### Task 4: Dadi domain (personas, taxonomy, fakes, number words, regex intel, tactic planner)

All of this runs offline (train-friendly).

**Files:**
- Create: `backend/dadi/personas.py`, `taxonomy.py`, `fakes.py`, `numwords.py`, `intel_rules.py`, `tactics.py`
- Test: `backend/tests/test_domain.py`

**Interfaces:**
- Produces:
  - `Persona` (dataclass: `key`, `name`, `age`, `city`, `language` (TTS language), `voice`, `speed`, `stt_hint` (language code), `backstory`, `quirks: list[str]`, `fillers: list[str]`, `greeting: str`). `PERSONAS: dict[str, Persona]` with keys `dadi` (Kamla Devi, 74, Kanpur, `hi-IN`, voice `Lakshmi`, speed 0.9), `paati` (Meenakshi, 76, Madurai, `ta-IN`, voice `Vasudha`, speed 0.9), `thakuma` (Bela Rani, 78, Howrah, `bn-IN`, voice `Chetana`, speed 0.9). At least 6 fillers each, including audio tags such as `"हाँ बेटा… <coughs> एक मिनट…"`. `persona_for_language(code: str | None) -> Persona` (`ta-IN` → paati, `bn-IN` → thakuma, else dadi).
  - `taxonomy.SCAM_TYPES = ["digital_arrest", "courier_parcel", "kyc_bank_block", "electricity_bill", "lottery_prize", "job_task", "investment", "other"]`; `taxonomy.RED_FLAGS = {"impersonates_authority", "threat_of_arrest", "demands_secrecy", "remote_access_app", "safe_account_transfer", "urgency_pressure", "asks_otp_pin", "asks_personal_ids"}`; `taxonomy.SCAM_KEYTERMS: list[str]` (CBI, ED, RBI, TRAI, FedEx, customs, Aadhaar, PAN, KYC, UPI, OTP, AnyDesk, TeamViewer, money laundering, narcotics, arrest warrant, digital arrest, safe account, IFSC, and more; 40 or fewer).
  - `fakes.luhn_valid(num: str) -> bool`, `fakes.verhoeff_valid(num: str) -> bool`, `fakes.fake_card(seed) -> str` (16 digits, Luhn-invalid), `fakes.fake_aadhaar(seed) -> str` (12 digits, starts with 0 or 1, Verhoeff-invalid), `fakes.fake_otp(seed) -> str` (6 digits), `fakes.fake_wallet(seed) -> dict[str, str]` (card, aadhaar, otp, bank "State Bank", balance "₹2,40,000").
  - `numwords.words_to_digits(text: str) -> str`: Hindi, English, Hinglish and Devanagari digit words (`shunya/zero/शून्य, ek/one/एक … nau/nine/नौ`) plus `double X`, `triple X` and Devanagari numerals → ASCII digits. Consecutive digit words join into one number.
  - `intel_rules.find_entities(text: str) -> dict[str, list[str]]` with keys `upi_ids`, `phones`, `accounts`, `ifsc`, `urls`, `apps`, `amounts` (runs `words_to_digits` first; UPI regex `[a-zA-Z0-9._-]{2,256}@[a-zA-Z]{2,64}`; phone `(?:\+?91[\s-]?)?[6-9]\d{9}`; account `\b\d{9,18}\b` excluding phones; IFSC `[A-Z]{4}0[A-Z0-9]{6}`; apps from {AnyDesk, TeamViewer, QuickSupport, RustDesk}).
  - `CallState` (dataclass: `turn: int = 0`, `captured: set[str]` (e.g. "upi_ids"), `recent_moves: list[str]`, `last_scammer_text: str = ""`), `Tactic` (dataclass: `phase: str`, `move: str`, `instruction: str`, `fake_field: str | None`), `next_tactic(state: CallState, rng: random.Random) -> Tactic`.
    Phases: turns 0–1 `confused`; 2–3 `scared`; then `stall_pay` and `extract` alternate until `captured` has `upi_ids` or `accounts`; then `loop` (re-ask with wrong digits, tangents). Moves never repeat within the last 3 (`recent_moves`). If `last_scammer_text` mentions OTP/PIN/CVV/card/Aadhaar, `fake_field` is set to `otp`/`card`/`aadhaar` and the move is `slow_digits`. Move ids: `glasses, door_bell, pressure_cooker, mishear, repeat_please, slow_digits, battery_low, grandson, health_tangent, tv_serial, wrong_button, neighbour, ask_upi, ask_account_ifsc, ask_name_badge, ask_whatsapp, ask_police_station`.

- [ ] **Step 1: Failing tests:**
```python
def test_fakes_are_provably_invalid():
    for s in range(50):
        assert not luhn_valid(fake_card(s)) and len(fake_card(s)) == 16
        a = fake_aadhaar(s); assert a[0] in "01" and len(a) == 12 and not verhoeff_valid(a)
    assert luhn_valid("4111111111111111") and verhoeff_valid("2363")  # known-good checks

def test_words_to_digits_hinglish():
    assert words_to_digits("nau aath saat chhe paanch chaar teen do ek shunya") == "9876543210"
    assert words_to_digits("double five triple nine") == "55999"
    assert words_to_digits("नौ आठ सात") == "987"

def test_find_entities():
    e = find_entities("UPI ID hai ramesh.kumar@okaxis aur number nau aath saat chhe paanch chaar teen do ek shunya, AnyDesk install karo, IFSC SBIN0001234")
    assert e["upi_ids"] == ["ramesh.kumar@okaxis"] and e["phones"] == ["9876543210"]
    assert e["ifsc"] == ["SBIN0001234"] and e["apps"] == ["AnyDesk"]

def test_tactics_progress_and_fake_field():
    rng = random.Random(0); st = CallState()
    assert next_tactic(st, rng).phase == "confused"
    st.turn = 6; st.last_scammer_text = "OTP batao jaldi"
    t = next_tactic(st, rng); assert t.fake_field == "otp" and t.move == "slow_digits"
    st.turn = 7; st.last_scammer_text = ""; st.captured = {"upi_ids"}
    assert next_tactic(st, rng).phase == "loop"

def test_moves_do_not_repeat_within_three():
    rng = random.Random(1); st = CallState(turn=4)
    for _ in range(12):
        t = next_tactic(st, rng); assert t.move not in st.recent_moves[-3:]
        st.recent_moves.append(t.move); st.turn += 1

def test_persona_for_language():
    assert persona_for_language("ta-IN").key == "paati" and persona_for_language(None).key == "dadi"
```
- [ ] **Step 2–4:** FAIL → implement → PASS (`uv run pytest backend/tests -v`).
- [ ] **Step 5:** Commit `feat(dadi): personas, scam taxonomy, safe fakes, number words, intel rules, tactics`.

---

### Task 5: Brain prompts, LLM intel extraction, report

**Files:**
- Create: `backend/dadi/brain.py`, `intel.py`, `report.py`
- Test: `backend/tests/test_brain_intel.py`

**Interfaces:**
- Consumes: `LLM`/`FakeLLM`, `Persona`, `Tactic`, `CallState`, `fake_wallet`, `find_entities`, `SCAM_TYPES`, `RED_FLAGS`
- Produces:
  - `Turn` (dataclass: `speaker: str` ("scammer"|"dadi"), `text: str`, `t: float` (seconds since call start), `lang: str | None = None`)
  - `build_messages(persona: Persona, tactic: Tactic, history: list[Turn], wallet: dict) -> list[dict]`: system prompt (persona card, rules: 1–3 short sentences, write as the persona speaks (Hindi in Devanagari with English words in Latin script for Dadi; Tamil/Bengali script plus English for the others), may use only these audio tags `<coughs> <sigh> <laugh> <pauses> <slow> <clears throat>`, never reveal being an AI, never give real data, read fake numbers slowly and get some digits wrong, never abuse or threaten), then the current tactic instruction, the wallet values when `tactic.fake_field` is set, and the last 12 turns as user/assistant messages.
  - `class DadiBrain(llm, persona)`: `reply_sentences(history: list[Turn], state: CallState, rng) -> AsyncIterator[str]` (streams the LLM and yields complete sentences via `split_sentences`; updates `state.recent_moves`).
  - `split_sentences(buf: str) -> tuple[list[str], str]` (splits on `. ! ? । ॥ …` or newline followed by whitespace or end; returns complete sentences and the remainder; pieces shorter than 2 characters are merged forward).
  - `IntelReport` (pydantic model: `upi_ids, phones, accounts, ifsc, urls, apps, amounts, names, agencies_claimed: list[str]`, `scam_type: str = "other"`, `scam_confidence: float = 0.0`, `red_flags: list[RedFlag]`; `RedFlag(flag: str, quote: str, t: float)`), `merge_intel(old: IntelReport, new: IntelReport) -> IntelReport` (dedupes lists case-insensitively; keeps the highest-confidence scam type; red flags deduped by `flag`).
  - `async extract_intel(llm, history: list[Turn], previous: IntelReport) -> IntelReport`: LLM JSON (json_mode) over scammer turns, merged with `find_entities` over scammer text; unknown scam types → "other"; unknown flags dropped; **on any LLM/JSON failure it returns `previous` merged with the regex entities (never raises)**.
  - `build_report(call: dict, turns: list[Turn], intel: IntelReport) -> dict` with keys `title`, `disclaimer` (the Global Constraints label), `summary`, `incident_time`, `duration_seconds`, `scam_type`, `suspect_identifiers` (dict of non-empty intel lists), `red_flags` (sorted by t), `transcript_excerpt` (first 12 turns), `where_to_report` (["cybercrime.gov.in", "Helpline 1930", "Sanchar Saathi – Chakshu"]).

- [ ] **Step 1: Failing tests:**
```python
def test_split_sentences():
    done, rest = split_sentences("हाँ बेटा। रुको ज़रा… चश्मा कहाँ है? मैं")
    assert done == ["हाँ बेटा।", "रुको ज़रा…", "चश्मा कहाँ है?"] and rest == "मैं"

def test_build_messages_includes_tactic_and_wallet():
    p = PERSONAS["dadi"]; t = Tactic(phase="stall_pay", move="slow_digits", instruction="read slowly", fake_field="otp")
    msgs = build_messages(p, t, [Turn("scammer", "OTP batao", 3.0)], {"otp": "104729"})
    sys = msgs[0]["content"]; assert "Kamla" in sys and "read slowly" in sys and "104729" in sys
    assert msgs[-1] == {"role": "user", "content": "OTP batao"}

async def test_extract_intel_survives_bad_json():
    prev = IntelReport(upi_ids=["a@okaxis"])
    out = await extract_intel(FakeLLM(["not json"]), [Turn("scammer", "send to b.kumar@ybl now", 5.0)], prev)
    assert set(out.upi_ids) == {"a@okaxis", "b.kumar@ybl"}

async def test_extract_intel_parses_llm_json():
    js = '{"scam_type":"digital_arrest","scam_confidence":0.9,"names":["Vijay Kumar"],"agencies_claimed":["CBI"],"red_flags":[{"flag":"threat_of_arrest","quote":"aapko arrest karenge","t":4.0},{"flag":"made_up","quote":"x","t":1}]}'
    out = await extract_intel(FakeLLM([js]), [Turn("scammer", "Main CBI se Vijay Kumar, aapko arrest karenge", 4.0)], IntelReport())
    assert out.scam_type == "digital_arrest" and [f.flag for f in out.red_flags] == ["threat_of_arrest"]

def test_report_has_disclaimer_and_identifiers():
    r = build_report({"id": "c1", "started_at": 0, "ended_at": 125}, [Turn("scammer", "hi", 0.0)], IntelReport(upi_ids=["x@ybl"]))
    assert "Simulated" in r["disclaimer"] and r["suspect_identifiers"] == {"upi_ids": ["x@ybl"]} and r["duration_seconds"] == 125
```
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5:** Commit `feat(dadi): persona brain, intel extraction and complaint report`.

---

### Task 6: Call session engine (fillers, barge-in, echo guard, reconnect)

**Files:**
- Create: `voice-core/voice_core/turns.py` (generic helpers), `backend/dadi/call.py`, `backend/dadi/store.py`
- Test: `voice-core/tests/test_turns.py`, `backend/tests/test_call.py`, `backend/tests/test_store.py`

**Interfaces:**
- Consumes: `PrismaStream`/`SttEvent`, `tts_stream`, `DadiBrain`, `extract_intel`, `merge_intel`, `PERSONAS`, `persona_for_language`, `next_tactic`, `CallState`, `Turn`, `IntelReport`, `audio.*`
- Produces:
  - `turns.is_echo(text: str, recent_agent_lines: list[str], threshold: float = 0.6) -> bool` (normalise: lowercase, strip punctuation and audio tags; `difflib.SequenceMatcher` ratio ≥ threshold against any of the last 2 lines, or either string contained in the other when the transcript has ≥ 3 words)
  - `turns.is_meaningful(text: str) -> bool` (≥ 2 non-space characters after stripping punctuation)
  - `store.Store(path: str)`: `create_call(persona: str) -> str` (uuid hex), `add_turn(call_id, turn: Turn)`, `save_intel(call_id, intel: IntelReport)`, `end_call(call_id, wasted_seconds: float)`, `get_call(call_id) -> dict | None` (includes `turns` and `intel`), `list_calls(limit=50) -> list[dict]`, `totals() -> dict` with keys `calls`, `seconds_wasted`, `mule_ids` (count of distinct UPI + account + phone across calls)
  - `class CallSession(*, send_json: Callable[[dict], Awaitable], send_audio: Callable[[bytes], Awaitable], store: Store, llm, settings, persona_key: str = "auto", stt_factory: Callable[[], PrismaStream-like] | None = None, tts_fn: Callable[..., AsyncIterator[bytes]] | None = None, fillers: dict[str, list[bytes]] | None = None, noise: np.ndarray | None = None, rng: random.Random | None = None)`: `async start()`, `async on_audio(pcm16: bytes)`, `async set_noise(snr_db: float | None)`, `async hangup() -> dict` (returns `{"call_id", "wasted_seconds"}`). Injected factories make it testable without network.
  - Behaviour (pinned):
    - On `start`: create the call row, open STT (factory), send `{"type":"call_started","call_id","persona","started_at"}`, and speak the persona greeting.
    - Uplink: when noise is set, mix `noise` at `snr_db` into the 8 kHz scammer audio (`telephone_band` applied first) before `send_audio`.
    - `speech_start` while Dadi is speaking → cancel the speaking task and send `{"type":"stop_audio"}` (**barge-in**).
    - `processing` while Dadi is idle → after 250 ms, if no reply audio has started, play one random cached filler (not the same as the previous one).
    - `transcript` → ignore if not `is_meaningful` or `is_echo` (vs last 2 Dadi lines); else (on the first meaningful turn when `persona_key == "auto"`, set persona via `persona_for_language`), store the turn, send `{"type":"turn","speaker":"scammer",...}`, start the reply task: sentences from `DadiBrain` → each sentence to `tts_fn` → audio chunks to `send_audio`; send `{"type":"turn","speaker":"dadi","text":<full reply>}` when done; send `{"type":"dadi_speaking","on":true|false}` around it. Start `extract_intel` in the background; when it finishes, save it, update `CallState.captured`, and send `{"type":"intel","intel":...}`.
    - STT stream ends unexpectedly → send `{"type":"status","stt":"reconnecting"}`, reconnect with backoff 0.5, 1, 2, 4, 8 s (max 5 tries) → `{"type":"status","stt":"connected"}` or `"error"`. The call continues.
    - TTS error → log it, retry the sentence once with `model="timbre-v2.5"`, voice `Poorvi` and `strip_audio_tags`; if that also fails, skip the sentence.
    - `wasted_seconds` = time from `start` to `hangup`.
  - **Fallback (only if the Task 2 concurrency check returns 429):** `TurnBasedStt` in `voice_core/turns.py` with the same `events()` interface, using an energy VAD (frame RMS > 0.015 for ≥ 200 ms starts speech; ≥ 600 ms below ends it) plus `transcribe_rest`, and never calling TTS while a REST STT request is in flight.

- [ ] **Step 1: Failing tests** (`FakeStt` yields scripted `SttEvent`s; `fake_tts` yields two 320-byte chunks per sentence; `FakeLLM` from Task 3):
```python
def test_is_echo_and_meaningful():
    assert is_echo("haan beta ek minute", ["हाँ बेटा <coughs>", "haan beta, ek minute!"])
    assert not is_echo("aapka aadhaar number batao", ["haan beta, ek minute!"])
    assert not is_meaningful("  . ") and is_meaningful("ok")

async def test_reply_flow_sends_turns_audio_and_intel(tmp_path):
    out_json, out_audio = [], []
    sess = make_session(tmp_path, out_json, out_audio, stt_events=[connected(), transcript("Main CBI se bol raha hoon, aapka UPI do", "hi-IN")], llm_replies=["हाँ बेटा। रुको ज़रा।", '{"scam_type":"digital_arrest","scam_confidence":0.8}'])
    await sess.start(); await drain(sess)
    kinds = [m["type"] for m in out_json]
    assert "call_started" in kinds and kinds.count("turn") >= 2 and "intel" in kinds
    assert len(out_audio) >= 4

async def test_echo_and_silence_do_not_trigger_reply(tmp_path): ...
    # transcripts "" and Dadi's own greeting → no new dadi turn

async def test_barge_in_sends_stop_audio(tmp_path): ...
    # speech_start while a slow fake_tts is mid-reply → {"type":"stop_audio"} sent, reply task cancelled

async def test_stt_drop_reconnects(tmp_path): ...
    # first FakeStt ends with "closed" unexpectedly → status reconnecting then connected; second stream's transcript still answered

def test_store_totals(tmp_path):
    st = Store(str(tmp_path / "d.db")); c = st.create_call("dadi")
    st.add_turn(c, Turn("scammer", "hi", 1.0)); st.save_intel(c, IntelReport(upi_ids=["a@ybl"], phones=["9876543210"])); st.end_call(c, 125.0)
    assert st.totals() == {"calls": 1, "seconds_wasted": 125.0, "mule_ids": 2}
    assert st.get_call(c)["turns"][0]["text"] == "hi"
```
(Write the 3 `...` tests fully with the same helpers; their assertions are given in the comments.)
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5:** Commit `feat(dadi): realtime call session with fillers, barge-in, echo guard and reconnect`.

---

### Task 7: FastAPI app, filler/noise cache, WebSocket protocol

**Files:**
- Create: `backend/dadi/app.py`, `backend/dadi/assets.py`, `run_backend.ps1`
- Test: `backend/tests/test_app.py`

**Interfaces:**
- Consumes: `CallSession`, `Store`, `get_settings`, `LLM`, `tts_rest`, `PERSONAS`, `build_report`, `audio.*`
- Produces:
  - `assets.load_or_make_fillers(settings, cache_dir: Path) -> dict[str, list[bytes]]` (per persona; synthesises each filler once with `tts_rest` and caches it as `cache/fillers/<persona>/<i>.pcm`; missing key or network → returns what is cached, never raises)
  - `assets.load_or_make_babble(settings, cache_dir) -> np.ndarray` ("call-centre babble": 8 TTS sentences in 4 languages and 4 voices, summed with random offsets plus `pink_noise` at −20 dB, 30 s at 8 kHz, cached as `cache/noise/babble_8k.pcm`; falls back to pink noise)
  - `create_app(settings=None, *, session_factory=None) -> FastAPI`. Routes:
    - `GET /api/health` → `{"gnani_key": bool, "llm_key": bool, "llm_provider": str, "fillers_ready": bool}`
    - `GET /api/personas` → list of `{key, name, age, city, language, voice}`
    - `GET /api/totals` → `Store.totals()`
    - `GET /api/calls`, `GET /api/calls/{id}` (404 if missing), `GET /api/calls/{id}/report` → `build_report(...)`
    - `WS /ws/call`: client sends JSON `{"type":"start","persona":"auto|dadi|paati|thakuma","noise_snr_db":null|number}` then binary PCM16 8 kHz frames; JSON `{"type":"set_noise","snr_db":null|number}`; JSON `{"type":"hangup"}`. Server sends the JSON events of Task 6, binary PCM16 8 kHz audio, and `{"type":"call_ended","call_id","wasted_seconds"}`.
    - Serves `frontend/dist` at `/` when it exists.
  - `run_backend.ps1`: `uv run uvicorn dadi.app:create_app --factory --host 127.0.0.1 --port 8765 --reload`

- [ ] **Step 1: Failing tests** (Starlette `TestClient`, `session_factory` returns a session wired to the fakes from Task 6):
```python
def test_health_and_personas(app_client):
    assert app_client.get("/api/health").status_code == 200
    assert {p["key"] for p in app_client.get("/api/personas").json()} == {"dadi", "paati", "thakuma"}

def test_ws_call_roundtrip(app_client):
    with app_client.websocket_connect("/ws/call") as ws:
        ws.send_json({"type": "start", "persona": "dadi", "noise_snr_db": None})
        assert ws.receive_json()["type"] == "call_started"
        ws.send_bytes(b"\x00" * 1024)
        ws.send_json({"type": "hangup"})
        msgs = drain_ws(ws)
        assert any(m.get("type") == "call_ended" for m in msgs)

def test_report_404(app_client):
    assert app_client.get("/api/calls/nope/report").status_code == 404
```
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5:** Commit `feat(dadi): FastAPI app, websocket call protocol, filler and babble cache`.

---

### Task 8: Frontend: phone + war room + report (ui-kit)

**Files:**
- Create: `voice-core/web/micCapture.js`, `voice-core/web/pcm-worklet.js`, `voice-core/web/pcmPlayer.js`
- Create: `frontend/` from the ui-kit (copy `package.json` deps, `vite.config.js` with proxy `/api` and `/ws` → `http://127.0.0.1:8765` and alias `@voice` → `../voice-core/web`, `styles/`, `src/ui`, `src/lib`, `src/shell` as needed, fonts)
- Create pages: `src/pages/CallRoom.jsx` (split view: `Phone.jsx` left, `WarRoom.jsx` right), `src/pages/Report.jsx` (printable), `src/pages/History.jsx`; widgets `TimeWasted.jsx`, `TranscriptFeed.jsx`, `IntelCard.jsx`, `RedFlags.jsx`, `ScamTypeBadge.jsx`, `TotalsBar.jsx`; `src/net/callSocket.js`

**Interfaces:**
- Consumes: the `/ws/call` protocol and REST routes of Task 7
- Produces:
  - `startMic({ targetRate = 8000, onFrame }) -> Promise<{ stop() }>`: `getUserMedia({audio:{echoCancellation:true, noiseSuppression:false, autoGainControl:true}})`, AudioWorklet downsampling to `targetRate`, `onFrame(ArrayBuffer)` with 512-sample Int16 frames
  - `createPcmPlayer({ sampleRate = 8000 }) -> { play(ArrayBuffer), flush(), level() }` (gapless scheduling with a 60 ms jitter buffer; `flush()` stops everything at once for barge-in; `level()` returns 0..1 for the speaking animation)
  - `openCall({ persona, noiseSnrDb, onEvent }) -> { sendAudio(ab), setNoise(db), hangup() }`
- UI requirements (pinned):
  - The phone shows the persona name and photo-less avatar, call timer, "Call Dadi" and hang-up buttons, a persona picker (Auto, Dadi, Paati, Thakuma), a **noise slider** (Off, 20, 10, 5, 0 dB SNR, labelled "Call-centre noise"), an earphones hint, and the disclaimer label.
  - The war room shows a big **"Scammer ka time barbaad: mm:ss"** counter, the scam-type badge with confidence, a red-flag timeline with quotes, an intel card (UPI, accounts, phones, IFSC, names, agencies, apps; a ✓ when the regex validated it), the live transcript (scammer left, Dadi right, Prisma latency shown on scammer bubbles), an STT status pill, and a totals bar from `/api/totals`.
  - The "Generate complaint report" button opens `/report/:id`, a print-styled page with every `build_report` field and a print button.
- [ ] **Step 1:** Scaffold from the ui-kit and `npm install` (needs network; do it before boarding).
- [ ] **Step 2:** `npm run build` succeeds with no errors.
- [ ] **Step 3:** Manual: run the backend with fakes (`DADI_FAKE=1` env makes `create_app` use the Task 6 fakes) and the frontend `npm run dev`; the call starts, the transcript renders, the timer runs, audio plays from fake chunks, hang-up shows the report link.
- [ ] **Step 4:** Commit `feat(dadi): phone + war room + report UI on the ui-kit`.

---

### Task 9: Live integration and tuning (needs keys + network)

- [ ] Run `uv run python voice-core/scripts/smoke_gnani.py --llm`; record results in `docs/04-test-log.md` (latencies, concurrency result).
- [ ] If concurrency failed, enable the `TurnBasedStt` fallback (Task 6) via `STT_MODE=turn` in `.env` and re-run.
- [ ] Generate fillers and babble (`/api/health` shows `fillers_ready: true`).
- [ ] Listen to all 13 v3.0 female voices on one Dadi line; set each persona's voice and speed by ear in `personas.py`.
- [ ] A 3-minute live call with earphones: no crash; filler within about 0.5 s; first reply audio within about 1.5 s; UPI and phone captured; report generated. Note issues and fix them.
- [ ] Repeat with noise at 5 dB SNR and record Prisma's transcript quality.
- [ ] Commit `chore: live tuning of voices, VAD and prompts`.

---

### Task 10 (P1): Arena: AI scammer vs AI Dadi + noise benchmark

**Files:**
- Create: `backend/dadi/arena.py`, `backend/dadi/scammer_scripts.py`, `frontend/src/pages/Arena.jsx`
- Test: `backend/tests/test_arena.py`

**Interfaces:**
- Produces: `cer(ref: str, hyp: str) -> float` (character error rate after normalisation); `async run_arena(*, scam_type: str, turns: int, snr_db: float | None, llm, settings, emit: Callable[[dict], Awaitable], tts_fn, stt_fn) -> dict` returning `{"turns", "seconds_simulated", "intel", "cer_mean", "persona_breaks"}`. Scammer lines come from the LLM using `scammer_scripts.SCRIPTS[scam_type]` (voice `Harshad`, `hi-IN`), are spoken via `tts_rest`, degraded with `telephone_band` + babble at `snr_db`, transcribed with `transcribe_rest`, and the CER against the intended line is recorded. Dadi replies with `DadiBrain`. Runs strictly one API call at a time. `WS /ws/arena` streams events (same shapes as `/ws/call` plus `{"type":"arena_metric","cer":...}`).
- [ ] Tests: `cer("abc","abc")==0.0`, `cer("abcd","abxd")==0.25`; `run_arena` with fakes returns `turns == 3` and emits ≥ 6 `turn` events.
- [ ] FAIL → implement → PASS → commit `feat(dadi): AI-vs-AI arena with noise benchmark`.

---

### Task 11: Submission pack

**Files:**
- Create: `README.md` (what, why, architecture diagram, Gnani models used: Prisma v3.0 realtime STT, Timbre v3.0 streaming TTS with audio tags, plus Evon if hosted; setup and run; safety design; prior art), `docs/05-interview-prep.md` (every decision with its reason, likely questions and answers, numbers), `docs/06-demo-and-post.md` (60-second shot list, LinkedIn and X post text with #GnaniAI #GreatIndianAIInternshipChallenge and the @Gnani AI tag, submission form answers)
- [ ] Write the three documents; commit `docs: README, interview prep, demo and post kit`.

---

## Self-review notes
- Spec coverage: shared engine (Tasks 1–3, 6), personas and auto-switch (4, 6), tactics/stalling/extraction (4, 5), safety fakes (4), intel and red flags (4, 5), report (5, 7, 8), war room (8), noise slider and 8 kHz (1, 6, 7, 8), latency hiding (6, 7), arena (10), concurrency unknown (2, 6, 9), demo/post (11). P2 items (voice cloning, Evon hosting, real phone number) are deliberately left out of this plan and get their own plan after posting.
- Awaaz and Pukaar get their own plans after Dadi is posted; they reuse `voice_core` (config, audio, gnani clients, llm, turns).
