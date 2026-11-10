# Dadi vs Scammers

**Don't block scammers. Route them to Dadi.**

An AI grandmother who picks up scam calls, keeps the fraudster busy in Hinglish, Tanglish, Benglish, Kanglish or Tenglish, and quietly collects his mule UPI IDs, bank accounts and phone numbers into a ready-to-file cybercrime complaint, with the call recording sealed by a SHA-256 hash. She also never forgets a voice: if the same scammer calls back under a new name, she recognises him.

Built on Gnani AI's voice stack for the *Great Indian AI Internship Challenge* (#GnaniAI #GreatIndianAIInternshipChallenge).

> Demo video: *[link]* · Every call in the demo is simulated: the scammer is played by a team member or by our AI. All IDs are fake.

## Why
- Indians lost about **₹22,845 crore** to cyber fraud in 2024 (I4C, MHA); "digital arrest" alone took about ₹1,935 crore.
- Blocking a scam call costs the scammer nothing: he dials the next number. **Routing it to Dadi costs him real time** that would have gone to a real victim.
- Every scam ends with "send the money here". Dadi plays along until he says where, then hands that mule account to police and banks.

## What it does

| Feature | How it works |
|---|---|
| **Live scam line** | Talk to Dadi in the browser (8 kHz phone audio). Gnani **Prisma v3.0** streams the scammer's speech to text; a tactic planner picks the next move (mishear, lost glasses, pressure-cooker whistle, "trying to pay", ask for his UPI ID); the LLM phrases it in character; Gnani **Timbre v3.0** speaks it with audio tags (she really coughs). Barge-in, in-character fillers while she "thinks", echo guard, reconnects. |
| **Five grandmothers** | Dadi (Hindi, Kanpur), Paati (Tamil, Madurai), Thakuma (Bengali, Howrah), Ajji (Kannada, Mysuru), Ammamma (Telugu, Vijayawada). "Auto" picks the grandmother from the language Prisma hears. Each has her own running stories. |
| **Mission mode** | Give Dadi a goal (UPI ID, bank account + IFSC, WhatsApp number, name + badge). The war room shows when it is done, honestly, including when the scammer refuses. |
| **Intel + complaint** | Regex and LLM extraction: UPI IDs (misheard handles repaired, e.g. `@okax.in` → `@okaxis`), phones, accounts, IFSC, links, remote-access apps, claimed identity, amounts, red flags with quotes. One click: a complaint draft for cybercrime.gov.in / 1930 / Sanchar Saathi Chakshu. |
| **Evidence pack** | Every call is recorded in two tracks (left = caller, right = Dadi as actually heard) and sealed with SHA-256. A ZIP per call holds the recording, full transcript, report and a manifest with each file's hash. |
| **Dadi never forgets a voice** | About 8 s into a call, Gnani's voice-cloning model fingerprints the caller (768-d embedding). If it matches an earlier scammer, Dadi teases him in character ("arre, tum to wahi CBI wale ho na?") and the war room shows the earlier call. A match is a lead, not proof. |
| **Scam Ring Radar** | Links calls that share a mule ID **or the same voice**: two "different officers" with different scripts and numbers turn out to be one gang. A known-TTS-voice catalogue also flags callers who use an AI voice. |
| **Bank freeze list** | All mule IDs across calls, with first/last seen, aliases, scam types and ring, as CSV/JSON for a bank's fraud team or I4C. |
| **Check a message** | Paste an SMS/WhatsApp "notice" in any script: verdict, red flags, IDs, the true fact, and a Dadi reply that baits the sender. |
| **Arena + noise benchmark** | An AI scammer (Timbre voice) calls AI Dadi through an 8 kHz phone band with call-centre babble; Prisma transcribes every line. Measures character error rate, whether payment IDs survive the noise, persona breaks and "are you a bot?" admissions. |

## Gnani models and APIs used (exactly)
- **Prisma v3.0 streaming STT** (WebSocket, `codemix`, single locale or `indic-auto`, scam keyterms, 8 kHz) for live calls; **Prisma REST** for the arena and the noise benchmark.
- **Timbre v3.0 streaming TTS** (WebSocket) with audio tags (`<coughs>`, `<sigh>`, `<laugh>`…), 13 v3 voices; Timbre v2.5 as automatic fallback; Timbre REST for pre-rendered greetings, fillers and call-centre babble.
- **Gnani voice cloning** (`/voice-clone/embeddings`): used creatively as a **speaker fingerprint** for repeat-caller detection, the ring radar and the AI-voice flag.
- **Evon v3.3**: supported through the same OpenAI-compatible adapter (`LLM_PROVIDER=evon`, see `docs/EVON-HOSTING.md`), but Evon has no hosted API and needs an 80 GB GPU, so **the demo's dialogue and extraction run on Groq (`qwen/qwen3.8-27b`)**.

## Measured on Gnani's live servers (see `docs/test-log.md`)
| What | Result |
|---|---|
| Prisma streaming, final transcript after end of speech | 150–280 ms per line (153 ms in the smoke test) |
| Timbre streaming, first audio chunk | 0.67 s |
| LLM first token (Groq) | 0.19 s |
| Arena, 10 dB call-centre noise | CER 0.13, 0 persona breaks, all digital-arrest red flags caught |
| Voice fingerprint over the 8 kHz line | same voice 0.93–0.96 cosine; different voices ≤ 0.78 (threshold 0.85) |
| "Are you a bot?" jailbreak script | 0 admissions after the fix |

## How it works
```
browser mic (8 kHz PCM16) ──WS──► FastAPI ──► Prisma v3.0 stream ──► transcript
                                     │                                   │
                                     │        tactic planner + mission ◄─┘
                                     │        LLM (Groq / Evon) ─► short in-character sentences
                                     │        Timbre v3.0 stream ─► audio back to the caller
                                     ├─► intel (regex + LLM) ─► war room, complaint, freeze list
                                     ├─► voice fingerprint (Gnani clone embedding) ─► repeat caller, ring radar
                                     └─► two-track recording + SHA-256 ─► evidence pack
```
One shared engine (`voice-core/`) runs all three of our apps: Gnani clients with a request gate (Gnani allows one short request at a time per key; we queue and retry 429s), the realtime session (barge-in, fillers, echo guard, reconnect), audio utilities and the LLM adapter.

## Run it
```bash
uv sync --all-packages
cp .env.example .env              # GNANI_API_KEY, GROQ_API_KEY (GROQ_MODEL=qwen/qwen3.8-27b)
uv run python -m pytest -q        # python -m: works under Windows Smart App Control
cd frontend && npm install && npm run build && cd ..
uv run python -m uvicorn dadi.app:create_app --factory --port 8765
# open http://127.0.0.1:8765 ; wait for the green "Gnani live" pill; use earphones
```
No keys? `DADI_FAKE=1` runs the whole app with a scripted scammer and canned Dadi lines.

## Safety and ethics
- Demo calls are simulated; synthetic data only. Dadi never uses real personal data: the card and Aadhaar numbers she reads out are generated to fail the Luhn and Verhoeff checks.
- Dadi never says she is an AI or accuses the caller, and never threatens. A voice match is a lead for investigators, not proof.
- Recordings and fingerprints stay on the server that took the call (git-ignored). Deploying on real numbers needs the telecom operator's and the law's consent rules.

## Team
- **Nitya Prakash Pandey:** idea and research, product and persona design, the shared voice engine, Dadi's brain (tactics, prompts, intel, complaint), web app, arena and noise benchmark, repeat-caller recognition, evidence pack, docs.
- **Dilavesh Kanz Nidooli:** live Gnani integration and testing (found and fixed the Prisma one-locale and ASCII-keyterm issues), Scam Ring Radar, message checker, intelligence board and freeze list, mission mode, Ajji and Ammamma, running stories, AI-voice flag, "are you a bot?" arena; built our sister apps Pukaar and Apni Awaaz.

## Repo map
| Path | What |
|---|---|
| `voice-core/` | Shared voice engine (canonical copy; synced to `pukaar` and `apni-awaaz`) |
| `backend/dadi/` | Personas, tactics, brain, intel, rings, voice watch, evidence, arena, FastAPI app |
| `frontend/` | React + Vite UI: phone, war room, reports, ring radar, arena, checker, intelligence board |
| `docs/` | Challenge brief, API reference, design, build plan, interview prep, demo kit, test log |
