from pathlib import Path

from src.parser import Parser, SnapshotEvent


def test_snapshot_event_parsing(tmp_path: Path) -> None:
    parser = Parser()
    fixture = Path(__file__).parent / "fixtures" / "sample_player_snapshot.log"
    events = []
    for line in fixture.read_text().splitlines():
        events.extend(parser.parse_line(line))
    snapshots = [event for event in events if isinstance(event, SnapshotEvent)]
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.cards == {12345: 2, 67890: 4}
