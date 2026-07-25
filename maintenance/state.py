"""Crash-safe persistent state for adaptive maintenance."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


STATE_VERSION = "unison.maintenance-state.v1"


class MaintenanceState:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty()
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != STATE_VERSION:
            raise ValueError("unsupported maintenance state")
        return value

    @staticmethod
    def empty() -> dict[str, Any]:
        return {
            "schema_version": STATE_VERSION,
            "grants": [],
            "decisions": [],
            "receipts": [],
            "source_runs": [],
            "actions_used": {},
            "cooldowns": {},
            "circuit_breakers": {},
            "recommendation_status": {},
        }

    def write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        value = {"schema_version": STATE_VERSION, **value}
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def mutate(self, update) -> dict[str, Any]:
        value = self.read()
        update(value)
        self.write(value)
        return value

    def append(self, collection: str, record: dict[str, Any], *, maximum: int = 500) -> dict:
        def update(value: dict) -> None:
            records = list(value.get(collection, []))
            records.append(record)
            value[collection] = records[-maximum:]

        return self.mutate(update)
