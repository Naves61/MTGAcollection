#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
BASE_DIR="${MTGA_TRACKER_BASE_DIR:-$HOME}"
SUPPORT_DIR="$BASE_DIR/Library/Application Support/mtga-collection-tracker"
LOG_DIR="$BASE_DIR/Library/Logs/mtga-collection-tracker"
EXPORT_DIR="$BASE_DIR/Documents/MTGA"
VENV_DIR="$SUPPORT_DIR/venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PLIST_DEST="$HOME/Library/LaunchAgents/com.navid.mtga.collection.tracker.plist"

mkdir -p "$SUPPORT_DIR" "$LOG_DIR" "$EXPORT_DIR" "$(dirname "$PLIST_DEST")"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install --upgrade requests orjson >/dev/null

cat "$SCRIPT_DIR/launchd/com.navid.mtga.collection.tracker.plist" \
  | sed "s|@PYTHON@|$VENV_DIR/bin/python|" \
  | sed "s|@TRACKER_SCRIPT@|$SCRIPT_DIR/src/tracker.py|" \
  | sed "s|@LOG_DIR@|$LOG_DIR|" >"$PLIST_DEST"

if command -v launchctl >/dev/null 2>&1; then
  launchctl unload -w "$PLIST_DEST" >/dev/null 2>&1 || true
  launchctl load -w "$PLIST_DEST"
else
  echo "launchctl not available; skipping agent load" >&2
fi

"$VENV_DIR/bin/python" "$SCRIPT_DIR/src/tracker.py" run --once
"$VENV_DIR/bin/python" "$SCRIPT_DIR/src/tracker.py" status
