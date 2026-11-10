# Dadi vs Scammers: don't block scammers, route them to Dadi

**Team:** Nitya Prakash Pandey & Dilavesh Kanz Nidooli · Built on Gnani **Prisma v3.0** (speech-to-text), **Timbre v3.0** (text-to-speech) and **Gnani voice cloning** · **Live demo:** [dadi-vs-scammers.vercel.app](https://dadi-vs-scammers.vercel.app/) · **Video:** *[video link]* · Code: [github.com/nitya-prakash-pandey-2005/dadi-vs-scammers](https://github.com/nitya-prakash-pandey-2005/dadi-vs-scammers)

## Problem

- Indians lost **₹22,845 crore** to cyber fraud in 2024 ([MHA via Inc42](https://inc42.com/?p=523954)). In 2025, **1,03,488 senior citizens** reported losing ₹4,005 crore ([MHA via ANI](https://newsable.asianetnews.com/india/senior-citizens-women-lost-rs-7-769-crore-to-cyber-fraud-in-2025-articleshow-u9oad8w)).
- Fake "CBI officers" held industrialist S.P. Oswal on Skype for two days and took **₹7 crore** ([Scroll](https://scroll.in/latest/1073888/2-arrested-for-duping-industrialist-sp-oswal-of-rs-7-crore-by-posing-as-officers-of-central-agencies)). Blocking a scam number costs him nothing; he dials the next grandmother.

## Product

An AI grandmother who takes the scam call instead of a real one.

- **She sounds real, in five languages.** Dadi (Hinglish), Paati (Tanglish), Thakuma (Benglish), Ajji (Kanglish), Ammamma (Tenglish). She mishears "CBI" as "CID", coughs (Timbre audio tags) and keeps him talking.
- **She has a mission.** A tactic planner steers every reply towards what he must reveal: UPI ID, bank account + IFSC, phone. She only ever reads out provably invalid fake card and Aadhaar numbers.
- **Her family joins in.** Mid-call she hands the phone to grandson **Bunty** (a second Timbre voice), who "tries to pay" and makes him spell the UPI ID again.
- **Every call becomes evidence.** Live extraction of mule IDs and red flags, a complaint draft for cybercrime.gov.in / 1930 / Chakshu, a two-track recording sealed with SHA-256, and a freeze list for banks.
- **She never forgets a voice.** Gnani voice cloning becomes a voice fingerprint: a repeat scammer is recognised mid-call and the **Scam Ring Radar** links one gang behind many "officers".
- **Guardian mode protects real elders.** On her own call, a live risk score (0–100) and calm spoken warnings in her language, plus a one-tap family alert.

## Proof (live on Gnani's servers, 10 Nov 2026, synthetic scammers)

- **Live call:** Prisma 67–170 ms per line; in 95 s Dadi got his UPI ID, his phone number (spoken in Hindi words) and the AnyDesk demand, with 4 red flags and the UPI mission complete.
- **"She remembers him":** the same scammer voice under a new name matched at **0.956**, and Dadi teased him: *"तब कहते थे पुलिस वाले हैं, अब SBI वाले?"*
- **Family hand-off:** Bunty held the phone for 71 s and extracted the UPI ID and IFSC.
- **Guardian:** the recorded call reaches risk 91, "stop", with 8 reasons shown.
- **256 automated tests** pass; CI is green on GitHub.

## How it is different

Apate.ai (Australia) and O2's Daisy (UK) already waste scammers' time in English. To our knowledge, as of November 2026, no scam-baiting voice agent speaks Indian code-mix and turns the call into UPI/mule identifiers, sealed evidence and a complaint for India's reporting channels, and none recognises a repeat scammer by voice.

## Honesty notes

- All calls are simulated with synthetic voices and fake IDs. The live demo replays real recorded runs, so it uses no API credits.
- The dialogue runs on Groq (`qwen/qwen3.8-27b`); Gnani Evon v3.3 fits the same adapter but has no hosted API.

## One engine, three products

Built on the same voice engine: **Pukaar** (flood helpline, [live](https://pukaar-snowy.vercel.app/)) and **Apni Awaaz** (your own voice back, [live](https://apni-awaaz-kappa.vercel.app/)). #GnaniAI #GreatIndianAIInternshipChallenge
