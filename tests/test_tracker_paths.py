from src.tracker import create_tracker


def test_player_log_path_prefers_existing_primary(tmp_path):
    tracker = create_tracker(base_dir=tmp_path)
    try:
        log_dir = tmp_path / "Library/Logs/Wizards Of The Coast/MTGA"
        log_dir.mkdir(parents=True, exist_ok=True)
        expected = log_dir / "Player.log"
        expected.write_text("test")

        assert tracker._player_log_path() == expected
    finally:
        tracker.store.close()


def test_player_log_path_uses_unity_variant_when_present(tmp_path):
    tracker = create_tracker(base_dir=tmp_path)
    try:
        unity_dir = tmp_path / "Library/Logs/Wizards Of The Coast/MTGA/Unity"
        unity_dir.mkdir(parents=True, exist_ok=True)
        expected = unity_dir / "Player.log"
        expected.write_text("test")

        assert tracker._player_log_path() == expected
    finally:
        tracker.store.close()


def test_player_log_path_defaults_to_primary_location(tmp_path):
    tracker = create_tracker(base_dir=tmp_path)
    try:
        expected = tmp_path / "Library/Logs/Wizards Of The Coast/MTGA/Player.log"
        assert tracker._player_log_path() == expected
    finally:
        tracker.store.close()
