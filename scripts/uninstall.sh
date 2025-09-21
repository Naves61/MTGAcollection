#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${MTGA_TRACKER_BASE_DIR:-$HOME}"
SUPPORT_DIR="$BASE_DIR/Library/Application Support/mtga-collection-tracker"
PLIST_DEST="$HOME/Library/LaunchAgents/com.navid.mtga.collection.tracker.plist"

if command -v launchctl >/dev/null 2>&1 && [ -f "$PLIST_DEST" ]; then
  launchctl unload -w "$PLIST_DEST" >/dev/null 2>&1 || true
fi

rm -f "$PLIST_DEST"
rm -rf "$SUPPORT_DIR/venv"

echo "State database and exports preserved in $SUPPORT_DIR"
