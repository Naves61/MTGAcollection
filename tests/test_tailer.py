from pathlib import Path

from src.tailer import FileTailer


def test_tailer_handles_rotation(tmp_path: Path) -> None:
    log_path = tmp_path / "Player.log"
    log_path.write_text("")
    tailer = FileTailer(log_path, active_interval=0.01, idle_interval=0.01, sleep=lambda _: None)
    gen = tailer.follow(stop=lambda: False)

    with log_path.open("a") as handle:
        handle.write("first\n")
    assert next(gen) == "first"

    # Simulate rotation by renaming the file and creating a new one.
    rotated = log_path.with_suffix(".1")
    log_path.rename(rotated)
    log_path.write_text("second\n")
    assert next(gen) == "second"

    gen.close()
