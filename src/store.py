"""SQLite persistence for mtga-collection-tracker."""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


@dataclass
class PendingDelta:
    arena_id: int
    delta: int
    ts: str


class Store:
    """Lightweight wrapper around SQLite to keep tracker state durable."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    # -- schema -----------------------------------------------------------------

    def _init_schema(self) -> None:
        with self._conn:  # autocommit transaction
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cards(
                    arena_id INTEGER PRIMARY KEY,
                    quantity INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata(
                    arena_id INTEGER PRIMARY KEY,
                    name TEXT,
                    set_code TEXT,
                    rarity TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS state(
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS pending_deltas(
                    arena_id INTEGER NOT NULL,
                    delta INTEGER NOT NULL,
                    ts TEXT NOT NULL
                );
                """
            )

    # -- card operations --------------------------------------------------------

    def replace_cards(self, cards: Dict[int, int]) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM cards")
            self._conn.executemany(
                "INSERT INTO cards(arena_id, quantity) VALUES(?, ?)",
                [(int(aid), int(qty)) for aid, qty in cards.items()],
            )

    def apply_deltas(self, deltas: Dict[int, int]) -> None:
        if not deltas:
            return
        with self._lock, self._conn:
            for arena_id, delta in deltas.items():
                self._conn.execute(
                    """
                    INSERT INTO cards(arena_id, quantity)
                    VALUES(?, ?)
                    ON CONFLICT(arena_id)
                    DO UPDATE SET quantity = MAX(quantity + excluded.quantity, 0)
                    """,
                    (int(arena_id), int(delta)),
                )

    def set_card_quantity(self, arena_id: int, quantity: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO cards(arena_id, quantity) VALUES(?, ?)\n                 ON CONFLICT(arena_id) DO UPDATE SET quantity = excluded.quantity",
                (int(arena_id), int(quantity)),
            )

    def get_all_cards(self) -> Dict[int, int]:
        cur = self._conn.execute("SELECT arena_id, quantity FROM cards")
        return {int(row["arena_id"]): int(row["quantity"]) for row in cur.fetchall()}

    # -- metadata operations ----------------------------------------------------

    def upsert_metadata(self, rows: Iterable[Tuple[int, str, str, str, str]]) -> None:
        with self._lock, self._conn:
            self._conn.executemany(
                """
                INSERT INTO metadata(arena_id, name, set_code, rarity, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(arena_id) DO UPDATE SET
                    name = excluded.name,
                    set_code = excluded.set_code,
                    rarity = excluded.rarity,
                    updated_at = excluded.updated_at
                """,
                rows,
            )

    def get_metadata_map(self) -> Dict[int, Tuple[str, str, str]]:
        cur = self._conn.execute("SELECT arena_id, name, set_code, rarity FROM metadata")
        return {
            int(row["arena_id"]): (
                row["name"] or "",
                row["set_code"] or "",
                row["rarity"] or "",
            )
            for row in cur.fetchall()
        }

    # -- state ------------------------------------------------------------------

    def get_state(self, key: str, default: Optional[str] = None) -> Optional[str]:
        cur = self._conn.execute("SELECT value FROM state WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def set_state(self, key: str, value: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO state(key, value) VALUES(?, ?)\n                 ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    # -- pending deltas ---------------------------------------------------------

    def add_pending_delta(self, arena_id: int, delta: int, ts: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO pending_deltas(arena_id, delta, ts) VALUES(?, ?, ?)",
                (int(arena_id), int(delta), ts),
            )

    def iter_pending_deltas(self) -> Iterator[PendingDelta]:
        cur = self._conn.execute(
            "SELECT arena_id, delta, ts FROM pending_deltas ORDER BY rowid"
        )
        for row in cur.fetchall():
            yield PendingDelta(int(row["arena_id"]), int(row["delta"]), row["ts"])

    def clear_pending_deltas(self) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM pending_deltas")

    # -- helpers ----------------------------------------------------------------

    def baseline_state(self) -> str:
        return self.get_state("baseline", "missing") or "missing"

    def mark_baseline_complete(self) -> None:
        self.set_state("baseline", "complete")

    def mark_baseline_missing(self) -> None:
        self.set_state("baseline", "missing")


__all__ = ["PendingDelta", "Store"]
