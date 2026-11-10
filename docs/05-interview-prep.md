# Interview prep: Dadi vs Scammers (and the shared engine)

Read this twice before the interview. Every big decision is here with **the reason**, and the questions you are likely to get come with honest answers. Speak in your own words; don't memorise.

---

## 1. The 30-second pitch
"Indians lost about ₹22,845 crore to cyber fraud in 2024, and when a telecom blocks a scam call, the scammer just dials the next person. So we built Dadi: an AI grandmother on Gnani's voice stack who *answers* scam calls instead. She speaks Hinglish, Tanglish and Benglish, coughs, mishears, loses her glasses, and keeps the scammer busy for as long as possible. Meanwhile she gets him to reveal where the money should go (his mule UPI ID, bank account and phone number), and turns the call into a ready-to-file cybercrime complaint. Every minute he spends with Dadi is a minute he isn't scamming a real grandmother."

## 2. The problem (numbers you should know)
- **₹22,845 crore** lost to cyber fraud in 2024 (I4C, Ministry of Home Affairs), up from about ₹7,465 crore in 2023.
- **Digital arrest** scams (fake CBI/police on video or phone) took about ₹1,935 crore in 2024. The Prime Minister warned about them on national radio.
- 2025: roughly 21–28 lakh fraud complaints (sources differ; say "over 20 lakh").
- **Mule accounts** are how scam money moves. The RBI built *MuleHunter.AI* to find them from transaction patterns; we get them straight from the scammer's mouth.

## 3. Prior art (say it before they do)
- **O2 "Daisy" (UK, Nov 2024):** an English AI granny that kept scammers on the line for up to 40 minutes and had over 1,000 calls. It was a marketing campaign with no intelligence output.
- **What we add:** Indian languages and code-mixing (three personas), **intelligence extraction** (UPI, accounts, phones, IFSC, apps, claimed identity, red flags), a **complaint draft** for India's systems (cybercrime.gov.in, 1930, Sanchar Saathi Chakshu), **noise robustness** on 8 kHz phone audio, an **AI-vs-AI test arena**, and a **sovereign stack** (Gnani speech plus open-weight Evon).
- Scam *detection* apps (Truecaller, Google) warn victims. We do something different: we waste the scammer's time and harvest his payment details.

## 4. Architecture (draw this on paper)
```
Browser "phone" (mic, AudioWorklet → 8 kHz PCM16)
   │ WebSocket (binary audio + JSON events)
FastAPI backend ── VoiceAgentSession (voice-core)
   ├─► Gnani Prisma v3.0 realtime WebSocket: codemix, language hints hi/en/ta/bn, scam keyterms; server-side VAD
   ├─► DadiAgent: tactic planner → LLM (Groq now, Evon pluggable) → short in-character lines with audio tags
   ├─► Gnani Timbre v3.0 WebSocket streaming TTS (sentence by sentence) → audio back to the browser
   └─► background: intel extraction (regex + LLM JSON) → SQLite → live "war room" dashboard
```
**Gnani models used:** Prisma v3.0 (STT realtime + REST), Timbre v3.0 (streaming TTS + audio tags; v2.5 as fallback), and Gnani voice cloning used as a **speaker fingerprint** (repeat callers, Scam Ring Radar, AI-voice flag). **Say it straight if asked about Evon:** the adapter supports it (`LLM_PROVIDER=evon`), but Evon has no hosted API and needs an 80 GB GPU, so the demo ran on Groq (qwen/qwen3.8-27b). Moving to Evon is a config change once it is hosted.

## 5. Decisions and why (most likely interview questions)

| Decision | Why |
|---|---|
| **Voice-first, phone-quality 8 kHz audio** | Real scam calls are phone calls. Prisma is trained on 14M+ hours of 8 kHz telephony, so this shows its real strength. It also uses about a quarter of the bandwidth, which mattered because we built it partly on a train. |
| **Prisma `codemix` format + language hints** | Scammers speak Hinglish. Codemix keeps English words (CBI, UPI, KYC) in Latin script, so our extractors and the LLM read them reliably. The hint list `hi-IN,en-IN,ta-IN,bn-IN` lets one stream handle all three personas. |
| **`keyterms` with scam vocabulary** | It biases Prisma towards words that matter (AnyDesk, IFSC, digital arrest) so they aren't misheard. |
| **Our own thin WebSocket clients instead of the SDK** | We needed the VAD tuning headers and exact control of frames (exactly 1024 bytes at real-time pace). The SDK also defaults to a retired TTS model. Writing the protocol ourselves made it debuggable. |
| **Sentence-level streaming** | The LLM streams; as soon as one sentence is complete it goes to Timbre's streaming TTS, so Dadi starts talking before the full reply exists. |
| **In-character fillers to hide latency** | The STT → LLM → TTS chain takes about 1–1.5 s. A slow, confused grandmother saying "हाँ बेटा… <coughs> एक मिनट…" makes the delay part of the character. Fillers are pre-rendered and cached, so they are instant and free. |
| **Barge-in** | If the scammer talks over her, we cancel her speech and tell the browser to flush its audio buffer. That is how real conversation works. |
| **Echo guard** | The mic can hear Dadi's own voice. Transcripts that closely match her last lines are dropped, using a fuzzy match. We also recommend earphones. |
| **Reconnect with backoff** | Networks drop. The STT socket reconnects (0.5/1/2/4/8 s) and the call continues. |
| **Tactic planner outside the LLM** | A small deterministic planner picks the next move (mishear, glasses, pressure cooker, ask for UPI…). Phases run confused → scared → stall/extract → loop, and moves never repeat within 3 turns. That keeps calls long and varied, and steers towards extraction. The LLM only phrases it. |
| **Regex + LLM for intel** | Regex is precise for UPI, phones, IFSC and accounts, including spoken numbers like "nau aath saat…" that we convert to digits. The LLM understands context (names, agencies, scam type, red flags). We merge both; if the LLM fails, regex still works. Validated items get a ✓. |
| **Provably invalid fake data** | When asked for a card or Aadhaar number, Dadi reads fake ones that **fail the Luhn / Verhoeff checksums**, and the Aadhaar numbers start with 0 or 1, which real ones never do. So we can never leak or collide with a real person's number. |
| **Groq for live talk, Evon pluggable** | Evon v3.3 has no hosted API; it needs an 80 GB GPU (or 4-bit on 24 GB). Live talk needs low latency, so Groq. Everything goes through one OpenAI-compatible adapter, so switching to Evon is a config change (`LLM_PROVIDER=evon`). Extraction and reports go to Evon first (`INTEL_LLM_PROVIDER`) because latency matters less there and Indic understanding matters more. |
| **SQLite** | Zero setup, a single file, enough for a demo; it would move to Postgres in production. |
| **Browser phone, not a real phone number** | Telephony providers in India need KYC (days), and the rules forbid real recorded calls. Production path: SIP/Exotel media streams into the same session at 8 kHz; Timbre can output μ-law directly. |

## 6. Safety and ethics questions
- *"Isn't deceiving people wrong?"* Dadi only **answers** calls to her own numbers (a honeypot). She never calls anyone, never targets real people, never uses real data. The only person deceived is someone actively trying to defraud a pensioner.
- *"Voice cloning misuse?"* Cloning is only used with recorded consent, for a real grandmother who wants to "lend" her voice.
- *"What if a real person calls by mistake?"* The persona is harmless: she just chats. In production, calls come only from numbers flagged by telecom spam systems, and a human reviews every report before filing.
- *"Can scammers detect it?"* Possibly, eventually. That's why the value is two-fold: wasted time **and** the identifiers they reveal before they notice.

## 7. Deployment and business (Gnani cares about this)
- **"Don't block, route to Dadi."** Telecoms already flag millions of spam calls. Instead of dropping them, route flagged calls to Dadi lines.
- **Banks** (Gnani's customers): mule accounts harvested by Dadi go straight to fraud teams to freeze before money moves.
- **Law enforcement:** I4C / state cyber cells get structured reports and scam-script trends.
- **Scale:** one server runs many parallel sessions; cost per minute is STT + TTS + LLM. Every minute costs the scammer a minute too.
- **Sovereignty:** fraud intelligence is sensitive. Gnani's stack can run on-premise, and Evon's open weights can run in a government data centre.

## 8. What you personally did (fill this in honestly)
- Nitya: idea and research, product and persona design, the shared voice engine (Gnani clients, request gate, realtime session), Dadi's brain (tactics, prompts, intel, complaint), web app, arena and noise benchmark, repeat-caller recognition, evidence pack, demo, posts, submission.
- Dilavesh: live Gnani integration and testing (Prisma one-locale and ASCII-keyterm fixes, Groq model choice), Scam Ring Radar, message checker, intelligence board and freeze list, mission mode, Ajji and Ammamma, running stories, AI-voice flag, "are you a bot?" arena; built Pukaar and Apni Awaaz.
- Be honest that you used AI coding assistants. Then show you **understand** every part. Expect to be asked to explain one file in depth: practise `voice-core/voice_core/session.py` and `backend/dadi/tactics.py`.

## 9. Likely technical questions (short answers)
- **Why 1024-byte frames?** Prisma's realtime protocol requires exactly 512 samples of 16-bit mono per frame, sent at real-time pace (64 ms at 8 kHz).
- **How does the server know the user stopped talking?** Prisma's server-side VAD (`x-min-silence-ms` ≈ 450 ms) closes the utterance and sends `processing` then `transcript`. We play a filler on `processing`.
- **How do you measure latency?** Prisma returns `latency` per transcript; we show it on each bubble. We measure the LLM's time to first token and the TTS first-chunk time in `smoke_gnani.py`.
- **What breaks under noise?** We add call-centre babble (generated from Gnani's own TTS voices) at a chosen SNR and watch the transcripts. The Arena measures character error rate per noise level.
- **What if Gnani allows only one request at a time?** It does (live: a second concurrent REST call gets 429). `voice-core/voice_core/gnani/gate.py` puts every short request (TTS, REST STT, voice embedding) through one app-wide slot and retries 429/5xx with 0.5/1/2 s backoff; the long-lived Prisma stream is not gated (an open stream plus TTS was allowed). A stuck holder can't freeze the app: after 20 s a waiter goes ahead and relies on retries.
- **How does Dadi recognise a repeat scammer?** `backend/dadi/voicewatch.py`: while Dadi is silent (so her own echo is not mixed in), the caller's speech is buffered; after 8 s of speech one Gnani voice-clone embedding (768-d) is made and compared by cosine with every earlier call (live: same voice 0.93–0.96, different voices ≤ 0.78, threshold 0.85). On a match, one line is added to Dadi's prompt ("you recognise this voice… tease him once") and the war room shows the earlier call. At hang-up the fingerprint is saved for the ring radar. It's a lead, not proof: real human voices vary more than TTS voices.
- **How is the recording trustworthy?** `backend/dadi/evidence.py`: two tracks on one call clock (left = caller as received, right = Dadi as actually played; a barge-in cuts Dadi's track where playback stopped). The WAV's SHA-256 is stored at hang-up; the evidence ZIP lists every file with its hash, so anyone can check nothing was changed.
- **How would you improve it?** Real telephony (a Twilio/Exotel media-stream bridge is on branch `feat/cl-phone-line`), automatic scam-script clustering, a voice-cloned real grandmother (with her consent), and Evon hosted and fine-tuned on scam transcripts.
