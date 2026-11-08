# Run from the repo root. Add -fake for no-keys mode.
param([switch]$fake)
if ($fake) { $env:DADI_FAKE = "1" } else { Remove-Item Env:DADI_FAKE -ErrorAction SilentlyContinue }
uv run uvicorn dadi.app:create_app --factory --host 127.0.0.1 --port 8765
