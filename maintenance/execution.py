"""Bounded, reversible adaptive-maintenance execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

from .contracts import now, stable_id


REVERSIBLE_ACTIONS = {
    "service-restart",
    "service-failover",
    "cache-housekeeping",
    "signed-patch-stage",
    "model-rollback",
    "configuration-rollback",
}


@dataclass(frozen=True)
class AutonomyGrant:
    grant_id: str
    device_id: str
    action_classes: tuple[str, ...]
    not_before: str
    expires_at: str
    max_actions: int
    max_downtime_seconds: int
    checkpoint_required: bool = True
    revoked: bool = False


class CircuitBreaker:
    def __init__(self, *, failure_limit: int = 2) -> None:
        self.failure_limit = failure_limit
        self.failures = 0
        self.open = False

    def record(self, healthy: bool) -> None:
        self.failures = 0 if healthy else self.failures + 1
        self.open = self.failures >= self.failure_limit


class BoundedExecutor:
    """Execute only exact, reversible plans covered by a live local grant."""

    def __init__(self, grant: AutonomyGrant, *, at: str, actions_used: int = 0) -> None:
        self.grant = grant
        self.at = at
        self.actions_used = actions_used
        self.breaker = CircuitBreaker()

    def authorize(self, plan: dict) -> None:
        action = plan.get("action_class")
        if self.grant.revoked:
            raise PermissionError("autonomy grant is revoked")
        if not (self.grant.not_before <= self.at <= self.grant.expires_at):
            raise PermissionError("outside the autonomy grant window")
        if action not in REVERSIBLE_ACTIONS or action not in self.grant.action_classes:
            raise PermissionError("action class is not covered by the grant")
        if self.actions_used >= self.grant.max_actions:
            raise PermissionError("action budget is exhausted")
        if plan.get("expected_downtime_seconds", 0) > self.grant.max_downtime_seconds:
            raise PermissionError("downtime budget would be exceeded")
        if self.grant.checkpoint_required and not plan.get("checkpoint_id"):
            raise PermissionError("a verified checkpoint is required")
        if not plan.get("artifact_signature_verified", False):
            raise PermissionError("the staged artifact is not verified")
        if plan.get("evidence_trust_tier") == "discovery-only":
            raise PermissionError("community evidence cannot authorize execution")
        if self.breaker.open:
            raise PermissionError("the maintenance circuit breaker is open")

    def execute(
        self,
        plan: dict,
        *,
        apply: Callable[[], None],
        health_gate: Callable[[], bool],
        rollback: Callable[[], None],
    ) -> dict:
        self.authorize(plan)
        canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
        plan_sha256 = hashlib.sha256(canonical).hexdigest()
        steps: list[dict] = [{"name": "authorize", "result": "passed"}]
        result = "promoted"
        apply()
        steps.append({"name": "canary", "result": "applied"})
        healthy = bool(health_gate())
        self.breaker.record(healthy)
        if not healthy:
            rollback()
            result = "rolled-back"
            steps.extend(
                [
                    {"name": "health-gate", "result": "failed"},
                    {"name": "rollback", "result": "completed"},
                ]
            )
        else:
            steps.append({"name": "health-gate", "result": "passed"})
        self.actions_used += 1
        return {
            "receipt_id": stable_id("receipt", [self.grant.grant_id, plan_sha256, self.at]),
            "recommendation_id": plan["recommendation_id"],
            "plan_sha256": plan_sha256,
            "started_at": self.at,
            "completed_at": now(),
            "result": result,
            "steps": steps,
            "checkpoint_id": plan["checkpoint_id"],
            "health_decision": {"healthy": healthy, "circuit_breaker_open": self.breaker.open},
            "before_observation_ids": plan.get("before_observation_ids", []),
            "after_observation_ids": plan.get("after_observation_ids", []),
        }
