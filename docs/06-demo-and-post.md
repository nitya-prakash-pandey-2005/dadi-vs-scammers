# Demo video, posts and submission kit

Replace every `[…]` with **real numbers from your recorded call**. The rules forbid misleading demos, so every number must be true.

## 1. Recording setup (15 minutes)
- **Who plays the scammer:** you or a friend, speaking Hinglish into the laptop mic **with earphones** (so Dadi's voice doesn't echo back into the mic).
- **Recorder:** OBS Studio (free) → Display Capture + "Desktop Audio" (Dadi) + "Mic/Aux" (scammer). Or Windows Game Bar (`Win+G`, record with `Win+Alt+R`; turn on "record mic").
- **Settings:** 1920×1080, 30 fps. Browser zoom about 90% so the phone and the war room both fit. Hide bookmarks. Turn on "Do not disturb".
- **Before recording:** the backend shows `fillers_ready: true` at `/api/health`, and one test call works.
- Record **3–4 full calls of 3–5 minutes each**; pick the best one. Cutting for length is fine; inventing or reordering what happened is not. Add a small caption "edited for length".
- **Script ideas for the scammer** (improvise around them): "Main CBI headquarters se Inspector Rathore bol raha hoon… aapke Aadhaar se drugs ka parcel pakda gaya hai… kisi ko mat batana… safe account mein paisa transfer karo… UPI ID likhiye: rathore.cbi@okaxis… mera WhatsApp nau aath saat…". Use **fake** IDs only. For the Tamil clip, a friend says "Madam, naan bank manager pesuren, KYC update pannanum…".

## 2. The 60-second cut (Demo Day Drop award)
| Time | Picture | Sound / caption |
|---|---|---|
| 0–4 s | Black, white text: **"₹22,845 crore."** then "lost to cyber fraud in India in 2024" | Phone ringing |
| 4–8 s | Text: "Blocking scammers doesn't stop them. So I gave them a new victim." → Dadi's call screen | Dadi: "हेलो? <clears throat> कौन बोल रहा है?" |
| 8–38 s | Live split screen: phone + war room. Scammer: "Main CBI se…". Dadi mishears "CID?", coughs, the pressure-cooker excuse. The timer runs. Scammer reveals the UPI ID → **the intel card lights up ✓** | Real call audio, with burnt-in English subtitles |
| 38–46 s | Quick montage: red flags pop in, "Digital arrest 9x%" badge; a 4-second clip of **Paati switching to Tamil** | Captions "Speaks Hinglish · Tanglish · Benglish" |
| 46–54 s | Click "Generate complaint report" → the report with UPI, phone, red flags | "Ready-to-file complaint: cybercrime.gov.in · 1930" |
| 54–60 s | End card: **"Don't block scammers. Route them to Dadi."** · "Built on Gnani AI Prisma + Timbre" · #GnaniAI #GreatIndianAIInternshipChallenge | — |

Subtitles matter: most people watch muted, and many don't speak Hindi. CapCut's auto-captions plus a quick manual fix work fine.

Optional extra shots (branch `dilavesh`; pick one, keep the cut at 60 s):
- **Scam Ring Radar (Jugaad Genius):** two arena calls with the same scammer voice and different scripts → the radar links "Inspector Vijay Rathore, CBI" and "Rahul, SBI" as **same voice (0.93)**; caption "Two different officers. Two different numbers. Same voice: same gang." (Gnani's voice-cloning model used as a voice fingerprint.)
- **Check a message (Crowd Favourite):** paste the Hinglish "digital arrest" WhatsApp sample → "Scam" + the true fact + Dadi's bait reply; caption "Forward it to your parents' phone."
- **Five grandmothers (Main Character / Mixed Vibes):** 3-second clips of Ajji (Kannada) and Ammamma (Telugu) answering the same scam.

## 3. LinkedIn post (native video upload; tag Gnani AI as `@Gnani AI`)
```
My Dadi just kept a fake "CBI officer" busy on the phone for [X] minutes… and got his UPI ID. 👵📞

She isn't real. She's an AI grandmother I built on Gnani AI's voice models for the #GreatIndianAIInternshipChallenge.

Indians lost ₹22,845 crore to cyber fraud in 2024. When a scam call gets blocked, the scammer simply dials the next person.
So instead of blocking them, we give them Dadi.

🎙️ She answers scam calls like a real Indian grandmother, in Hinglish (Dadi), Tanglish (Paati) or Benglish (Thakuma). She coughs, mishears "CBI" as "CID", loses her glasses, and keeps the scammer talking.
🕵️ Meanwhile she "tries to pay", collects the scammer's mule UPI IDs, bank accounts and phone numbers, flags the red flags, and turns the call into a ready-to-file cybercrime complaint.
⏱️ Every minute a scammer spends with Dadi is a minute he isn't scamming a real grandmother.

Built on @Gnani AI's sovereign voice stack:
• Prisma v3.0: real-time speech-to-text for noisy, code-mixed phone audio
• Timbre v3.0: streaming text-to-speech with emotion tags (yes, she really coughs)
[• Evon v3.3: Indic LLM for intelligence extraction — ONLY if we actually used it]

(The call in the video is simulated; I'm playing the scammer 😄)

Would you trust Dadi with your parents' phone? 👇

#GnaniAI #GreatIndianAIInternshipChallenge #CyberSafety #DigitalArrest #VoiceAI #MadeInIndia
```

## 4. X post (≤ 280 characters; attach the video)
```
Scammers called Dadi. She kept them busy for [X] min and got their UPI ID 👵📞
She's an AI grandmother on @GnaniAi's Prisma + Timbre voice models, speaking Hinglish, Tanglish & Benglish.
Don't block scammers. Route them to Dadi.
#GnaniAI #GreatIndianAIInternshipChallenge
```

## 5. Engagement plan (inside the rules)
- **Allowed:** personally asking real friends, family and classmates to watch, react and comment honestly; posting in college groups; your teammate resharing with his own words; replying to every comment quickly.
- **Not allowed (disqualification risk):** buying likes, bots, paid promotion, "like-for-like" exchanges with other participants (engagement pods).
- **Timing:** publish as early as possible, ideally **Mon 9 Nov 7–9 PM IST**. Engagement counts only until the cutoff. **The post must be live before you submit.**
- First comment: the GitHub link (make the repo public just before posting) and one line on how it works.
- Pin the post on your profile. Reply to comments with real answers ("Yes, Paati speaks Tamil, here's how…").

## 6. Submission form answers (paste and edit)
- **Project title:** Dadi vs Scammers: an AI grandmother who scams the scammers
- **The problem you are solving:** Phone scams (digital arrest, KYC, parcel, lottery) cost Indians ₹22,845 crore in 2024. Blocking a scam call costs the scammer nothing; he calls the next victim. There is no system that turns scam calls into wasted scammer time and actionable intelligence (mule accounts).
- **Who will use it:** telecom operators (route spam-flagged calls to Dadi lines instead of blocking them), bank fraud teams (freeze harvested mule accounts), cyber police and I4C (structured reports and scam-script trends), and families (forward suspicious calls to Dadi).
- **Gnani AI models / APIs used:** Prisma v3.0 realtime STT over WebSocket (codemix format, Hindi/English/Tamil/Bengali hints, scam keyterms, 8 kHz telephony), Prisma REST STT, Timbre v3.0 streaming TTS over WebSocket with audio tags (Timbre v2.5 as fallback) [, Gnani voice cloning] [, Evon v3.3 self-hosted for intel extraction].
- **Each member's contribution:** Nitya: [idea, research, persona and product design, prompts and tactics, testing, demo, posts]. [Teammate]: [Evon hosting and evaluation, testing, Pukaar …]. Be accurate; you will both be interviewed separately.
- **Written explanation (about 150 words):** Dadi is a realtime voice agent that answers scam calls as a believable Indian grandmother. The caller's audio streams to Gnani Prisma v3.0, which transcribes noisy, code-mixed phone speech. A tactic planner chooses the next move (stall, mishear, "try to pay", ask for the scammer's UPI ID), and an LLM phrases it in Hinglish, Tanglish or Benglish. Gnani Timbre v3.0 speaks it with audio tags (coughs, sighs) via streaming TTS. Pre-rendered fillers hide latency, and barge-in, echo guards and reconnects keep calls natural on real networks. In the background, regex plus LLM extraction builds an intel report (UPI IDs, accounts, phones, IFSC, remote-access apps, claimed identity, red flags) and a ready-to-file complaint. All personal data Dadi speaks is provably fake (fails Luhn/Verhoeff checks).
- **Nominated posts:** the LinkedIn URL and the X URL (one per platform).
