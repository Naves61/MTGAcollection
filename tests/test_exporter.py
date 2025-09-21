from pathlib import Path

from src.exporter import Exporter
from src.tracker import create_tracker


def test_exporter_writes_atomically(tmp_path: Path) -> None:
    tracker = create_tracker(tmp_path)
    tracker.store.replace_cards({111: 3})
    tracker.store.mark_baseline_complete()
    exporter = Exporter(tracker.config, tracker.store)
    csv_path = tracker.config.paths.csv_export
    csv_path.write_text("corrupted")
    exporter.export()
    assert csv_path.read_text().startswith("arena_id,quantity")
    assert not csv_path.with_suffix(csv_path.suffix + ".tmp").exists()
    json_path = tracker.config.paths.json_export
    assert json_path.exists()
