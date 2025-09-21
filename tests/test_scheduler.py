from typing import List

from src.scheduler import Scheduler


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, value: float) -> None:
        self.now += value

    def __call__(self) -> float:
        return self.now


def test_scheduler_respects_intervals() -> None:
    clock = _Clock()
    executed: List[str] = []

    def task() -> None:
        executed.append("run")

    scheduler = Scheduler(time_fn=clock)
    scheduler.add_task("demo", 5.0, task)
    scheduler.run_pending()
    assert executed == ["run"]
    assert scheduler.time_until_next_task() == 5.0
    clock.advance(2.0)
    assert scheduler.time_until_next_task() == 3.0
    scheduler.run_pending()
    assert executed == ["run"]
    clock.advance(3.1)
    scheduler.run_pending()
    assert executed == ["run", "run"]
