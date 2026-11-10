# Deploy the demo on Vercel

The Vercel link is the real frontend with its network layer swapped for **recorded data**: REST calls read static JSON
snapshots, the live call and the arena replay recorded WebSocket timelines at real-time pace, and the call plays its
real stereo recording (left = scammer, right = Dadi). No backend, no API keys, no microphone, no cost. A banner on
every page says it is a replay and links to GitHub for running it live.

Why not host the backend: Vercel can't hold long-lived WebSockets or run the Python voice loop, and a public live
backend would let anyone spend the team's Gnani credits.

## Deploy (one time)

1. Push the branch with the demo build to GitHub (it must be on the branch Vercel deploys, usually `main`).
2. In Vercel: **Add New → Project → Import** the `dadi-vs-scammers` GitHub repo.
3. Keep **Root Directory = the repo root** (not `frontend/`): the build needs `voice-core/web`, which sits next to it.
4. Leave framework, build and output settings alone: `vercel.json` sets them
   (`cd frontend && npm install`, `cd frontend && npm run build:demo`, output `frontend/dist`). No environment
   variables are needed. Python is never used.
5. Deploy. The URL is `https://<project-name>.vercel.app` (for example `https://dadi-vs-scammers.vercel.app`).

## Redeploy

Every push to the deployed branch redeploys by itself. To redeploy without a push: Vercel → the project →
**Deployments** → the latest one → **Redeploy**. The demo build has no service worker, so a new deploy shows on
the next page load.

## What the demo build reads

All under `frontend/public/demo/` (copied to `/demo/` in the build):

| File | Used for |
| --- | --- |
| `ws-call.json` | "Call Dadi": the recorded `/ws/call` messages, `[{ "t": seconds, "msg": {...} }]`. Guardian's "Play a recorded call" also reads it: only the scammer's `turn` lines, scored in the browser by `frontend/src/lib/guardian.js` (no `/ws/guard` replay) |
| `call.wav` | the real recording of that same call (stereo, starts with `session_started`); Guardian plays only its left channel (the caller) at real-time speed |
| `ws-arena.json` | "Start AI-vs-AI call": a recorded `/ws/arena` run (`arena_turn`, `intel`, `repeat_caller`, `arena_done`) |
| `ws-bench.json` | optional: a recorded noise benchmark; without it the button is disabled with a note |
| `api/...` | REST snapshots: health, personas, calls, reports, rings, insights, freeze list, CSV feeds, recordings, evidence packs, checker verdicts for the sample messages |

The timeline loader also accepts `{ "events": [...] }`, `data`/`message` instead of `msg`, a JSON string as the
message, and epoch or millisecond times. Binary frames in a capture are skipped. Two replay rules:

- The arena emits each turn as soon as it is computed, so its timestamps are bunched up or stalled. The replay
  re-times it to a reading pace (each turn 2.5 to 4 s after the previous one; intel, mission and repeat-caller
  messages within 1.2 s after the turn before them, in recorded order). The live call keeps its real timing,
  because its audio has to stay in sync.
- A call capture without `call_ended` gets one 1 s after its last message. The committed capture had none (it
  stopped at the last turn), so `call_ended` was added at 95.26 s, the end of the recording, where the hang-up was.

The data committed on 10 Nov 2026: live call `2c5705e9410b` (95 s, featured report with the sealed recording and
evidence pack), the arena rematch (lottery script, Harshad voice, 10 dB, mission UPI, repeat caller), 5 calls in
total, and real checker verdicts for the 3 sample messages.

## Refresh the snapshots from real data

The quickest way is a backend that is already running on the real database: its GET endpoints make no Gnani or
Groq calls, so `--base` can point at it; the only paid calls are the 3 checker POSTs (Groq, once per run). Never
run `--capture-*` against it. Otherwise:

1. Start the backend on the database you want to show (`cache/dadi.db` of that checkout) **without keys**, so it
   only reads the database. An empty key in the environment falls back to the repo's `.env`, so either start it
   from a checkout that has no `.env`, or set the keys to a dummy value:

   ```bash
   GNANI_API_KEY=off GROQ_API_KEY=off EVON_BASE_URL= uv run python -m uvicorn dadi.app:create_app --factory --port 8765
   ```

2. Save every REST response (replaces `frontend/public/demo/api/`):

   ```bash
   cd frontend && npm run snapshot:demo -- --base http://127.0.0.1:8765
   ```

   Options: `--no-audio` / `--no-evidence` skip recordings and evidence packs (size), `--calls id1,id2` keeps
   recordings and packs for those calls only.

   The checker samples need a working LLM (the checker uses only the LLM, no Gnani). Add
   `--check-base http://127.0.0.1:<port>` to post the 3 samples to a backend that has one. Without an LLM the
   script keeps the verdicts already in `api/check` and the demo shows a "try a sample" note for missing ones.

3. Put the live captures next to it: `frontend/public/demo/ws-call.json`, `call.wav` (the recording of that call),
   `ws-arena.json`. The call's `call_id` should be one of the snapshot's calls, so its report opens after hang-up.
4. Check locally, then commit and push:

   ```bash
   cd frontend && npm run build:demo && npx vite preview --port 4173   # open http://localhost:4173
   ```

Fake-mode placeholders (scripted scammer, tone audio) can be captured with
`npm run snapshot:demo -- --base http://127.0.0.1:8880 --capture-call 30 --capture-arena` against a backend started
with `DADI_FAKE=1`. Never point `--capture-*` at a backend with real keys: it would place live calls.

## Normal build

`npm run build` (and the FastAPI-served app) is unchanged: the demo code is removed from it at build time and
`dist/demo` is deleted from it.
