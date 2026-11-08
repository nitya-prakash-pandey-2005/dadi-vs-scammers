# Competitor gaps and idea backlog (Dadi vs Scammers)

Written Sun 8 Nov 2026 (TM). Branch for this work: `dilavesh`.

## 1. What the competitors do

| Product | What it does that Dadi did not (on 8 Nov) |
|---|---|
| **Apate.ai** (Australia; CommBank, TPG Telecom) | Thousands of victim personas (ages, genders, accents, languages). Voice **and** SMS, email, social media. Customers give each bot a **mission** ("get the crypto wallet"). An **insights portal**: impersonated brands, campaigns, trends. Intelligence is **pushed into bank/telco fraud systems**. Outbound agents. TPG diverted ~590,000 calls to it. |
| **O2 Daisy** (UK, 2024) | Long rambling stories (knitting, cat), up to 40 min per call. **Number seeding**: her numbers were put on scammers' target lists. English only, no intelligence output. |
| **Jolly Roger Telephone** (US) | Subscription: users **forward or merge** a scam call into the bot. Detects robocall/IVR and presses keys to stay connected. Several voices, including cloned ones. |
| **Kitboga's bots** (US) | Bots call scam centres at scale. Got a scammer's own AI bot to reveal its prompt: scammers now use AI voices too. |
| **Truecaller** (India) | AI Call Scanner says "AI voice detected" in ~3 s. **Scam Checker**: paste a number, link or message and get a verdict. |
| **CBI chatbot** (India, Apr 2026) | Citizens check if a "notice" or "arrest warrant" is real. |
| **Sanchar Saathi Chakshu / 1930 / cybercrime.gov.in** | The official places to report. Chakshu asks for: medium (call/SMS/WhatsApp), the number, date, category, a screenshot or description. |

What Dadi already does that nobody else does in India: Hinglish/Tanglish/Benglish voice grandmothers on Gnani, audio-tag personality, mule-ID extraction on a noisy 8 kHz line, AI-vs-AI arena with CER and payment-ID recall, complaint draft, and (new) **Scam Ring Radar** with Gnani voice fingerprints.

## 2. Ideas, ranked

Effort: S < 2 h, M < 5 h, L > 5 h. Credits: Gnani calls needed.

### Build now (high demo value, low credits)
| # | Idea | Gap it closes | Award fit | Effort |
|---|---|---|---|---|
| 1 | **Scam Intelligence board**: top impersonated agencies/brands, scam types, ₹ demanded (lakh/crore), mule IDs by bank handle, minutes wasted | Apate insights portal | Real Deal, interview | S |
| 2 | **Freeze list export**: CSV/JSON of every mule ID with its ring, calls and first-seen time; per-call **Chakshu-ready** fields | Apate "push to fraud systems" | Real Deal | S |
| 3 | **Scam Message Checker**: paste an SMS/WhatsApp/"notice" (Hinglish, Tamil, Hindi), get a verdict, red flags, extracted IDs, and a Dadi reply to send back | Truecaller Scam Checker, CBI notice bot, Apate text channel | Real Deal, Crowd Favourite (shareable) | M |
| 4 | **Mission mode**: the operator gives Dadi a goal (UPI / bank account / WhatsApp / name and badge); the tactic planner steers to it and the war room shows "mission complete" | Apate missions | Jugaad Genius, demo | M |
| 5 | **"Are you a bot?" defence**: arena script where the scammer tests Dadi; Dadi deflects in character; persona-break metric | Kitboga showed bots leak prompts | interview | S |
| 6 | **AI-voice flag on scammers**: compare the scammer's voice fingerprint with fingerprints of known TTS voices; "this caller sounds synthetic" | Truecaller AI Call Scanner, voice-clone "digital arrest 2.0" | Jugaad Genius | M (≈13 Gnani calls once) |

### Next (more personas and languages)
| 7 | Two more grandmothers: **Ajji** (Kannada-English) and **Ammamma** (Telugu-English); Timbre v3.0 speaks all 10 languages | Apate persona variety | Main Character, Mixed Vibes | M (≈20 Gnani calls for fillers) |
| 8 | **Daisy-style story memory**: each grandmother has a few running stories (the cat, the knee operation) she returns to | Daisy's long calls | demo | S |

### Roadmap only (say it in the interview; not buildable by 10 Nov)
- **Telco integration**: telcos already flag scam calls; route them to Dadi (TPG did 590,000). Exotel/Twilio SIP to the same `/ws/call` bridge.
- **Number seeding** with scam-baiter communities (how Daisy got calls).
- **Forward/merge a live scam call to Dadi** (Jolly Roger), and IVR/robocall key pressing.
- **Feeds to I4C / bank fraud systems** (STIX or the I4C suspect registry format) once a partner agrees.
- **Evon on a cloud GPU** for sovereign report writing (`docs/EVON-HOSTING.md`).

## Sources
- Apate (TechCrunch, 14 Oct 2026): https://techcrunch.com/2026/10/14/apate-sends-ai-agents-undercover-to-get-scammed-so-they-can-gather-fraud-intelligence/
- CommBank and Apate: https://www.finextra.com/newsarticle/46222/commbank-deploys-batallion-of-ai-powered-bot-profiles-to-chat-with-scammers
- O2 Daisy: https://www.theregister.com/2024/11/15/o2_ai_granny/ and https://www.npr.org/2024/12/10/nx-s1-5220362/daisy-ai-granny-o2-fraud-spam-prevention
- Jolly Roger: https://www.theregister.com/2023/07/03/jolly_roger_telephone_company/ and https://www.techspot.com/news/99264-man-opens-chatgpt-bot-subscription-service-annoy-waste.html
- Kitboga: https://frankonfraud.com/kitboga-gets-ai-scam-bot-to-confess-then-it-starts-oinking/
- Truecaller AI Call Scanner / Scam Checker: https://www.digit.in/news/apps/truecallers-new-ai-call-scanner-can-save-you-from-ai-based-scams.html and https://www.techrepublic.com/article/news-truecaller-scam-checker-apac-india/
- CBI notice chatbot: https://www.convergence-now.com/artificial-intelligence/cbi-ai-chatbot-digital-arrest-scam-verification-india/
- Chakshu: https://www.outlookmoney.com/retirement/financial-planning/how-to-report-suspected-fraud-communication-via-dots-chakshu-facility
- Awards and rules: https://www.gnani.ai/resources/blogs/great-indian-ai-internship-challenge-2026
