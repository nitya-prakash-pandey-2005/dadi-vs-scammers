# Design: shared voice engine + Project 1 "Dadi vs Scammers"

Status: draft for approval, 8 Nov 2026, 08:30 IST. Deadline: 10 Nov 2026, 23:59 IST.

---

## 0. The big picture: three projects, one engine

All three projects are the same loop at heart: **listen → understand → speak**.

| Project | Who talks to it | What it does |
|---|---|---|
| **01 Dadi vs Scammers** | A scammer calling | Wastes their time as an AI grandmother and extracts mule accounts |
| **02 Awaaz** | A person who lost their voice, and whoever they're talking to | Speaks typed text in the person's own cloned voice and transcribes the other side |
| **03 Pukaar** | A person in a disaster | Calms them, triages them and puts them on a live rescue map |

So we build **one shared engine** (`voice-core/`) and three thin apps on top of it.
**Reason:** writing streaming audio, the Gnani clients and the LLM adapter once means fewer bugs, and projects 2 and 3 become days of work saved, not repeated.

```
The_Great_Indian_AI_Internship_Challenge/
├─ docs/                     research, design, interview prep
├─ voice-core/               shared engine (Python package + browser audio library)
├─ 01-dadi-vs-scammers/      Project 1 (built first, submitted, posted first)
├─ 02-awaaz/                 Project 2
└─ 03-pukaar/                Project 3
```

**Important rule:** "Each participant or team can submit **one** entry." So we cannot submit three entries.
Plan: **Dadi is the entry we post and submit first** (most shareable). Awaaz and Pukaar are built on the same engine afterwards. On 10 Nov we decide between submitting Dadi alone or one umbrella entry, based on what is polished. Either way, all three make you far stronger in the interview ("I built three voice products on one engine").

---

## 1. Shared engine (`voice-core/`)

### 1.1 Parts
| Module | Job |
|---|---|
| `gnani/stt_stream.py` | Prisma realtime WebSocket client: sends 1024-byte PCM frames at real-time pace, receives `speech_start` / `processing` / `transcript` events |
| `gnani/stt_rest.py` | Prisma REST for short clips (≤30 s) |
| `gnani/tts.py` | Timbre WebSocket streaming (first audio fast) and REST |
| `gnani/voice_clone.py` | Gnani voice cloning: create an embedding from a 5 to 30 s sample, then speak with `vachana-vc-v1` |
| `llm.py` | One OpenAI-compatible adapter. Providers: **Groq** (live talk) and **Evon** (self-hosted vLLM/llama.cpp endpoint), switched by config |
| `audio.py` | Resampling, 8 kHz telephone simulation, μ-law, noise mixing at a chosen SNR, WAV read/write |
| `agent.py` | Generic voice-agent loop: transcript in, policy decides, speech out, with **filler clips**, **barge-in** (stop talking when the caller speaks) and turn timing |
| `server.py` helpers | FastAPI WebSocket bridge between browser and engine (browsers cannot set Gnani's auth header, so audio goes through our backend) |
| `web/` (TypeScript) | Mic capture (AudioWorklet → 16 kHz or 8 kHz PCM16), streaming audio player, WebSocket client |

### 1.2 Key engineering decisions (and the reasons)

| Decision | Reason |
|---|---|
| **Our own thin Gnani clients** instead of the `gnani-vachana` SDK | The SDK's streaming client hides the VAD tuning headers we need, and it defaults to the retired `timbre-v2.0`. Writing the protocol ourselves (1024-byte frames at real-time cadence) gives full control and is a strong interview point. |
| **Prisma v3.0** with language hints (`hi-IN,en-IN`) and `format=codemix` | Scammers speak code-mixed Hinglish. Codemix keeps English words (CBI, KYC, UPI, Aadhaar) in Latin script, so entity extraction is reliable. `keyterms` boosts scam vocabulary. |
| **Timbre v3.0** with audio tags | `<coughs>`, `<sigh>`, `<laugh>`, `<slow>`, `<pauses>` give the grandmother a believable personality. That is our "Jugaad" use of Gnani's newest feature. WebSocket streaming starts playback before the full sentence is synthesized. |
| **Groq for live dialogue, Evon pluggable** | Live conversation needs replies in under about 1 s. Groq is free and the fastest; Gnani's own Pipecat example pairs their speech with Groq. Evon has no hosted API, so we plug it in through the same OpenAI-compatible interface once it is hosted on a GPU, and use it first for intel extraction and report writing, where latency matters less. |
| **Hide latency with in-character fillers** | Cached clips like "Haan beta… ek minute…" or "<coughs> haan bolo" play the moment the scammer stops talking, while the LLM and TTS work. A slow grandmother is in character, so latency becomes a feature. |
| **Python 3.12 via `uv`** | Your system Python is 3.14, which is too new for some audio/web packages. `uv` gives a clean, reproducible 3.12 environment in seconds. |
| **React + Vite + TypeScript, styled with your ui-kit** (dark glass/HUD) | Fast to build, and the HUD look suits an "anti-scam war room". |
| **SQLite** for calls, transcripts and intel | Zero setup, one file, enough for a demo and easy to explain. |

### 1.3 The one big technical unknown
Gnani's docs show a 429 error, "Only 1 active request is allowed at a time". If our account allows only one active request, an open STT stream might block a TTS call. **First test once the key arrives:** open STT and TTS at the same time. If that is blocked, the fallback is our own voice-activity detection plus REST STT per utterance, then TTS, run strictly in turn. The engine supports both modes behind one switch.

---

## 2. Project 1: "Dadi vs Scammers"

### 2.1 One-liner
India's first multilingual AI grandmother who picks up scam calls, keeps fraudsters busy in Hinglish, Tanglish or Benglish, and quietly collects their UPI IDs, bank accounts and phone numbers into a ready-to-file cybercrime report.

### 2.2 Why (the interview answer)
- Indians lost about **₹22,845 crore** to cyber fraud in 2024 (I4C, MHA), up from ₹7,465 crore in 2023. "Digital arrest" scams alone took about ₹1,935 crore.
- **Blocking a scam call costs the scammer nothing**; he just dials the next number. **Routing it to Dadi costs him real time**: every minute with Dadi is a minute a real grandmother is safe.
- Scammers must eventually reveal where to send the money: a **mule account or UPI ID**. Police and banks fight scams through mule accounts. Dadi collects them straight from the scammer.
- Deployment story: telecoms already flag and block scam calls. **"Don't block. Route to Dadi."** Banks and telecoms are Gnani's customers.
- Sovereign: scam intelligence is law-enforcement data, so it should stay on an Indian stack (Gnani speech + Evon open weights runnable in a government data centre).
- Prior art, said openly: O2's English "Daisy" (UK, 2024). Ours adds Indian languages and code-mixing, intelligence extraction, complaint drafting for India's systems (cybercrime.gov.in / 1930 / Sanchar Saathi Chakshu) and an AI-vs-AI test arena.

### 2.3 Goals, non-goals, anti-goals
**Goals**
1. A live voice conversation with Dadi in the browser that feels real and funny, with fast turn-taking.
2. A live "war room" dashboard: transcript, a big **"scammer time wasted"** counter, scam type, red flags and extracted intel.
3. A one-click **complaint report** (NCRP-style summary, suspect identifiers, timeline).
4. Something that looks great in a 60-second video.

**Non-goals (for now)**
- A real phone number. No telephony provider can be set up in 48 hours, and the rules forbid using real calls. The architecture shows how it plugs in: Timbre outputs 8 kHz μ-law natively and Prisma is trained on 8 kHz calls.
- Actually filing complaints on government portals (we draft them; a human files).

**Anti-goals (what would make it a failure even if it works)**
- A demo that pretends to be a real scam call. **Every demo call is labelled "Simulated scam call: the scammer is played by an actor or our AI".**
- Leaking anything real. Dadi only ever gives **fake numbers that are provably invalid**: card numbers that fail the Luhn check, Aadhaar numbers that fail the Verhoeff check, and OTPs that go nowhere. They can never match a real person.
- Dadi calling anyone. She only answers; she never dials out.
- A laggy, glitchy demo. Latency hiding and a tested happy path come first.

### 2.4 How a call works
```
Scammer (browser "phone", mic)
   │ PCM16 frames over WebSocket
   ▼
Backend (FastAPI) ──► Prisma v3.0 stream (codemix, hi-IN,en-IN, scam keyterms)
   │                     │ transcript events
   │                     ▼
   │               Dadi brain
   │               ├─ Tactic planner: what to do next (stall, mishear, tangent, "try to pay", ask for UPI…)
   │               ├─ LLM (Groq / Evon): writes Dadi's next line, with audio tags
   │               └─ Intel extractor (after every turn, async): entities + scam type + red flags
   │                     │ reply text
   ▼                     ▼
Filler clip plays at once ──► Timbre v3.0 stream (Dadi's voice) ──► scammer hears Dadi
   │
   └─► Dashboard (WebSocket): transcript, timer, intel, red flags, report
```

### 2.5 Dadi's brain
**Persona cards** (three grandmothers):

| Persona | Language | Voice (Timbre v3.0) | Flavour |
|---|---|---|---|
| **Dadi** (Kamla Devi, 74, Kanpur) | Hinglish | a v3.0 female voice, speed 0.9, `<slow>` (picked by ear in testing) | Grandson Bunty in Bangalore, knee pain, pressure cooker, Sharma ji next door, TV serials |
| **Paati** (Meenakshi, 76, Madurai) | Tanglish | v3.0 female voice | Filter coffee, temple visits, grandson in the US |
| **Thakuma** (Bela Rani, 78, Howrah) | Benglish | v3.0 female voice | Fish market, Rabindra Sangeet, cats |

**Auto language switch:** Prisma's `detected_language_code` on the first sentence picks the persona. If the scammer speaks Tamil, Paati answers.

**Tactic planner** (keeps calls long and pushes towards intel):
- Phases: *Confused opening → Scared and cooperative → "Trying to pay" (stalling) → Extraction → Loop back*.
- Stall tactics: mishearing ("CBI? CID? Arre TV wala CID?"), asking for repeats, reading digits one by one and getting them wrong, glasses lost, door bell, pressure cooker whistle, battery dying, "Bunty se poochh ke batati hoon", long tangents.
- Extraction moves: "Beta, UPI ID dheere dheere bolo, likh rahi hoon", "Account number aur IFSC dobara bolo", "Aapka naam aur badge number kya hai, officer?", "WhatsApp number do, photo bhejti hoon".
- Safety: never real data, never insults, never threats, never admits being an AI. If the scammer turns abusive, stay calm and keep stalling.

**Intel extractor** (runs after each turn, in the background):
- LLM extraction to JSON, cross-checked with validators: UPI ID pattern `name@bank`, Indian mobile `[6-9]\d{9}`, account number (9 to 18 digits), IFSC `[A-Z]{4}0[A-Z0-9]{6}`, URLs and apps (AnyDesk, TeamViewer), claimed agency and name, amount demanded.
- **Scam type:** digital arrest / courier-parcel, KYC/bank block, electricity bill, lottery/KBC, job/task, investment, other, with a confidence score.
- **Red flags** with timestamps: "claims to be police/CBI", "threat of arrest", "demands secrecy", "asks for a remote-access app", "asks to transfer to a 'safe account'", "urgency".

### 2.6 Screens
1. **Scam Line (phone):** a phone-style screen. "Call Dadi" button, persona picker (or auto), a *telephone mode* toggle (8 kHz) and a **noise slider** (adds call-centre background noise to the scammer's audio, to show Prisma works on messy calls).
2. **War Room (dashboard):** live chat-style transcript (scammer vs Dadi), a big timer "Scammer ka ⏱ 12:41 barbaad", scam-type badge, red-flag timeline, an intel card (UPI IDs, accounts, phones, names, each marked validated or unvalidated), and a running total across calls (minutes wasted, mule accounts captured).
3. **Report:** a printable complaint draft (incident summary, suspect identifiers, red flags, transcript excerpt) to save as PDF. A second version in the persona's language is a bonus.
4. **Arena (P1):** AI scammer vs AI Dadi. The scammer bot is voiced by Timbre, degraded to 8 kHz with noise, and transcribed by Prisma, so it is a real audio loop. It runs scripted scam types, measures time wasted, intel captured and persona breaks, and builds a **synthetic scam-call test set** (rule-compliant synthetic data).

### 2.7 Priorities
| Priority | Scope | Target |
|---|---|---|
| **P0** | Live Hinglish call with Dadi (STT stream, LLM, TTS with tags, fillers), War Room with transcript, timer, intel, red flags and scam type, complaint report | **Sun 8 Nov night** |
| **P1** | Paati and Thakuma with auto-switch, 8 kHz plus noise slider, Arena, running totals, polish | Mon 9 Nov midday |
| — | **Record demo video, post on LinkedIn + X** | **Mon 9 Nov evening** |
| **P2** | Real grandmother's voice via Gnani cloning (only with her consent), Evon hosted on GPU for extraction/report, real phone number | if time |

### 2.8 Demo video plan (60 s, Demo Day Drop)
0 to 5 s: hook, "₹22,845 crore. That's what scammers took from Indians last year. So I gave them a new victim." · 5 to 40 s: a live simulated "CBI digital arrest" call; Dadi coughs, mishears and stalls; the timer runs; the scammer reveals a UPI ID and it pops into the intel card · 40 to 52 s: one-click complaint report, running totals · 52 to 60 s: "Built on Gnani Prisma + Timbre. Don't block scammers. Route them to Dadi." with hashtags.

### 2.9 What success looks like
- A 3-minute live call with no crashes; first reply audio about 1.5 s or less after the scammer stops (filler at once).
- The intel card captures a UPI ID and phone number spoken in Hinglish.
- The report is generated in one click.
- Video and post are live by Monday 9 Nov evening.

---

## 3. Projects 2 and 3: scope preview (full designs after Dadi is posted)

**02 Awaaz:** voice banking from 5 to 30 s of old voice notes (Gnani cloning); a quick-phrase board in Indian languages; type or tap to speak in your own voice with emotion; "listen" mode transcribes the other person live (Prisma), and the LLM suggests three quick replies so slow typists keep up; works on speakerphone calls.

**03 Pukaar:** disaster-surge helpline. The caller talks to a calm AI in their language (warm Timbre voice, `<slow>`, grounded NDMA safety instructions). Live triage extracts location, people count, injuries, vulnerable people and needs, and gives a severity score. A live rescue map and incident queue for the control room, with a human always confirming dispatch. A dispatcher types an update in English and the caller hears it in their own language. Drill mode generates synthetic noisy calls (rain, crowd) with Timbre to stress-test Prisma.

---

## 4. Calls I made (check these)
1. Shared engine plus three folders (you asked for three folders; the fourth, `voice-core/`, holds code all three share).
2. Dadi first and posted first; the umbrella-versus-single-entry decision on 10 Nov.
3. Browser "phone" instead of a real phone number for now.
4. Groq for live talk; Evon for extraction/report once hosted.
5. React + Vite + TypeScript with your ui-kit; FastAPI + Python 3.12 backend.
6. Voices picked by ear once your key works.
