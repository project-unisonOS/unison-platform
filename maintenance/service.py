"""Recommend-first maintenance service orchestration."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .feeds import ScheduledFeedCollector, verify_signed_registry
from .lifecycle import MaintenanceLifecycle
from .state import MaintenanceState


class MaintenanceService:
    def __init__(
        self,
        *,
        state_path: Path,
        command_dir: Path,
        wellbeing_path: Path,
        registry_path: Path,
        registry_public_key: Path,
        device_id: str,
        collector_factory=ScheduledFeedCollector,
    ) -> None:
        self.state = MaintenanceState(state_path)
        self.command_dir = command_dir
        self.wellbeing_path = wellbeing_path
        self.registry_path = registry_path
        self.registry_public_key = registry_public_key
        self.lifecycle = MaintenanceLifecycle(self.state, device_id=device_id)
        self.collector_factory = collector_factory

    def process_commands(self) -> list[dict]:
        processed: list[dict] = []
        self.command_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.command_dir.glob("*.json")):
            try:
                command = json.loads(path.read_text(encoding="utf-8"))
                owner = command.pop("owner_person_id")
                command.pop("command_id", None)
                processed.append(self.lifecycle.record_decision(command, owner_person_id=owner))
                destination = path.with_suffix(".processed")
                path.replace(destination)
            except Exception as error:
                destination = path.with_suffix(".rejected")
                destination.write_text(
                    json.dumps(
                        {"error": str(error), "command_sha256": hashlib.sha256(
                            path.read_bytes()
                        ).hexdigest()},
                        sort_keys=True,
                    ) + "\n",
                    encoding="utf-8",
                )
                os.chmod(destination, 0o600)
                path.unlink(missing_ok=True)
        return processed

    def collect_due_sources(self) -> list:
        envelope = json.loads(self.registry_path.read_text(encoding="utf-8"))
        registry = verify_signed_registry(envelope, self.registry_public_key)
        return self.collector_factory(registry, self.state).run_due()

    def publish_status(self) -> dict:
        state = self.state.read()
        active = next(
            (
                grant for grant in reversed(state["grants"])
                if not grant.get("revoked", False)
            ),
            None,
        )
        status = {
            "status": "healthy",
            "summary": "Adaptive maintenance is monitoring this device.",
            "dimensions": [],
            "recommendations": [],
            "maintenance_history": state["receipts"][-20:],
            "community_proposals": [],
            "privacy": {"personal_content_collected": False},
            "autonomy": {
                "default": "recommend",
                "execution_available": active is not None,
                "grant_id": active.get("grant_id") if active else None,
                "revocable": True,
            },
        }
        self.wellbeing_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.wellbeing_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o640)
        os.replace(temporary, self.wellbeing_path)
        return status

    def run_once(self, *, collect: bool = True) -> dict:
        decisions = self.process_commands()
        sources = self.collect_due_sources() if collect else []
        status = self.publish_status()
        return {
            "decisions_processed": len(decisions),
            "sources_collected": len(sources),
            "status": status["status"],
        }
