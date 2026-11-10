# Contributing to Dadi vs Scammers

Thanks for helping. This page covers setup, tests, lint, the demo build and how we write commits.
For how the code fits together, read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); for the REST and
WebSocket protocol, read [`docs/API.md`](docs/API.md).

## Layout

| Path | What it is |
| --- | --- |
| `voice-core/` | The shared voice engine (Gnani Prisma STT, Timbre TTS, request gate, realtime session, LLM adapter). It is the canonical copy: `scripts/sync-core.sh` copies it into the sibling repos. |
| `backend/` | The Dadi app (`dadi` package): agent, intel extraction, voice fingerprints, evidence pack, arena, FastAPI app. |
| `frontend/` | React + Vite web app. `npm run build:demo` makes the static replay demo. |
| `docs/` | Design notes, API and architecture references, test log. |
| `scripts/` | Small tools (OpenAPI export, wireframe/pitch generators, voiceprint builder). |

## Setup

You need [uv](https://docs.astral.sh/uv/) (Python 3.12 is installed by uv) and Node 20 or newer.

```bash
uv sync --all-packages            # Python workspace: voice-core + backend + dev tools
cp .env.example .env              # optional: GNANI_API_KEY, GROQ_API_KEY for live calls
cd frontend && npm ci && cd ..
```

No keys? Set `DADI_FAKE=1` (or `FAKE=1 bash run_backend.sh`) to run the whole app with a scripted scammer,
canned Dadi lines and a soft tone instead of speech. Never commit `.env`, databases (`cache/`), recordings or
media files; `.gitignore` already excludes them.

## Tests

```bash
uv run python -m pytest -q        # all Python tests, fakes only: no keys, no network
```

- Use `python -m pytest`, not `pytest.exe`: Windows Smart App Control can block the generated launcher.
- Tests must never call Gnani or Groq. Use the fakes in `voice-core/voice_core/testing.py`
  (`FakeStt`, `FakeLLM`, `fake_tts`) and `backend/dadi/fakes.py`, or `httpx.MockTransport` for REST clients.
- The Gnani team key allows one short request at a time; the request gate (`voice_core.gnani.gate`) enforces
  this. Tests that exercise retries set `gate.RETRY_DELAYS` to zeros so they stay fast.
- Coverage (optional):
  `uv run --with pytest-cov python -m pytest -q --cov=backend/dadi --cov=voice-core/voice_core --cov-report=term-missing`

## Lint

```bash
uv run --with ruff ruff check backend voice-core scripts
```

The rules live in `[tool.ruff]` in the root `pyproject.toml` (E, F, I, B, UP on Python 3.12). Fix real issues
(unused names, bugs) in the code you touch. Please do not reformat whole files in a feature change: it makes
reviews and merges harder.

## Frontend and the static demo

```bash
cd frontend
npm run build          # the real app, served by the backend at http://127.0.0.1:8765
npm run build:demo     # the static replay demo in frontend/dist (what Vercel deploys, see vercel.json)
```

After `build:demo`, run `npm run build` again so a local backend serves the real app.

## API reference

If you add or change a REST route, regenerate the schema and update `docs/API.md`:

```bash
uv run python scripts/export_openapi.py          # writes docs/api/openapi.json (offline, fake mode)
uv run python scripts/export_openapi.py --check  # exits 1 if the committed file is stale
```

## Before you open a pull request

CI (`.github/workflows/ci.yml`) runs the same checks on every push and pull request to `main`:

1. `uv run python -m pytest -q` is green.
2. `cd frontend && npm run build && npm run build:demo` both pass.
3. Lint has no new warnings in the files you changed.

## Commit style

We use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary` in the imperative,
lower case, no full stop. Common types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `ci`. Scopes we use
include `core` (voice-core), `dadi` (backend), `web` (frontend), `intel`, `tactics`, `arena` and `readme`. Examples:

```text
fix(core): free the Gnani gate when a Timbre stream stalls
test(dadi): evidence pack hashes match the files in the zip
docs(api): document the arena benchmark messages
```

Keep each commit focused and the tests green at every commit.

## Honesty rules for docs and claims

Every number in the README, pitch or docs must come from the code, `docs/test-log.md` or a cited source. All demo
voices and callers are synthetic. Do not put real phone numbers, UPI IDs or personal data in tests or fixtures.
