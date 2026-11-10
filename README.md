# Dadi vs Scammers

**India's first multilingual AI grandmother who picks up scam calls, keeps fraudsters busy in Hinglish, Tanglish and Benglish, and quietly collects their UPI IDs, bank accounts and phone numbers into a ready-to-file cybercrime report.**

Built on Gnani AI's sovereign voice stack: **Prisma v3.0** (realtime speech-to-text), **Timbre v3.0** (streaming text-to-speech with audio tags) and **Evon v3.3** (LLM).
Entry for Gnani AI's *Great Indian AI Internship Challenge* (#GnaniAI #GreatIndianAIInternshipChallenge).

> **New here? Read `docs/START-HERE.md` first.** Status: under active development (8–10 Nov 2026). Start with `docs/TEAM-PLAYBOOK.md`.

## Why
- Indians lost about **₹22,845 crore** to cyber fraud in 2024 (I4C, MHA).
- Blocking a scam call costs the scammer nothing; he dials the next number. **Routing it to Dadi costs him real time** that would have gone to a real victim.
- Scammers must eventually reveal where the money should go (a mule UPI ID or bank account). Dadi collects those for police and banks.

## Scam Ring Radar
One gang uses many names and many numbers. Dadi links calls that share a mule UPI ID, phone or account, **or the same scammer's voice**: Gnani's voice-cloning model turns ~10 s of the scammer's speech into a 768-d voice fingerprint (same voice 0.93–0.95 cosine over an 8 kHz line, different voices ≤ 0.63). Page: *Scam ring radar*; API: `GET /api/rings`. A voice match is a lead for investigators, not proof.

## Beyond the call (TM, branch `dilavesh`)
- **Check a message:** paste an SMS, WhatsApp message or "notice" in any script; get a verdict, red flags, mule IDs, the true fact, and a Dadi reply that baits the sender.
- **Scam intelligence board:** who scammers pretend to be, scripts, pressure tactics, ₹ demanded; **freeze list** of mule IDs with the bank behind each UPI handle (CSV). Reports carry Chakshu-ready fields.
- **Mission mode:** give Dadi a goal (UPI, account + IFSC, WhatsApp, name + badge); the war room shows when it is done.
- **AI-voice flag:** a scammer whose voice matches a known Timbre voice is marked "AI voice?".
- **"Are you a bot?" arena script:** Dadi stays in character against jailbreak attempts (0 admissions in the live run).
- Competitor gaps and the full idea list: [`docs/07-competitor-gaps-and-ideas.md`](docs/07-competitor-gaps-and-ideas.md).

## Repo map
| Path | What |
|---|---|
| `voice-core/` | Shared voice engine (Gnani clients, audio, LLM adapter). Canonical copy; synced to `apni-awaaz` and `pukaar`. |
| `backend/` | Dadi's brain, intel extraction, call session, FastAPI app |
| `frontend/` | React + Vite UI (phone + war room + report) |
| `docs/` | Rules, API reference, design, build plan, team playbook, Evon hosting, task board |

## Quick start
```bash
uv sync --all-packages
cp .env.example .env        # add GNANI_API_KEY and GROQ_API_KEY
uv run pytest -q
cd frontend && npm install && npm run dev
```

## Safety
Every demo call is simulated (the scammer is played by an actor or our AI). Dadi never uses real personal data. The card and Aadhaar numbers she reads out are generated to be provably invalid (they fail the Luhn and Verhoeff checks).
