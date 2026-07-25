"""Full-stack eligibility, feedback calibration, and pilot readiness."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_LAYERS = {
    "os-package": True,
    "container-runtime": True,
    "driver": True,
    "model-runtime": True,
    "model": True,
    "capability": True,
    "database-configuration": True,
    "firmware": False,
}


def full_stack_eligibility(candidate: dict, compatibility: dict) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    layer = candidate.get("layer")
    if layer not in SUPPORTED_LAYERS:
        reasons.append("unknown maintenance layer")
    if layer == "firmware" and not compatibility.get("vendor_recovery_verified", False):
        reasons.append("firmware requires verified vendor recovery")
    if not candidate.get("signed", False):
        reasons.append("artifact signature is not verified")
    if not candidate.get("rollback_available", False):
        reasons.append("rollback is unavailable")
    if candidate.get("hardware_id") not in compatibility.get("hardware_ids", []):
        reasons.append("candidate is not approved for this hardware")
    return not reasons, tuple(reasons)


@dataclass
class Calibration:
    accepted: int = 0
    rejected: int = 0
    realized: int = 0
    rolled_back: int = 0
    alerts: int = 0

    def record(self, *, accepted: bool, realized: bool = False, rolled_back: bool = False) -> None:
        self.accepted += int(accepted)
        self.rejected += int(not accepted)
        self.realized += int(realized)
        self.rolled_back += int(rolled_back)

    def report(self) -> dict:
        decisions = self.accepted + self.rejected
        return {
            "decisions": decisions,
            "acceptance_rate": self.accepted / decisions if decisions else 0.0,
            "realized_benefit_rate": self.realized / self.accepted if self.accepted else 0.0,
            "rollback_rate": self.rolled_back / self.accepted if self.accepted else 0.0,
            "alert_burden": self.alerts,
        }


def pilot_readiness(evidence: dict) -> dict:
    required = (
        "privacy_review",
        "security_review",
        "accessibility_review",
        "incident_runbook",
        "source_governance_review",
        "support_boundaries",
    )
    missing = [item for item in required if evidence.get(item) != "passed"]
    physical = evidence.get("physical_matrix") == "passed"
    return {
        "ci_verifiable_ready": not missing,
        "pilot_promotion_ready": not missing and physical and evidence.get("human_promotion") == "approved",
        "missing": missing,
        "physical_matrix": evidence.get("physical_matrix", "pending"),
        "human_promotion": evidence.get("human_promotion", "pending"),
    }
