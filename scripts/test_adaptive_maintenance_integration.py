#!/usr/bin/env python3
"""End-to-end integration tests for maintenance, Lifecycle, persistence, and feeds."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maintenance.feeds import ScheduledFeedCollector, verify_signed_registry  # noqa: E402
from maintenance.lifecycle import MaintenanceLifecycle  # noqa: E402
from maintenance.service import MaintenanceService  # noqa: E402
from maintenance.state import MaintenanceState  # noqa: E402


AT = "2026-07-25T10:00:00Z"


class FakeUpdate:
    def __init__(self, *, healthy: bool) -> None:
        self.healthy = healthy
        self.state = {}

    def apply(self, _bundle: Path, _authorization: dict) -> dict:
        if self.healthy:
            self.state = {"status": "promoted"}
            return {"status": "promoted", "version": "v-next", "previous": "v-current"}
        self.state = {"status": "rolled-back", "automatic": True}
        raise RuntimeError("rolled back automatically after bounded health checks")

    def _state(self) -> dict:
        return self.state


class Response:
    def __init__(self, content: bytes, url: str) -> None:
        self.content = content
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int) -> bytes:
        return self.content[:limit]

    def geturl(self) -> str:
        return self.url


def create_signed_registry(root: Path) -> tuple[Path, Path]:
    private_key = root / "registry-private.pem"
    public_key = root / "registry-public.pem"
    payload = root / "registry-payload.json"
    envelope = root / "registry.json"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)],
        check=True, capture_output=True,
    )
    public_key.write_bytes(subprocess.run(
        ["openssl", "pkey", "-in", str(private_key), "-pubout"],
        check=True, capture_output=True,
    ).stdout)
    payload.write_text(json.dumps({
        "registry_version": 1,
        "sources": [{
            "source_id": "fixture-authoritative",
            "trust_tier": "authoritative",
            "url": "https://updates.example/feed.json",
            "allowed_hosts": ["updates.example"],
            "parser": "json",
            "interval_seconds": 3600,
            "enabled": True,
        }],
    }))
    subprocess.run([
        sys.executable, str(ROOT / "scripts/sign-maintenance-source-registry.py"),
        "--payload", str(payload), "--private-key", str(private_key), "--out", str(envelope),
    ], check=True)
    return envelope, public_key


def plan(grant_id: str) -> dict:
    return {
        "grant_id": grant_id,
        "recommendation_id": "recommendation-1",
        "action_class": "signed-patch-stage",
        "expected_downtime_seconds": 60,
        "checkpoint_id": "checkpoint-phase9",
        "artifact_signature_verified": True,
        "evidence_trust_tier": "authoritative",
    }


def test_persistent_owner_grant_lifecycle_and_restart(root: Path) -> None:
    state = MaintenanceState(root / "state.json")
    lifecycle = MaintenanceLifecycle(state, device_id="local-appliance")
    lifecycle.record_decision({
        "decision": "grant",
        "grant_id": "grant-1",
        "device_id": "local-appliance",
        "action_classes": ["signed-patch-stage"],
        "not_before": "2026-07-25T09:00:00Z",
        "expires_at": "2026-07-25T11:00:00Z",
        "max_actions": 2,
        "max_downtime_seconds": 120,
    }, owner_person_id="owner-1")
    promoted = lifecycle.execute_update(
        plan("grant-1"), bundle_path=root / "bundle",
        authorization={"verified": True}, update_transaction=FakeUpdate(healthy=True), at=AT,
    )
    assert promoted["result"] == "promoted"
    restarted = MaintenanceLifecycle(MaintenanceState(root / "state.json"), device_id="local-appliance")
    rolled_back = restarted.execute_update(
        plan("grant-1"), bundle_path=root / "bundle",
        authorization={"verified": True}, update_transaction=FakeUpdate(healthy=False), at=AT,
    )
    assert rolled_back["result"] == "rolled-back"
    persisted = state.read()
    assert persisted["actions_used"]["grant-1"] == 2
    assert len(persisted["receipts"]) == 2
    try:
        restarted.execute_update(
            plan("grant-1"), bundle_path=root / "bundle",
            authorization={}, update_transaction=FakeUpdate(healthy=True), at=AT,
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("action budget did not survive restart")


def test_signed_scheduled_read_only_feed(root: Path) -> None:
    envelope, public_key = create_signed_registry(root)
    registry = verify_signed_registry(json.loads(envelope.read_text()), public_key)
    state = MaintenanceState(root / "feed-state.json")
    collector = ScheduledFeedCollector(
        registry, state,
        opener=lambda request, timeout: Response(b'{"advisories":[]}', request.full_url),
    )
    at = datetime(2026, 7, 25, 10, tzinfo=timezone.utc)
    first = collector.run_due(at=at)
    assert len(first) == 1 and first[0].trust_tier == "authoritative"
    assert collector.run_due(at=at) == []
    tampered = json.loads(envelope.read_text())
    tampered["signed"]["sources"][0]["url"] = "https://evil.example/feed"
    try:
        verify_signed_registry(tampered, public_key)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered registry signature was accepted")


def test_service_processes_owner_queue_and_publishes_status(root: Path) -> None:
    envelope, public_key = create_signed_registry(root)
    commands = root / "commands"
    commands.mkdir()
    command = {
        "command_id": "command-1",
        "owner_person_id": "owner-1",
        "decision": "grant",
        "grant_id": "grant-service",
        "device_id": "local-appliance",
        "action_classes": ["service-restart"],
        "not_before": "2026-07-25T09:00:00Z",
        "expires_at": "2026-07-25T11:00:00Z",
        "max_actions": 1,
        "max_downtime_seconds": 120,
    }
    (commands / "command-1.json").write_text(json.dumps(command))
    service = MaintenanceService(
        state_path=root / "service-state.json",
        command_dir=commands,
        wellbeing_path=root / "wellbeing.json",
        registry_path=envelope,
        registry_public_key=public_key,
        device_id="local-appliance",
    )
    result = service.run_once(collect=False)
    assert result["decisions_processed"] == 1
    assert (commands / "command-1.processed").exists()
    status = json.loads((root / "wellbeing.json").read_text())
    assert status["autonomy"]["grant_id"] == "grant-service"
    assert status["privacy"]["personal_content_collected"] is False


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        test_persistent_owner_grant_lifecycle_and_restart(root / "lifecycle")
        (root / "feeds").mkdir()
        test_signed_scheduled_read_only_feed(root / "feeds")
        (root / "service").mkdir()
        test_service_processes_owner_queue_and_publishes_status(root / "service")
    print("[PASS] Adaptive maintenance integration and restart recovery gates pass.")


if __name__ == "__main__":
    main()
