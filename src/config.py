"""Configuration helpers for mtga-collection-tracker."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

_DEFAULT_REFRESH_DAYS = 7
_DEFAULT_ACTIVE_INTERVAL = 0.5
_DEFAULT_IDLE_INTERVAL = 5.0


@dataclass(frozen=True)
class Paths:
    """Convenience container for well known paths."""

    base_dir: Path
    support_dir: Path
    log_dir: Path
    documents_dir: Path
    export_dir: Path
    state_db: Path
    config_file: Path
    mapping_cache: Path
    csv_export: Path
    json_export: Path


@dataclass
class Config:
    """Resolved configuration values for the tracker."""

    paths: Paths
    refresh_days: int = _DEFAULT_REFRESH_DAYS
    active_interval: float = _DEFAULT_ACTIVE_INTERVAL
    idle_interval: float = _DEFAULT_IDLE_INTERVAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "export_dir": str(self.paths.export_dir),
            "refresh_days": self.refresh_days,
            "active_interval": self.active_interval,
            "idle_interval": self.idle_interval,
        }


def _expand(path: Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(path))))


def determine_base_dir(explicit: Optional[Path] = None) -> Path:
    """Return the base directory for all tracker files."""

    if explicit is not None:
        return _expand(explicit)
    env = os.environ.get("MTGA_TRACKER_BASE_DIR")
    if env:
        return _expand(Path(env))
    # The repository defaults to macOS style layout even on Linux for
    # deterministic tests.  Tests override the base via the environment.
    return Path.home()


def build_paths(base_dir: Optional[Path] = None) -> Paths:
    base = determine_base_dir(base_dir)
    support_dir = base / "Library" / "Application Support" / "mtga-collection-tracker"
    log_dir = base / "Library" / "Logs" / "mtga-collection-tracker"
    documents_dir = base / "Documents" / "MTGA"
    export_dir = documents_dir
    state_db = support_dir / "state.db"
    config_file = support_dir / "config.json"
    mapping_cache = support_dir / "scryfall_default_cards.json"
    csv_export = export_dir / "collection.csv"
    json_export = export_dir / "collection.json"
    return Paths(
        base_dir=base,
        support_dir=support_dir,
        log_dir=log_dir,
        documents_dir=documents_dir,
        export_dir=export_dir,
        state_db=state_db,
        config_file=config_file,
        mapping_cache=mapping_cache,
        csv_export=csv_export,
        json_export=json_export,
    )


def ensure_directories(paths: Paths) -> None:
    """Create all required directories if they do not already exist."""

    for path in (paths.support_dir, paths.log_dir, paths.export_dir):
        path.mkdir(parents=True, exist_ok=True)


def load_config(base_dir: Optional[Path] = None) -> Config:
    """Load configuration from disk, creating defaults if needed."""

    paths = build_paths(base_dir)
    ensure_directories(paths)
    refresh_days = _DEFAULT_REFRESH_DAYS
    active_interval = _DEFAULT_ACTIVE_INTERVAL
    idle_interval = _DEFAULT_IDLE_INTERVAL
    if paths.config_file.exists():
        try:
            data = json.loads(paths.config_file.read_text())
        except json.JSONDecodeError:
            data = {}
        refresh_days = int(data.get("refresh_days", refresh_days))
        if "active_interval" in data:
            active_interval = float(data["active_interval"])
        if "idle_interval" in data:
            idle_interval = float(data["idle_interval"])
        export_dir = _expand(Path(data.get("export_dir", paths.export_dir)))
        if export_dir != paths.export_dir:
            paths = Paths(
                base_dir=paths.base_dir,
                support_dir=paths.support_dir,
                log_dir=paths.log_dir,
                documents_dir=paths.documents_dir,
                export_dir=export_dir,
                state_db=paths.state_db,
                config_file=paths.config_file,
                mapping_cache=paths.mapping_cache,
                csv_export=export_dir / "collection.csv",
                json_export=export_dir / "collection.json",
            )
            ensure_directories(paths)
    else:
        save_config(Config(paths=paths, refresh_days=refresh_days, active_interval=active_interval, idle_interval=idle_interval))
    return Config(paths=paths, refresh_days=refresh_days, active_interval=active_interval, idle_interval=idle_interval)


def save_config(config: Config) -> None:
    config.paths.config_file.write_text(json.dumps(config.to_dict(), indent=2))


__all__ = ["Config", "Paths", "build_paths", "determine_base_dir", "ensure_directories", "load_config", "save_config"]
