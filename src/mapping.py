"""Scryfall mapping management."""
from __future__ import annotations

import datetime as _dt
import json
from typing import Dict, Iterable, Optional

try:  # pragma: no cover - optional dependency
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

from .config import Config
from .store import Store

_DEFAULT_BULK_URL = "https://data.scryfall.io/default-cards/default-cards-20240101000000.json"
_UTC = _dt.timezone.utc


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(tz=_UTC)


class MappingManager:
    """Download and persist Scryfall card metadata."""

    def __init__(self, config: Config, store: Store) -> None:
        self.config = config
        self.store = store

    # ------------------------------------------------------------------
    # Public API

    def needs_refresh(self, now: Optional[_dt.datetime] = None) -> bool:
        last_refresh = self.store.get_state("mapping_refreshed_at")
        if not last_refresh:
            return True
        try:
            last_dt = _dt.datetime.fromisoformat(last_refresh)
        except ValueError:
            return True
        now = now or _utcnow()
        return (now - last_dt) >= _dt.timedelta(days=self.config.refresh_days)

    def refresh(self, *, url: str = _DEFAULT_BULK_URL, now: Optional[_dt.datetime] = None) -> int:
        data = self._download(url)
        path = self.config.paths.mapping_cache
        path.write_text(data)
        mapping = json.loads(data)
        timestamp = now or _utcnow()
        count = self._write_mapping(mapping, now=timestamp)
        self.store.set_state("mapping_refreshed_at", timestamp.isoformat())
        return count

    def update_from_cache(self, now: Optional[_dt.datetime] = None) -> int:
        path = self.config.paths.mapping_cache
        if not path.exists():
            return 0
        mapping = json.loads(path.read_text())
        return self._write_mapping(mapping, now=now)

    # ------------------------------------------------------------------
    # internal helpers

    def _download(self, url: str) -> str:
        if requests is None:
            from urllib.request import urlopen

            with urlopen(url) as resp:  # type: ignore[call-arg]
                return resp.read().decode("utf-8")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def _write_mapping(self, mapping: Iterable[dict], now: Optional[_dt.datetime] = None) -> int:
        chosen: Dict[int, dict] = {}
        for card in mapping:
            arena_id = card.get("arena_id")
            if arena_id is None:
                continue
            arena_id = int(arena_id)
            if arena_id in chosen and not self._prefer(card, chosen[arena_id]):
                continue
            chosen[arena_id] = card
        timestamp = (now or _utcnow()).isoformat()
        rows = [
            (
                arena_id,
                str(card.get("name", "")),
                str(card.get("set", "")),
                str(card.get("rarity", "")),
                timestamp,
            )
            for arena_id, card in chosen.items()
        ]
        if rows:
            self.store.upsert_metadata(rows)
        return len(rows)

    def _prefer(self, new: dict, current: dict) -> bool:
        # Avoid promo duplicates if a main set version exists.
        new_set_type = str(new.get("set_type", ""))
        cur_set_type = str(current.get("set_type", ""))
        if cur_set_type == "promo" and new_set_type != "promo":
            return True
        if new_set_type == "promo" and cur_set_type != "promo":
            return False
        # Fallback to whichever entry was updated most recently.
        new_released = str(new.get("released_at", ""))
        cur_released = str(current.get("released_at", ""))
        return new_released >= cur_released


__all__ = ["MappingManager"]
