import csv
from pathlib import Path

from src.tracker import create_tracker


def test_delta_sequence_updates_counts(tmp_path: Path) -> None:
    tracker = create_tracker(tmp_path)
    tracker.store.replace_cards({12345: 2, 67890: 1})
    tracker.store.mark_baseline_complete()
    fixture = Path(__file__).parent / "fixtures" / "sample_inventory_deltas.log"
    for line in fixture.read_text().splitlines():
        tracker.process_line(line)
    cards = tracker.store.get_all_cards()
    assert cards == {12345: 3, 67890: 1, 55555: 2}
    csv_path = tracker.config.paths.csv_export
    assert csv_path.exists()
    with csv_path.open() as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["arena_id"] == "55555" and row["quantity"] == "2" for row in rows)
