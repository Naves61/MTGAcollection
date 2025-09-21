"""Very small periodic scheduler used by the tracker."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class _Task:
    name: str
    interval: float
    callback: Callable[[], None]
    last_run: float


class Scheduler:
    def __init__(self, *, time_fn: Callable[[], float] = time.monotonic) -> None:
        self._time_fn = time_fn
        self._tasks: Dict[str, _Task] = {}

    def add_task(self, name: str, interval: float, callback: Callable[[], None]) -> None:
        now = self._time_fn()
        self._tasks[name] = _Task(name=name, interval=interval, callback=callback, last_run=now - interval)

    def run_pending(self) -> List[str]:
        now = self._time_fn()
        executed: List[str] = []
        for task in self._tasks.values():
            if now - task.last_run >= task.interval:
                task.callback()
                task.last_run = now
                executed.append(task.name)
        return executed

    def time_until_next_task(self) -> Optional[float]:
        if not self._tasks:
            return None
        now = self._time_fn()
        remaining = [max(task.interval - (now - task.last_run), 0.0) for task in self._tasks.values()]
        return min(remaining)


__all__ = ["Scheduler"]
