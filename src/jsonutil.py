"""Lightweight JSON helpers with optional orjson acceleration."""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - optional dependency
    import orjson  # type: ignore
except ImportError:  # pragma: no cover - fallback path
    import json

    def loads(data: str) -> Any:
        return json.loads(data)

    def dumps(data: Any) -> str:
        return json.dumps(data)
else:  # pragma: no cover - executed when orjson is available
    def loads(data: str) -> Any:
        return orjson.loads(data)

    def dumps(data: Any) -> str:
        return orjson.dumps(data).decode("utf-8")


__all__ = ["loads", "dumps"]
