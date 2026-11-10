# One Gnani voice engine, three products for India

**Team:** Nitya Prakash Pandey & Dilavesh Kanz Nidooli · Built on Gnani **Prisma v3.0** (speech-to-text), **Timbre v3.0** (text-to-speech) and **Gnani voice cloning** · One shared realtime engine (barge-in, in-character fillers, echo guard, reconnects, a request gate for Gnani's one-request-per-key limit) powers all three.

**Live demos:** Dadi vs Scammers [dadi-vs-scammers.vercel.app](https://dadi-vs-scammers.vercel.app/) · Pukaar [pukaar-snowy.vercel.app](https://pukaar-snowy.vercel.app/) · Apni Awaaz [apni-awaaz-kappa.vercel.app](https://apni-awaaz-kappa.vercel.app/) &nbsp;|&nbsp; **Videos (all three):** *[videos folder link]*

## 1. Dadi vs Scammers: *don't block scammers, route them to Dadi* (flagship)

**Problem.** Indians lost **₹22,845 crore** to cyber fraud in 2024 ([MHA via Inc42](https://inc42.com/?p=523954)); in 2025, **1,03,488 senior citizens** reported losing ₹4,005 crore ([MHA via ANI](https://newsable.asianetnews.com/india/senior-citizens-women-lost-rs-7-769-crore-to-cyber-fraud-in-2025-articleshow-u9oad8w)). A fake "CBI" call took ₹7 crore from industrialist S.P. Oswal ([Scroll](https://scroll.in/latest/1073888/2-arrested-for-duping-industrialist-sp-oswal-of-rs-7-crore-by-posing-as-officers-of-central-agencies)). Blocking a number costs the scammer nothing; he dials the next grandmother.

**Product.** An AI grandmother in Hinglish, Tanglish, Benglish, Kanglish and Tenglish answers the scam call, wastes his time with a tactic planner and steers him into revealing his **UPI IDs and mule accounts**; mid-call she hands the phone to grandson Bunty. Every call becomes a complaint draft for cybercrime.gov.in / 1930 / Chakshu, a SHA-256-sealed two-track recording and a bank freeze list. Gnani voice cloning doubles as a **voice fingerprint**: a scammer who calls back under a new name is recognised mid-call, and the Scam Ring Radar links his calls. Guardian mode warns a real elder during her own call.

**Proof (live, Gnani servers, 10 Nov).** Prisma 67–170 ms per line; in 95 s Dadi got his UPI ID, phone number and AnyDesk demand; the same scammer voice under a new name matched at **0.956** and Dadi said: *"तब कहते थे पुलिस वाले हैं, अब SBI वाले?"*; Bunty extracted the UPI ID and IFSC in 71 s; 256 tests pass.

**Different from** Apate.ai (Australia) and O2's Daisy (UK): to our knowledge, no other scam-baiting voice agent speaks Indian code-mix and turns the call into UPI/mule identifiers, evidence and a complaint for India's reporting channels.

## 2. Pukaar: every flood call answered, in the caller's language

**Problem.** During Cyclone Michaung in Chennai, "almost every call to the complaint cell went unanswered till December 7" ([DT Next](https://www.dtnext.in/news/city/calls-to-govt-helplines-go-unanswered-754073)). In Kerala 2018, 483 people died and volunteers' keralarescue.in received over 1 crore aid and rescue requests ([ThePrint](https://theprint.in/governance/behind-official-kerala-rescue-website-are-1500-techies-working-for-free/102568)).

**Product.** An overflow emergency line that answers when no human can: it calms the caller in Tamil, Hindi, Telugu or English code-mix, gives only approved safety instructions, never promises a time or says "you are safe", scores severity with transparent rules, locates callers from spoken landmarks and merges duplicate callers into one incident on a control-room map. It ranks the best rescue team with reasons (a human confirms every dispatch), interprets live between a Hindi-speaking rescuer and a Tamil caller, and broadcasts alerts in 7 languages as CAP 1.2 (the standard NDMA's SACHET uses).

**Proof.** Severity rose to critical 90 as facts arrived on a live Tamil call; triage accuracy unchanged from clean audio to 0 dB rain; live interpreter 2.3 s one way, 1.6 s back; 277 tests pass.

**Different from** Bengaluru's VANKI and Telangana's AI-ERSS, which assist human 112 call-takers: Pukaar answers the overflow call itself.

## 3. Apni Awaaz: your own voice, back

**Problem.** India had **2,05,878** new lip and oral cavity cancer cases in GLOBOCAN 2024, the most common cancer in Indian men ([IARC](https://gco.iarc.who.int/media/globocan/factsheets/populations/356-india-fact-sheet.pdf)); many survivors lose their voice. Apple Personal Voice supports no Indian language and needs a recording made before the voice is lost ([Apple](https://www.apple.com/ios/feature-availability/)).

**Product.** Gnani voice cloning rebuilds a person's own voice from voice notes they already have, with mandatory consent and one-tap delete. They type (romanised Hindi works), tap quick phrases, say where it hurts on a body map, or pick a suggested reply while live captions show what the nurse says, and the app speaks in **their own voice in 10 Indian languages**. Visit notes read the doctor's instructions back in their voice; switch scanning and an offline SOS cover stroke and ALS users.

**Proof (live).** Voice built in 0.67 s; a sentence in the cloned voice in 1.5–2.2 s; Tamil spoken in a Hindi speaker's cloned voice, re-transcribed by Prisma word for word; 244 Python and 12 JavaScript tests pass.

**Different from** ElevenLabs' Impact Program (a general platform you apply to) and Avaz/Jellow (stock voices): a free, India-first conversation app around your own voice.

**Honesty notes.** All demo calls and voices are synthetic. Live dialogue runs on Groq (`qwen/qwen3.8-27b`); Evon v3.3 plugs into the same adapter but has no hosted API. Code: [dadi-vs-scammers](https://github.com/nitya-prakash-pandey-2005/dadi-vs-scammers) · [pukaar](https://github.com/nitya-prakash-pandey-2005/pukaar) · [apni-awaaz](https://github.com/nitya-prakash-pandey-2005/apni-awaaz) · #GnaniAI #GreatIndianAIInternshipChallenge
