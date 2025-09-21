"""Log parsing utilities for mtga-collection-tracker."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import jsonutil

# Keys that usually indicate a full inventory snapshot.
_SNAPSHOT_KEYS = {"cards", "ownedcards"}
# Keys that indicate delta style payloads.
_DELTA_EVENT_KEYS = {
    "inventorydelta",
    "inventoryupdated",
    "boosteropened",
    "eventreward",
    "rewardgranted",
    "dailywin",
    "craftcard",
    "upgradecard",
    "vaultprogress",
    "vaultreward",
    "wildcardgranted",
}
_ID_KEYS = ("grpid", "grp_id", "titleid", "title_id", "arenaid", "cardid", "mtgaid")
_SNAPSHOT_COUNT_KEYS = ("quantity", "qty", "count")
_DELTA_COUNT_KEYS = ("delta", "quantitydelta", "change", "amount")


@dataclass
class SnapshotEvent:
    cards: Dict[int, int]
    source: str
    raw: Dict[str, Any]


@dataclass
class DeltaEvent:
    deltas: Dict[int, int]
    source: str
    raw: Dict[str, Any]


class Parser:
    """Extract JSON payloads from MTGA log lines."""

    def __init__(self) -> None:
        pass
    # ------------------------------------------------------------------
    # public API

    def parse_line(self, line: str) -> List[Any]:
        events: List[Any] = []
        for snippet in self._extract_json_strings(line):
            try:
                data = jsonutil.loads(snippet)
            except ValueError:
                continue
            events.extend(self._parse_json_object(data))
        return events

    # ------------------------------------------------------------------
    # internal helpers

    def _extract_json_strings(self, text: str) -> Iterator[str]:
        depth = 0
        start = None
        for idx, char in enumerate(text):
            if char == "{":
                if depth == 0:
                    start = idx
                depth += 1
            elif char == "}":
                if depth == 0:
                    continue
                depth -= 1
                if depth == 0 and start is not None:
                    snippet = text[start : idx + 1]
                    start = None
                    yield snippet

    def _parse_json_object(self, obj: Any) -> List[Any]:
        if not isinstance(obj, dict):
            return []
        delta_events: List[DeltaEvent] = []
        for source, deltas in self._extract_delta_events(obj):
            if deltas:
                delta_events.append(DeltaEvent(deltas=deltas, source=source, raw=obj))
        if delta_events:
            return delta_events
        # Snapshots are rare but easy to detect: a dict containing a list under
        # a key "Cards" or "OwnedCards" with absolute quantities.
        snapshot_cards = self._extract_snapshot_cards(obj)
        if snapshot_cards:
            return [SnapshotEvent(snapshot_cards, source="snapshot", raw=obj)]
        return []

    # ------------------------------------------------------------------
    # snapshot helpers

    def _extract_snapshot_cards(self, obj: Dict[str, Any]) -> Dict[int, int]:
        card_entries = self._find_card_entries(obj, keys=_SNAPSHOT_KEYS)
        cards: Dict[int, int] = {}
        for entry in card_entries:
            arena_id = self._extract_arena_id(entry)
            if arena_id is None:
                continue
            quantity = self._extract_first_int(entry, _SNAPSHOT_COUNT_KEYS)
            if quantity is None:
                continue
            cards[arena_id] = max(int(quantity), 0)
        return cards

    # ------------------------------------------------------------------
    # delta helpers

    def _extract_delta_events(self, obj: Dict[str, Any]) -> Iterator[Tuple[str, Dict[int, int]]]:
        for key, value in self._walk_dict(obj):
            if key in _DELTA_EVENT_KEYS:
                deltas = self._normalise_deltas(value)
                if deltas:
                    yield key, deltas

    def _normalise_deltas(self, value: Any) -> Dict[int, int]:
        deltas: Dict[int, int] = {}
        entries = self._collect_card_like_entries(value)
        for entry, multiplier in entries:
            arena_id = self._extract_arena_id(entry)
            if arena_id is None:
                continue
            delta = self._extract_first_int(entry, _DELTA_COUNT_KEYS)
            if delta is not None:
                change = int(delta) * multiplier
            else:
                quantity = self._extract_first_int(entry, _SNAPSHOT_COUNT_KEYS)
                if quantity is None:
                    continue
                change = int(quantity) * multiplier
            if change == 0:
                continue
            deltas[arena_id] = deltas.get(arena_id, 0) + change
        return deltas

    def _collect_card_like_entries(self, value: Any) -> List[Tuple[Dict[str, Any], int]]:
        results: List[Tuple[Dict[str, Any], int]] = []
        if isinstance(value, dict):
            for key, inner in value.items():
                lower = key.lower()
                if lower in ("adds", "addedcards", "grantedcards"):
                    results.extend([(item, 1) for item in self._ensure_list(inner)])
                elif lower in ("removes", "removedcards", "spentcards"):
                    results.extend([(item, -1) for item in self._ensure_list(inner)])
                elif lower in ("changes", "cards", "deltas"):
                    results.extend([(item, 1) for item in self._ensure_list(inner)])
                else:
                    results.extend(self._collect_card_like_entries(inner))
        elif isinstance(value, list):
            for item in value:
                results.extend(self._collect_card_like_entries(item))
        return [(entry, multiplier) for entry, multiplier in results if isinstance(entry, dict)]

    # ------------------------------------------------------------------
    # generic traversal helpers

    def _find_card_entries(self, obj: Any, keys: Iterable[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        key_set = {k.lower() for k in keys}
        if isinstance(obj, dict):
            for key, value in obj.items():
                lower = key.lower()
                if lower in key_set:
                    for item in self._ensure_list(value):
                        if isinstance(item, dict):
                            results.append(item)
                else:
                    results.extend(self._find_card_entries(value, keys))
        elif isinstance(obj, list):
            for item in obj:
                results.extend(self._find_card_entries(item, keys))
        return results

    def _walk_dict(self, obj: Any) -> Iterator[Tuple[str, Any]]:
        if isinstance(obj, dict):
            for key, value in obj.items():
                yield key.lower(), value
                yield from self._walk_dict(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from self._walk_dict(item)

    def _ensure_list(self, value: Any) -> List[Any]:
        if isinstance(value, list):
            return value
        return [value]

    def _extract_arena_id(self, entry: Dict[str, Any]) -> Optional[int]:
        for key in _ID_KEYS:
            if key in entry:
                return int(entry[key])
        for key, value in entry.items():
            if isinstance(key, str) and key.lower() in _ID_KEYS:
                return int(value)
        # As a fallback, arena ID might be stored under the canonical key
        # "id" when the payload only contains card information.
        if "id" in entry:
            try:
                return int(entry["id"])
            except (TypeError, ValueError):
                return None
        return None

    def _extract_first_int(self, entry: Dict[str, Any], keys: Iterable[str]) -> Optional[int]:
        for key in keys:
            value = entry.get(key)
            if value is None:
                value = entry.get(key.capitalize())
            if value is None:
                value = entry.get(key.upper())
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None


__all__ = ["Parser", "SnapshotEvent", "DeltaEvent"]
