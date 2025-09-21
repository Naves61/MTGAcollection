"""Efficient polling based file tailer."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, Generator, Optional


class FileTailer:
    """Minimal polling tailer resilient to log rotation."""

    def __init__(
        self,
        path: Path,
        *,
        active_interval: float = 0.5,
        idle_interval: float = 5.0,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.path = Path(path)
        self.active_interval = active_interval
        self.idle_interval = idle_interval
        self._sleep = sleep or time.sleep
        self._offset = 0
        self._inode: Optional[int] = None
        self._last_size = 0

    def follow(self, stop: Optional[Callable[[], bool]] = None) -> Generator[str, None, None]:
        """Yield appended lines until ``stop`` returns True."""

        while True:
            if stop and stop():
                return
            try:
                stat = self.path.stat()
            except FileNotFoundError:
                self._inode = None
                self._offset = 0
                self._sleep(self.idle_interval)
                continue
            inode = getattr(stat, "st_ino", None)
            file_was_rotated = self._inode is not None and inode != self._inode
            size_shrunk = stat.st_size < self._last_size
            if file_was_rotated or size_shrunk:
                self._offset = 0
            self._inode = inode
            self._last_size = stat.st_size
            with self.path.open("r", encoding="utf-8", errors="ignore") as handle:
                handle.seek(self._offset, os.SEEK_SET)
                while True:
                    line = handle.readline()
                    if not line:
                        self._offset = handle.tell()
                        break
                    yield line.rstrip("\n")
            self._sleep(self.active_interval if stat.st_size > 0 else self.idle_interval)


__all__ = ["FileTailer"]
