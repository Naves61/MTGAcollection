# MTGA Collection Tracker

codex/implement-mtga-collection-tracker-on-macos-m8xth1
A headless Magic: The Gathering Arena collection tracker for macOS that tails
Arena log files, keeps a durable SQLite database of owned cards, and exports the
current collection to CSV/JSON for easy ingestion by spreadsheets or other
tooling. The tracker runs in the background as a `launchd` agent and is designed
to be set-and-forget with a tiny resource footprint.

## Table of contents

1. [Features at a glance](#features-at-a-glance)
2. [System requirements](#system-requirements)
3. [Quick start](#quick-start)
4. [How the tracker works](#how-the-tracker-works)
5. [Outputs and file locations](#outputs-and-file-locations)
6. [Configuration](#configuration)
7. [Operations and troubleshooting](#operations-and-troubleshooting)
8. [Repository layout](#repository-layout)
9. [Development](#development)

## Features at a glance

- Lightweight poll-based log tailer with automatic log-rotation recovery.
- Snapshot and delta parsing tolerant to Arena's changing field casing.
- Durable SQLite store that keeps the active collection, card metadata, and
  pending deltas waiting on a baseline.
- Automatic Scryfall metadata download and caching (default weekly refresh).
- Atomic CSV/JSON exports written under `~/Documents/MTGA` after each update.
- Headless `launchd` service that stays dormant until Arena emits new events.

## System requirements

- macOS 13+ on Apple Silicon (tested on macOS Ventura and Sonoma).
- Python 3.11 (the installer script will create an isolated virtual
  environment under `~/Library/Application Support/mtga-collection-tracker`).
- Disk space: <50 MB for the virtual environment, cache, and database.
- Network access for periodic Scryfall metadata downloads (default once per
  week).

## Quick start

1. **Clone** the repository or download a release archive.
2. **Run the installer script** from Terminal:

   ```bash
   ./scripts/install.sh
   ```

   The installer performs the following:

   - Creates a virtual environment under
     `~/Library/Application Support/mtga-collection-tracker/venv`.
   - Installs runtime dependencies (`orjson`, `requests`, optional `watchdog`).
   - Writes the default configuration file.
   - Copies and loads the `launchd` agent
     (`~/Library/LaunchAgents/com.navid.mtga.collection.tracker.plist`).
   - Runs the tracker once in the foreground to download the Scryfall mapping
     and verify permissions.

3. **Start MTG Arena and open the Collection view once.** Within a minute the
   tracker should detect the snapshot and populate the exports under
   `~/Documents/MTGA`.

To uninstall, run:

```bash
./scripts/uninstall.sh
```

Add the `--purge` flag if you also want to delete the database, cache, and
exports.

## How the tracker works

1. The `launchd` agent starts `src/tracker.py run` whenever you log in.
2. The tracker tails
   `~/Library/Logs/Wizards Of The Coast/MTGA/Unity/Player.log`, reopening the
   file when Arena rotates it.
3. Each log line is scanned for JSON payloads containing either:
   - **Snapshots** (`GetPlayerCards`, `PlayerInventory`, etc.). A snapshot is a
     full list of cards and is treated as authoritative.
   - **Deltas** (`InventoryDelta`, `BoosterOpened`, `CraftCard`, rewards, etc.).
     Deltas adjust the tracked counts incrementally.
4. Parsed data is written to a SQLite database under
   `~/Library/Application Support/mtga-collection-tracker/state.db`. If only
   deltas are seen, they are stored in a `pending_deltas` table until a baseline
   is available.
5. Card names, sets, and rarities are joined from the cached Scryfall
   `default_cards` bulk download. The tracker refreshes the cache weekly (or on
   Arena version changes).
6. After applying a snapshot or deltas, the tracker emits fresh CSV and JSON
   exports atomically (writes to `*.tmp` and renames) so readers never see a
   partially written file.

### Seeding when Arena never emits a snapshot

If your log history only contains deltas, the tracker requires an initial
baseline. Supply one using the CLI once:

```bash
python -m src.tracker seed /path/to/collection.csv
```

The CSV must contain `arena_id` and `quantity` columns (additional columns are
ignored). After seeding, the tracker replays any pending deltas and continues to
track perfectly.

### Useful CLI commands

The installer puts the tracker on your `PATH` via the virtual environment. Run
these commands from the repository or by pointing to the venv interpreter:

- `python -m src.tracker status` — summary of the baseline state, export paths,
  and last update timestamp.
- `python -m src.tracker export` — forces a CSV/JSON export using current DB
  contents.
- `python -m src.tracker run --once` — runs the daemon loop once in the
  foreground (useful for debugging).

## Outputs and file locations

| Path                                                                  | Description                                 |
| --------------------------------------------------------------------- | ------------------------------------------- |
| `~/Documents/MTGA/collection.csv`                                     | Canonical CSV export (arena_id, quantity…). |
| `~/Documents/MTGA/collection.json`                                    | JSON export mirroring the CSV contents.     |
| `~/Library/Application Support/mtga-collection-tracker/state.db`      | SQLite database with cards and metadata.    |
| `~/Library/Application Support/mtga-collection-tracker/config.json`   | Runtime configuration file.                 |
| `~/Library/Application Support/mtga-collection-tracker/scryfall_default_cards.json` | Cached Scryfall bulk data.        |
| `~/Library/Logs/mtga-collection-tracker/agent.log`                    | Rotating log output from the daemon.        |

## Configuration

The default configuration written during installation looks like:

```json
{
  "export_dir": "~/Documents/MTGA",
  "refresh_days": 7
}
```

You may edit `config.json` to change the export directory or adjust the Scryfall
refresh cadence. Changes are picked up the next time the tracker starts.

## Operations and troubleshooting

- **Tracker not running?** Check the agent log at
  `~/Library/Logs/mtga-collection-tracker/agent.log` for Python tracebacks or
  permission errors. Restart the service with
  `launchctl kickstart gui/$UID/com.navid.mtga.collection.tracker`.
- **CSV not updating?** Ensure Arena has emitted new events (open the
  Collection tab). Run `python -m src.tracker status` to confirm the last update
  time and baseline status.
- **Need to refresh metadata now?** Delete the cached Scryfall file and run
  `python -m src.tracker run --once`; the tracker redownloads it on start.
- **Upgrading the tracker?** Pull the latest changes, rerun `./scripts/install.sh`
  to reinstall the virtual environment and reload the agent.

## Repository layout

```
mtga-collection-tracker/
  launchd/                         # launchd agent definition
  scripts/                         # helper scripts for installation
  src/                             # tracker implementation
  tests/                           # pytest based test-suite
```

## Development

codex/implement-mtga-collection-tracker-on-macos-m8xth1
The project targets Python 3.11. Create a virtual environment and install
development dependencies when hacking on the codebase:

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
