"""Append-only JSON-lines cache. A re-run costs nothing and gives the same answers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def cache_key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


class JsonlCache:
    def __init__(self, path: Path | None) -> None:
        """A None path keeps everything in memory, for runs that must not reuse earlier answers."""
        self._path = path
        self._items: dict[str, dict[str, Any]] = {}
        if path is not None and path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._items[row["key"]] = row["value"]

    def get(self, key: str) -> dict[str, Any] | None:
        return self._items.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self._items[key] = value
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as out:
            out.write(json.dumps({"key": key, "value": value}) + "\n")

    def __len__(self) -> int:
        return len(self._items)
