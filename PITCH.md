# Dadi vs Scammers: one-page pitch

**Don't block scammers. Route them to Dadi.** An AI grandmother on Gnani's voice stack who answers scam calls in Indian languages, wastes the scammer's time, and turns the call into evidence police and banks can act on.

**The problem.** Indians lost about **₹22,845 crore** to cyber fraud in 2024 (I4C); "digital arrest" calls alone took about ₹1,935 crore. Blocking a scam number costs the scammer nothing: he dials the next person, often an elderly parent. And the one thing that could stop him, the mule account the money goes to, is only revealed to a victim who is about to pay.

**Our solution.** Telecoms and families route suspected scam calls to Dadi instead of blocking them.
- **She sounds real, in five languages:** Dadi (Hinglish), Paati (Tanglish), Thakuma (Benglish), Ajji (Kanglish), Ammamma (Tenglish). She mishears "CBI" as "CID", loses her glasses, coughs (Timbre audio tags), and keeps him talking. "Auto" picks the grandmother from the language Prisma hears.
- **She has a mission:** a tactic planner steers every reply toward what the scammer must reveal (UPI ID, bank account + IFSC, WhatsApp number, name and badge) while she reads out only provably invalid fake card and Aadhaar numbers.
- **Every call becomes evidence:** live extraction of UPI IDs (misheard handles repaired), phones, accounts, links and red flags; a one-click complaint draft for cybercrime.gov.in / 1930 / Chakshu; a two-track recording sealed with SHA-256; a freeze list of mule IDs for banks (CSV).
- **She never forgets a voice:** Gnani's voice-cloning model becomes a speaker fingerprint. A scammer who calls back with a new name and script is recognised mid-call (Dadi teases him), and the **Scam Ring Radar** links calls by shared mule ID or shared voice to expose one gang behind many "officers".
- **Beyond calls:** a message checker for scam SMS/WhatsApp in any script, and an AI-vs-AI arena that stress-tests Dadi through noisy 8 kHz phone audio.

**Gnani models, used genuinely.** Prisma v3.0 streaming STT (code-mixed, 8 kHz telephony) for every scammer line; Prisma REST for the noise benchmark; Timbre v3.0 streaming TTS with audio tags (v2.5 fallback) for every word Dadi says; Gnani voice cloning as a voice fingerprint (our most unexpected use). Evon v3.3 plugs in through the same adapter; the live demo uses Groq because Evon has no hosted API.

**Measured on Gnani's live servers.** Prisma final transcripts in 150–280 ms; Timbre first audio in 0.67 s; arena at 10 dB call-centre noise: character error rate 0.13, 0 persona breaks, every digital-arrest red flag caught; voice fingerprint: same scammer 0.93–0.96 vs different voices ≤ 0.78; 0 "I am an AI" admissions under a jailbreak script. More than 100 automated tests.

**Who pays, how it scales.** Telecom operators (route flagged calls to Dadi lines instead of dropping them), bank fraud teams (freeze harvested mule accounts before money moves), I4C / cyber cells (structured reports, scam-script trends), and families. One server runs many parallel calls; every minute costs the scammer a minute too. Gnani's stack can run on-premise, so sensitive fraud intelligence stays in India.

**Safety.** Demo calls are simulated with synthetic data; Dadi never speaks real personal data, never insults or threatens, and a voice match is a lead for investigators, not proof.

**The team also built, on the same engine:** **Pukaar**, a flood-emergency voice line that triages callers in Tamil/Hindi/English and maps them for a control room; and **Apni Awaaz**, which rebuilds a person's own voice from old voice notes (Gnani voice cloning) for people who lost their voice to cancer, stroke or ALS.

**Team:** Nitya Prakash Pandey and Dilavesh Kanz Nidooli · Code: github.com/nitya-prakash-pandey-2005/dadi-vs-scammers · #GnaniAI #GreatIndianAIInternshipChallenge
