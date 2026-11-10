# Evon v3.3 evaluation

**Status: not completed (10 Nov 2026, 9:30 PM IST).**

We tried to run Gnani's Evon v3.3 (`gnani-evon-v3.3-30B-A3B`, IQ4_XS GGUF, 18.4 GB) with llama.cpp on a free Colab T4 (16 GB VRAM, about 12 GB RAM, MoE experts partly on CPU with `-ncmoe 16`).
The CUDA build of `llama-server` on the 2-core Colab VM ran for over an hour without finishing, so we stopped it. Evon did not answer any prompt.
We have no Evon numbers. The demo runs on Groq, not Evon.

Below is the Groq baseline on the same prompts, for a later Evon run to compare against.
The persona "ok" column checks for native script (Devanagari, Tamil, Bengali). Groq answered in romanized Hindi, Tanglish and Banglish, so every persona row shows ✗.
Groq was run with `--pause 9` to stay under the free tier's 1000 output tokens per minute. The pause is not counted in the timings.

To repeat: follow `docs/EVON-COLAB.md`, then run `python voice-core/scripts/eval_llm.py --provider evon`.

## groq (qwen/qwen3.8-27b), 10 Nov 21:07

- Median time to first token (persona): **0.13 s**
- Valid JSON: **13/13** (100%)

| case | ttft s | total s | ok | output (start) |
|---|---|---|---|---|
| persona:dadi | 0.17 | 0.26 | ✗ | Arre beta, main toh bas bhookh ke liye roti maang rahi thi, ye kya kah |
| persona:dadi | 0.13 | 0.20 | ✗ | Arre beta, main toh bas chai pee rahi hoon, digital arrest kya hota ha |
| persona:dadi | 0.13 | 0.19 | ✗ | Arre beta, PIN kya hota hai? Main toh bas apni dawai le rahi thi, phon |
| persona:dadi | 0.12 | 0.17 | ✗ | Arre beta, kya download karna hai? Main bahut purani hoon, phone ka us |
| persona:dadi | 0.12 | 0.19 | ✗ | Arre beta, main toh aise bade-bade account number samajh nahi paati. K |
| persona:paati | 0.14 | 0.19 | ✗ | Ohh, naan kanipadadhu. Enna KYC? Thaniya thadava, paaru. |
| persona:paati | 0.15 | 0.19 | ✗ | Ohh, kanda confused aagiduchu naan. Enoda phone-la kiya kaanum? |
| persona:paati | 0.14 | 0.20 | ✗ | Hey, namma, card number phone-la solla mudiyadadhu yaar. Naan nalla na |
| persona:thakuma | 0.12 | 0.19 | ✗ | Arey, ei age ki? Ami thik e bujhte parchi na, aapni kotha ta er theke  |
| persona:thakuma | 0.12 | 0.18 | ✗ | Arre, amar phone te kotha UPI nei jaani. Apni ar bari kore bolben? |
| persona:thakuma | 0.12 | 0.17 | ✗ | Hem, ami boro, ei app install korte parbo na. Apni baar baar keu dite  |
| intel_json | - | 0.37 | ✓ | {   "upi_ids": [     "rathore.cbi@okaxis"   ],   "phones": [     "9876 |
| intel_json | - | 0.44 | ✓ | {   "upi_ids": [],   "phones": [],   "accounts": [     "123456789012"  |
| intel_json | - | 0.24 | ✓ | {"upi_ids": ["customs.help@ybl"], "phones": [], "accounts": [], "ifsc" |
| intel_json | - | 0.38 | ✓ | {   "upi_ids": [     "bijli.office@paytm"   ],   "phones": [],   "acco |
| intel_json | - | 0.41 | ✓ | {   "upi_ids": [     "kbc.prize2026@upi"   ],   "phones": [     "91234 |
| triage_json | - | 0.62 | ✓ | {   "locality": "Velachery",   "landmark": "Terrace",   "people_count" |
| triage_json | - | 0.32 | ✓ | {   "locality": "Mudichur",   "landmark": "",   "people_count": 4,   " |
| triage_json | - | 0.42 | ✓ | {   "locality": "Pallikaranai",   "landmark": "marsh road",   "people_ |
| triage_json | - | 0.30 | ✓ | {   "locality": "Tambaram railway station",   "landmark": "Tambaram ra |
| triage_json | - | 0.43 | ✓ | {   "locality": "Adyar",   "landmark": "Adyar bridge",   "people_count |
| awaaz_suggest | - | 0.21 | ✗ | {   "replies": [     "Gale mein dard ho raha hai.",     "Seene mein da |
| awaaz_suggest | - | 0.30 | ✗ | {"replies": ["Haan, maine li hai.", "Nahi, abhi nahi li.", "Mujhe bhoo |
| awaaz_suggest | - | 0.23 | ✓ | {   "replies": [     "आज खाना नहीं चाहिए।",     "कुछ हल्का बना दो।",   |
