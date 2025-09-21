#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BASE_DIR="${MTGA_TRACKER_BASE_DIR:-}" 

if [ -n "$BASE_DIR" ]; then
  MTGA_TRACKER_BASE_DIR="$BASE_DIR" "$PYTHON_BIN" "$SCRIPT_DIR/src/tracker.py" run --once
else
  "$PYTHON_BIN" "$SCRIPT_DIR/src/tracker.py" run --once
fi
