# Test log

One line per test: date and time, build, scenario, result, latency, notes.

| When (IST) | Build | Scenario | Result | Latency | Notes |
|---|---|---|---|---|---|
| Sun 8 Nov 12:45 | 8d432ee | `smoke_gnani.py --llm --voices` | 4 PASS, 3 FAIL | TTS REST 2.08 s for 5.5 s audio; STT REST 0.52 s; TTS stream first chunk 0.92 s | `stt_stream` closed 1008; Groq `llama-3.3-70b-versatile` no longer exists (404). Concurrency allowed → `STT_MODE=stream`. All 13 v3.0 voices rendered to `cache/voices/`. (TM) |
| Sun 8 Nov 13:05 | feat/tm-core-stt-headers | `smoke_gnani.py --llm` | 7/7 PASS | STT stream 153 ms; LLM first token 0.19 s; TTS stream first chunk 0.67 s | After the fixes below. (TM) |

## Findings (Sun 8 Nov, TM)

- **Prisma streaming now takes exactly one locale.** `language_code: hi-IN,en-IN` fails with "Invalid language_code: exactly one locale is required". `multi_lang_codes` is not accepted on streaming (docs). Fix in `build_stt_headers`: a list becomes `indic-auto` on prisma-v3.0 (first locale on v2.5). REST still accepts lists.
- **Keyterms must be ASCII.** Raw Tamil/Devanagari in the `keyterms` header makes the `websockets` client raise `InvalidHeaderValue` before connecting. Fix: `json.dumps` with `\u` escapes (the docs say so too).
- **8 kHz is fine.** The `connected` message always echoes `sample_rate: 16000`, but 8 kHz audio with `x-sample-rate: 8000` transcribes perfectly (same text as a 16 kHz upsample, 162 ms).
- **Groq model:** the account lists `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`. With Pukaar's real triage prompt, gpt-oss returned empty JSON (reasoning eats `max_tokens`), Qwen extracted all 8 facts from a Tanglish turn in ~0.45 s. New default: `GROQ_MODEL=qwen/qwen3.8-27b`.
