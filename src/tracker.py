"""Main application entrypoint for the MTGA collection tracker."""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional

from .config import Config, load_config
from .exporter import Exporter
from .mapping import MappingManager
from .parser import DeltaEvent, Parser, SnapshotEvent
from .scheduler import Scheduler
from .store import Store
from .tailer import FileTailer
from .version import __version__

_PLAYER_LOG_RELATIVE = Path("Library/Logs/Wizards Of The Coast/MTGA/Unity/Player.log")
_UTC = _dt.timezone.utc


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(tz=_UTC)


class Tracker:
    def __init__(self, config: Config, store: Store, mapping: MappingManager) -> None:
        self.config = config
        self.store = store
        self.mapping = mapping
        self.parser = Parser()
        self.exporter = Exporter(config, store)
        self.scheduler = Scheduler()
        # Mapping refresh once a day by default.
        self.scheduler.add_task("refresh-mapping", config.refresh_days * 86400, self.ensure_mapping)

    # ------------------------------------------------------------------
    # public API

    def ensure_mapping(self) -> None:
        if self.mapping.update_from_cache() == 0 and self.mapping.needs_refresh():
            try:
                self.mapping.refresh()
            except Exception:
                # Metadata refresh should not bring the daemon down; errors are logged by caller.
                pass

    def process_line(self, line: str) -> None:
        for event in self.parser.parse_line(line):
            if isinstance(event, SnapshotEvent):
                self._handle_snapshot(event)
            elif isinstance(event, DeltaEvent):
                self._handle_delta(event)

    def run(self, *, once: bool = False, stop_event: Optional[threading.Event] = None) -> None:
        stop_event = stop_event or threading.Event()
        log_path = self._player_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        tailer = FileTailer(
            log_path,
            active_interval=self.config.active_interval,
            idle_interval=self.config.idle_interval,
        )
        self.ensure_mapping()
        if once:
            self.exporter.export()
            return
        for line in tailer.follow(stop_event.is_set):
            self.process_line(line)
            self.scheduler.run_pending()

    def export_now(self) -> int:
        return self.exporter.export()

    def seed_from_csv(self, csv_path: Path) -> int:
        cards = self._read_seed_csv(csv_path)
        self.store.replace_cards(cards)
        self.store.mark_baseline_complete()
        self._apply_pending_deltas()
        return self.exporter.export()

    def status(self) -> Dict[str, str]:
        counts = len(self.store.get_all_cards())
        baseline = self.store.baseline_state()
        last_snapshot = self.store.get_state("last_snapshot", "")
        return {
            "cards": str(counts),
            "baseline": baseline,
            "last_snapshot": last_snapshot,
        }

    # ------------------------------------------------------------------
    # internal helpers

    def _handle_snapshot(self, event: SnapshotEvent) -> None:
        self.store.replace_cards(event.cards)
        self.store.mark_baseline_complete()
        self.store.set_state("last_snapshot", _utcnow().isoformat())
        self._apply_pending_deltas()
        self.exporter.export()

    def _handle_delta(self, event: DeltaEvent) -> None:
        timestamp = event.raw.get("timestamp") if isinstance(event.raw, dict) else None
        ts = timestamp or _utcnow().isoformat()
        if self.store.baseline_state() != "complete":
            for arena_id, delta in event.deltas.items():
                self.store.add_pending_delta(arena_id, delta, ts)
            return
        self.store.apply_deltas(event.deltas)
        self.exporter.export()

    def _apply_pending_deltas(self) -> None:
        pending = list(self.store.iter_pending_deltas())
        if not pending:
            return
        aggregate: Dict[int, int] = {}
        for item in pending:
            aggregate[item.arena_id] = aggregate.get(item.arena_id, 0) + item.delta
        self.store.apply_deltas(aggregate)
        self.store.clear_pending_deltas()

    def _player_log_path(self) -> Path:
        return self.config.paths.base_dir / _PLAYER_LOG_RELATIVE

    def _read_seed_csv(self, csv_path: Path) -> Dict[int, int]:
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            id_field = None
            qty_field = None
            header_lower = {name.lower(): name for name in reader.fieldnames or []}
            for key in ("arena_id", "grpid", "titleid", "id"):
                if key in header_lower:
                    id_field = header_lower[key]
                    break
            for key in ("quantity", "qty", "count"):
                if key in header_lower:
                    qty_field = header_lower[key]
                    break
            if not id_field or not qty_field:
                raise ValueError("seed CSV must contain arena_id and quantity columns")
            cards: Dict[int, int] = {}
            for row in reader:
                arena_id = int(row[id_field])
                quantity = int(row[qty_field])
                cards[arena_id] = quantity
            return cards


def create_tracker(base_dir: Optional[Path] = None) -> Tracker:
    config = load_config(base_dir)
    store = Store(config.paths.state_db)
    mapping = MappingManager(config, store)
    return Tracker(config=config, store=store, mapping=mapping)


def _cmd_install(args: argparse.Namespace) -> int:
    tracker = create_tracker()
    tracker.ensure_mapping()
    tracker.export_now()
    print("Installation complete. Exports available at", tracker.config.paths.export_dir)
    return 0


def _cmd_uninstall(args: argparse.Namespace) -> int:
    tracker = create_tracker()
    # Leave existing exports and state in place to honour no-data-loss requirement.
    tracker.store.close()
    print("Uninstall does not remove data directories; delete manually if desired.")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    tracker = create_tracker()
    once = getattr(args, "once", False)
    tracker.run(once=once)
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    tracker = create_tracker()
    tracker.seed_from_csv(Path(args.csv))
    print("Seed import applied. Current status:", tracker.status())
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    tracker = create_tracker()
    tracker.export_now()
    print("Export complete ->", tracker.config.paths.csv_export)
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    tracker = create_tracker()
    status = tracker.status()
    for key, value in status.items():
        print(f"{key}: {value}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mtga-collection-tracker")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install", help="install launchd agent")
    install.set_defaults(func=_cmd_install)

    uninstall = sub.add_parser("uninstall", help="remove launchd agent")
    uninstall.set_defaults(func=_cmd_uninstall)

    run = sub.add_parser("run", help="run the tracker in the foreground")
    run.add_argument("--once", action="store_true", help="run initial export only")
    run.set_defaults(func=_cmd_run)

    seed = sub.add_parser("seed", help="import a baseline collection CSV")
    seed.add_argument("csv", help="path to CSV file containing arena_id and quantity columns")
    seed.set_defaults(func=_cmd_seed)

    export = sub.add_parser("export", help="force a CSV/JSON export")
    export.set_defaults(func=_cmd_export)

    status = sub.add_parser("status", help="show tracker status")
    status.set_defaults(func=_cmd_status)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - manual execution
    sys.exit(main())
