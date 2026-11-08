#!/usr/bin/env bash
# Copies the canonical shared engine from this repo (dadi-vs-scammers/voice-core)
# into the sibling repos apni-awaaz and pukaar. Run from anywhere:
#   bash dadi-vs-scammers/scripts/sync-core.sh
# Rule: edit voice-core ONLY in dadi-vs-scammers, then sync and commit in each repo.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(dirname "$HERE")"
for repo in apni-awaaz pukaar; do
  if [ -d "$ROOT/$repo" ]; then
    rm -rf "$ROOT/$repo/voice-core"
    mkdir -p "$ROOT/$repo/voice-core"
    (cd "$HERE/voice-core" && tar --exclude='__pycache__' --exclude='.pytest_cache' -cf - .) | (cd "$ROOT/$repo/voice-core" && tar -xf -)
    echo "synced voice-core -> $repo"
  else
    echo "skip: $ROOT/$repo not found (clone it next to dadi-vs-scammers)"
  fi
done
