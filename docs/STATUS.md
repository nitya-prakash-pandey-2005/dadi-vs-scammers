# Task board: dadi-vs-scammers

Claim a task **before** starting it: put your name and branch in the row and push this file (or tell the others).
If a claimed task shows no pushed progress for 3 hours, anyone may take it over and must note that here.
Owners: **NP** = Nitya · **TM** = teammate (plus AI assistant) · **CL** = Claude on Nitya's laptop (only works while that laptop is online).

The plan with the exact interfaces and tests is in `docs/04-build-plan.md`.

| # | Task (plan section) | Owner | Branch | Status |
|---|---|---|---|---|
| 1 | Config and audio utilities (`voice-core`) | CL | main | done |
| 2 | Gnani clients and smoke test (`voice-core`) | CL | main | done (live run pending keys) |
| 3 | LLM adapter (Groq/Evon) and `eval_llm.py` (`voice-core`) | CL | main | done |
| 4 | Dadi domain: personas, taxonomy, fakes, number words, intel rules, tactics | CL | main | in progress |
| 5 | Brain prompts, intel extraction, report | | | todo |
| 6 | Call session engine | | | todo |
| 7 | FastAPI app and WebSocket protocol | | | todo |
| 8 | Frontend: phone, war room, report | CL | main | done |
| 9 | Live integration and tuning (needs keys) | TM | feat/tm-dadi-live | arena live-tested; UPI-handle + Hindi-number fixes |
| 10 | Arena: AI vs AI and noise benchmark (P1) | CL | main | done (live run pending keys) |
| 11 | README, interview prep, demo and post kit | CL | main | interview prep + demo kit done; README pending results |
| R | Scam Ring Radar: link calls by mule ID or voice fingerprint (Gnani clone embedding) | TM | feat/tm-dadi-live | done, live-tested |
| E | Host Evon (`docs/EVON-HOSTING.md`) | TM | feat/tm-evon | todo |

## Log
- Sun 8 Nov 10:30: repo skeleton, docs and playbook (CL).
- Sun 8 Nov 17:40: arena live run, UPI/number fixes, Scam Ring Radar (TM).
