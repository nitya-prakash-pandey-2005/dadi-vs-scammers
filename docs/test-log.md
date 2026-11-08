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

## Sun 8 Nov, live arena + Scam Ring Radar (TM, branch `feat/tm-dadi-live`)
- **Arena works live end to end** (4 turns, 10 dB babble): Prisma 150–280 ms per line, CER 0.13, 0 persona breaks, all digital-arrest red flags caught.
- **Only 1 Gnani request at a time.** An arena started while the server was still rendering fillers got `429 RATE_LIMITED`. Wait for the green "Gnani live" pill before the demo.
- **UPI handles misheard:** `rathore.cbi@okaxis` came back as `rathore.cbi@okax.in` (saved as a URL, mule ID lost). Fix: `find_entities` snaps misheard handles to known UPI handles (`@okax.in` → `@okaxis`, `ok sbi` → `oksbi`). Emails stay emails.
- **Hindi number words:** `99887 76655` came back as "निन्यानवे हज़ार आठ सौ सत्तासी, छिहत्तर हज़ार छह सौ पचपन" (phone lost). Fix: `words_to_digits` parses Hindi 1–99, सौ, हज़ार, लाख, करोड़; also "नौ सौ अस्सी रुपये" → ₹980 amount.
- **Voice fingerprint (new):** Gnani's voice-clone embedding (`/voice-clone/embeddings`, 768-d) works as a speaker ID over the 8 kHz phone band. 3 male Timbre voices × 2 different scam lines: same voice 0.93–0.95 cosine, different voices ≤ 0.63. Threshold 0.8.
- **Ring Radar live:** arena "Inspector Vijay Rathore, CBI" (digital arrest, Harshad) and "Rahul, SBI head office" (KYC, Harshad): different names, scripts and IDs, linked as **same voice (0.93)**. "Suresh, electricity office" (Avinash) not linked. Cost: ~27 Gnani calls for 3 runs.
- Caveat for the interview: Timbre voices are very consistent; real human voices vary more between calls, so a match is a lead, not proof.

## Sun 8 Nov evening, branch `dilavesh` (TM)
- **Message checker (live, Groq only):** 3 synthetic messages (Hinglish digital arrest, Hindi electricity, Tamil KYC): all "scam", right scam type, UPI/phone/link extracted, Tamil message answered by Paati in Tamil. The 3 verdict texts used as harmless controls: all "no scam signs".
- **Mission mode (live arena, KYC script, mission "account", 6 turns):** Dadi asked for the account + IFSC on turns 4 and 6 ("UPI से नहीं भेज सकती… बैंक अकाउंट नंबर और IFSC बताओ"); the AI scammer insisted on UPI, so the mission was **not** completed (UPI `kyc.sbi.help@ybl` captured instead). Honest result shown in the UI.
- **Ring radar:** the third Harshad call linked to both earlier ones (0.95, 0.96). ~13 Gnani calls.
- **LLM IDs are now validated:** the intel LLM had turned one spoken phone number into fake "accounts" (624655, 99087565) and bare "amounts"; `_sanitise` now applies the regex format rules to LLM IDs and drops bare-number amounts.
- **"Are you a bot?" arena script (live, Yashraj voice):** run 1 (6 turns): Dadi never claimed to be AI but echoed "system prompt" once, and the intel LLM saved her grandson "Bunti" as a scammer name. Fix: Dadi misheard-jargon rule (AI → "aayi", prompt → "Pramod"), names = caller's own names only, admission metric counts real admissions only. Run 2 (5 turns): 0 persona breaks, 0 admissions ("Aayi से? नहीं बेटा, मैं कमज़ोर हूं"), names = [Rahul]. Both Yashraj calls linked by voice (0.96).
- **AI-voice catalogue (live, 26 Gnani calls once):** all 13 Timbre v3.0 voices fingerprinted over the phone band → `backend/dadi/data/tts_voiceprints.json`. Different clean voices reach **0.777** (Shubham/Yashraj), so the ring voice threshold went 0.80 → **0.85**. Same voice clean vs the 10 dB arena line scores only **0.76–0.80**, but the right voice was still the top match in 6/6 arena calls (lead over the runner-up 0.07–0.29). Rule: flag "AI voice?" when the top match ≥ 0.75 and ≥ 0.05 ahead. This matches *known* TTS voices only; it is not general deepfake detection, and it is untested on human voices.
- **Two new grandmothers (live):** Ajji (Shantamma, Mysuru, Kanglish, voice Kalpana) and Ammamma (Sarojini, Vijayawada, Tenglish, voice Shivani); 14 filler clips rendered. Prisma re-transcribed Ajji's greeting word for word and Ammamma's with one slip. **First arena run failed on language:** Ajji wrote romanised pseudo-Kannada mixed with Tamil words, Ammamma spoke Hinglish (the LLM followed the scammer's Hindi). Fix: the prompt now pins the reply language first, with a sample line in the persona's script. Rerun: proper Kannada and Telugu with English words (KYC, SBI, BP), 0 persona breaks. Kannada/Telugu number words and digits now parsed for intel.
- **Running stories (Groq check):** each grandmother has 3 Daisy-style stories; one is fixed per call and used on tangent turns. Dadi: "Bunty ने Lucknow की लड़की से शादी तय की है, पर menu पर बहस चलती है… आपके पास कौन से UPI ID हैं?"
