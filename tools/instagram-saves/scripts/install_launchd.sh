#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_NAME="com.hairsolutions.instagram-saves-sync.plist"
SOURCE="$REPO_DIR/launchd/${PLIST_NAME}.template"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

mkdir -p "$HOME/Library/LaunchAgents" "$REPO_DIR/logs" "$REPO_DIR/data"
chmod +x "$REPO_DIR/scripts/run_sync.sh"

if [[ -x "$REPO_DIR/.venv/bin/python" ]]; then
  PYTHON="$REPO_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

if ! "$PYTHON" - <<'PY'
from pathlib import Path

env_path = Path(".env")
values = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip()

missing = [
    key
    for key in ("INSTAGRAM_SESSIONID", "INSTAGRAM_CSRFTOKEN", "INSTAGRAM_DS_USER_ID")
    if not values.get(key)
]
if missing:
    print(", ".join(missing))
    raise SystemExit(1)
PY
then
  echo "Refusing to install launchd: required Instagram cookies are missing in $REPO_DIR/.env"
  echo "Add Instagram cookies, run '$REPO_DIR/.venv/bin/instagram-saves sync' successfully once, then rerun this installer."
  exit 1
fi

sed "s#__REPO_DIR__#$REPO_DIR#g" "$SOURCE" > "$TARGET"
launchctl unload "$TARGET" >/dev/null 2>&1 || true
launchctl load "$TARGET"

echo "Installed $PLIST_NAME"
echo "Verify with: launchctl list | grep hairsolutions.instagram-saves-sync"
