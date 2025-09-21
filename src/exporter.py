"""CSV and JSON export helpers."""
from __future__ import annotations

import csv
import json
import os
from typing import List, Sequence, Tuple

from .config import Config
from .store import Store

Row = Tuple[int, int, str, str, str]


class Exporter:
    def __init__(self, config: Config, store: Store) -> None:
        self.config = config
        self.store = store

    def export(self) -> int:
        cards = self.store.get_all_cards()
        metadata = self.store.get_metadata_map()
        rows: List[Row] = []
        for arena_id, quantity in cards.items():
            name, set_code, rarity = metadata.get(arena_id, ("", "", ""))
            rows.append((arena_id, quantity, name, set_code, rarity))
        rows.sort(key=lambda row: (row[2].lower(), row[3].lower(), row[0]))
        self._write_csv(rows)
        self._write_json(rows)
        return len(rows)

    # ------------------------------------------------------------------

    def _write_csv(self, rows: Sequence[Row]) -> None:
        path = self.config.paths.csv_export
        temp = path.with_suffix(path.suffix + ".tmp")
        path.parent.mkdir(parents=True, exist_ok=True)
        with temp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["arena_id", "quantity", "name", "set", "rarity"])
            for row in rows:
                writer.writerow(row)
        os.replace(temp, path)

    def _write_json(self, rows: Sequence[Row]) -> None:
        path = self.config.paths.json_export
        temp = path.with_suffix(path.suffix + ".tmp")
        payload = [
            {
                "arena_id": arena_id,
                "quantity": quantity,
                "name": name,
                "set": set_code,
                "rarity": rarity,
            }
            for arena_id, quantity, name, set_code, rarity in rows
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps(payload, indent=2))
        os.replace(temp, path)


__all__ = ["Exporter", "Row"]
