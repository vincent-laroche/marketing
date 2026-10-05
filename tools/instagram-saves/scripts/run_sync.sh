#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

mkdir -p "$REPO_DIR/logs" "$REPO_DIR/data"

if [[ -x "$REPO_DIR/.venv/bin/python" ]]; then
  PYTHON="$REPO_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

exec "$PYTHON" -m instagram_saves_engine sync
