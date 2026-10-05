#!/usr/bin/env bash
set -euo pipefail

PLIST_NAME="com.hairsolutions.instagram-saves-sync.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [[ -f "$TARGET" ]]; then
  launchctl unload "$TARGET" >/dev/null 2>&1 || true
  rm "$TARGET"
  echo "Uninstalled $PLIST_NAME"
else
  echo "$PLIST_NAME is not installed"
fi
