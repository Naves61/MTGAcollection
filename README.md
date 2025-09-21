# MTGA Collection Tracker

A headless Magic: The Gathering Arena collection tracker for macOS that tails the
Arena `Player.log`, persists the card collection to SQLite, and exports the
current collection to CSV/JSON files that can be consumed by spreadsheets or
other tooling.  The tracker is intentionally lightweight and designed to run as
a background service started via `launchd`.

## Features

- Poll-based file tailer with log-rotation detection
- Snapshot and delta log parsing resilient to key casing differences
- Durable SQLite store for the collection, metadata, and pending deltas
- Automatic Scryfall metadata import with caching
- Atomic CSV/JSON exports located under `~/Documents/MTGA`
- Minimal scheduler for periodic tasks such as mapping refreshes

## Repository layout

```
mtga-collection-tracker/
  launchd/                         # launchd agent definition
  scripts/                         # helper scripts for installation
  src/                             # tracker implementation
  tests/                           # pytest based test-suite
```

## Development

The project targets Python 3.11.  Create a virtual environment and install
`pytest` when hacking on the codebase:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt  # optional helper if you create one
pytest
```

Running the tracker in the foreground is useful when developing locally:

```bash
python -m src.tracker run --once
```

The helper scripts under `scripts/` illustrate how to install the tracker as a
`launchd` agent on macOS.
