"""Export the backend's OpenAPI schema to docs/api/openapi.json.

Runs fully offline: the app is built in-process in fake mode (DADI_FAKE=1) with a
throwaway cache folder, so no API keys, network calls or server are needed.
WebSocket routes (/ws/call, /ws/arena) are not part of OpenAPI; see docs/API.md.

Usage (from the repo root):  uv run python scripts/export_openapi.py [--check]
  --check  exit 1 if the committed file is out of date (useful in CI).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "api" / "openapi.json"


def build_schema() -> dict:
    os.environ["DADI_FAKE"] = "1"
    from dadi.app import create_app
    from voice_core.config import Settings

    # ignore_cleanup_errors: the app keeps its SQLite file open, which Windows will not delete
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        app = create_app(Settings(cache_dir=Path(tmp) / "cache"))
        return app.openapi()


def main() -> int:
    schema = build_schema()
    text = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv[1:]:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(ROOT)} is out of date: run `uv run python scripts/export_openapi.py`")
            return 1
        print("openapi.json is up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} ({len(schema.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
