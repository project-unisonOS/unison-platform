"""Persistent bridge from adaptive-maintenance authority to Phase 9 Lifecycle."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .contracts import now, stable_id
from .execution import AutonomyGrant, BoundedExecutor
from .state import MaintenanceState


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class MaintenanceLifecycle:
    def __init__(self, state: MaintenanceState, *, device_id: str) -> None:
        self.state = state
        self.device_id = device_id

    def record_decision(self, decision: dict, *, owner_person_id: str) -> dict:
        if decision.get("decision") not in {"grant", "revoke", "defer", "cancel"}:
            raise ValueError("unsupported owner decision")
        if decision["decision"] == "grant":
            if decision.get("device_id") != self.device_id:
                raise ValueError("grant targets the wrong device")
            grant = AutonomyGrant(
                grant_id=decision["grant_id"],
                device_id=decision["device_id"],
                action_classes=tuple(decision["action_classes"]),
                not_before=decision["not_before"],
                expires_at=decision["expires_at"],
                max_actions=int(decision["max_actions"]),
                max_downtime_seconds=int(decision["max_downtime_seconds"]),
            )
        record = {
            **decision,
            "decision_id": stable_id("decision", [owner_person_id, decision, now()]),
            "owner_person_id": owner_person_id,
            "recorded_at": now(),
        }

        def persist(value: dict) -> None:
            value["decisions"] = [*value.get("decisions", []), record][-500:]
            if decision["decision"] == "grant":
                value["grants"] = [*value.get("grants", []), asdict(grant)][-500:]
            if decision["decision"] == "revoke":
                grant_id = decision["grant_id"]
                value["grants"] = [
                    {**item, "revoked": True} if item["grant_id"] == grant_id else item
                    for item in value.get("grants", [])
                ]
            if decision["decision"] in {"defer", "cancel"}:
                recommendation_id = decision.get("recommendation_id")
                if not recommendation_id:
                    raise ValueError("recommendation decision requires a recommendation")
                statuses = dict(value.get("recommendation_status", {}))
                statuses[recommendation_id] = {
                    "status": decision["decision"],
                    "until": decision.get("defer_until"),
                    "recorded_at": record["recorded_at"],
                }
                value["recommendation_status"] = statuses

        self.state.mutate(persist)
        return record

    def _grant(self, grant_id: str, *, at: str) -> tuple[AutonomyGrant, int]:
        value = self.state.read()
        raw = next((item for item in value["grants"] if item["grant_id"] == grant_id), None)
        if raw is None:
            raise PermissionError("maintenance grant is not present")
        grant = AutonomyGrant(
            **{**raw, "action_classes": tuple(raw["action_classes"])}
        )
        cooldown = value.get("cooldowns", {}).get(grant_id)
        if cooldown and _timestamp(at) < _timestamp(cooldown):
            raise PermissionError("maintenance grant is cooling down")
        if value.get("circuit_breakers", {}).get(grant_id, {}).get("open"):
            raise PermissionError("maintenance circuit breaker is open")
        return grant, int(value.get("actions_used", {}).get(grant_id, 0))

    def execute_update(
        self,
        plan: dict,
        *,
        bundle_path: Path,
        authorization: dict,
        update_transaction,
        at: str,
    ) -> dict:
        """Authorize once, then delegate update, checkpoint, health, and rollback to Phase 9."""
        grant, used = self._grant(plan["grant_id"], at=at)
        executor = BoundedExecutor(grant, at=at, actions_used=used)
        executor.authorize(plan)
        canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
        plan_sha256 = hashlib.sha256(canonical).hexdigest()
        steps = [{"name": "bounded-authority", "result": "passed"}]
        result = "failed"
        lifecycle_result: dict = {}
        try:
            lifecycle_result = update_transaction.apply(bundle_path, authorization)
            result = lifecycle_result["status"]
            steps.extend([
                {"name": "phase9-checkpoint-stage-activate", "result": "passed"},
                {"name": "phase9-health-gate", "result": "passed"},
            ])
        except Exception as error:
            phase9 = update_transaction._state()
            rolled_back = phase9.get("status") == "rolled-back"
            result = "rolled-back" if rolled_back else "failed"
            steps.extend([
                {"name": "phase9-transaction", "result": "failed", "detail": str(error)},
                {"name": "phase9-rollback", "result": "completed" if rolled_back else "not-available"},
            ])
        receipt = {
            "receipt_id": stable_id("receipt", [grant.grant_id, plan_sha256, at]),
            "recommendation_id": plan["recommendation_id"],
            "plan_sha256": plan_sha256,
            "started_at": at,
            "completed_at": now(),
            "result": result,
            "steps": steps,
            "checkpoint_id": plan["checkpoint_id"],
            "health_decision": {
                "healthy": result == "promoted",
                "phase9_state": update_transaction._state().get("status"),
            },
            "before_observation_ids": plan.get("before_observation_ids", []),
            "after_observation_ids": plan.get("after_observation_ids", []),
            "lifecycle_result": lifecycle_result,
        }

        def persist(value: dict) -> None:
            value["receipts"] = [*value.get("receipts", []), receipt][-500:]
            counts = dict(value.get("actions_used", {}))
            counts[grant.grant_id] = counts.get(grant.grant_id, 0) + 1
            value["actions_used"] = counts
            if result != "promoted":
                breakers = dict(value.get("circuit_breakers", {}))
                previous = breakers.get(grant.grant_id, {"failures": 0})
                failures = int(previous.get("failures", 0)) + 1
                breakers[grant.grant_id] = {"failures": failures, "open": failures >= 2}
                value["circuit_breakers"] = breakers

        self.state.mutate(persist)
        return receipt
