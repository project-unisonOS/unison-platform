"""Deterministic, person-aligned maintenance and hardware recommendations."""

from __future__ import annotations

from typing import Iterable

from .contracts import HealthObservation, Recommendation, stable_id
from .intelligence import Exposure


SEVERITY_WEIGHT = {"critical": 100.0, "high": 70.0, "medium": 40.0, "low": 15.0, "none": 0.0}


def evaluate_hardware_candidate(profile: dict, candidate: dict) -> tuple[bool, tuple[str, ...]]:
    """Fail closed unless a hardware candidate matches declared constraints."""
    reasons: list[str] = []
    if candidate.get("kind") not in {"memory", "storage", "accelerator", "cpu"}:
        reasons.append("unknown hardware class")
    architectures = candidate.get("architectures", [])
    if profile.get("architecture") not in architectures:
        reasons.append("architecture is not supported")
    if candidate.get("support_tier") not in {"reference", "compatible"}:
        reasons.append("candidate is not in a supported compatibility tier")
    if candidate.get("kind") == "memory":
        slots_free = profile.get("memory", {}).get("upgrade_slots_free")
        if slots_free is None or slots_free < 1:
            reasons.append("a free compatible memory slot has not been verified")
    if candidate.get("required_power_watts", 0) > candidate.get("available_power_watts", 0):
        reasons.append("power requirement exceeds the verified budget")
    if not candidate.get("firmware_compatible", False):
        reasons.append("firmware compatibility is not verified")
    return not reasons, tuple(reasons)


class RecommendationEngine:
    def recommend(
        self,
        profile: dict,
        observations: Iterable[HealthObservation],
        exposures: Iterable[Exposure],
        *,
        trends: dict[str, float] | None = None,
        hardware_candidates: Iterable[dict] = (),
    ) -> list[Recommendation]:
        trends = trends or {}
        results: list[Recommendation] = []
        for exposure in exposures:
            if not exposure.fix_available:
                continue
            candidate = stable_id("candidate", [exposure.component, exposure.evidence_id])
            results.append(
                Recommendation(
                    candidate_id=candidate,
                    title=f"Patch {exposure.component['name']}",
                    rationale=(exposure.reason, f"Verified advisory severity: {exposure.severity}"),
                    alternatives=("Temporarily isolate the affected component", "Defer and continue monitoring"),
                    expected_effects={"security_risk_reduced": exposure.severity, "downtime_seconds": 60},
                    risk="medium",
                    authority="prepare",
                    requires_confirmation=True,
                    rollback={"available": True, "method": "last-known-good release"},
                    rank=SEVERITY_WEIGHT[exposure.severity] + 20.0,
                    confidence=0.98,
                )
            )

        by_metric = {item.metric: item for item in observations}
        memory = by_metric.get("memory.pressure")
        if memory and memory.severity in {"warning", "critical"}:
            total_gib = profile["memory"]["total_bytes"] / (1024 ** 3)
            results.append(
                Recommendation(
                    candidate_id=stable_id("candidate", ["memory", total_gib, memory.value]),
                    title="Reduce memory pressure",
                    rationale=(
                        f"Sustained memory pressure is {memory.value:.0%}",
                        f"This appliance has {total_gib:.1f} GiB RAM",
                    ),
                    alternatives=(
                        "Use a smaller or more aggressively quantized local model",
                        "Schedule memory-heavy work at different times",
                        "Add compatible RAM after confirming slot and firmware support",
                    ),
                    expected_effects={
                        "responsiveness": "improved",
                        "hardware_purchase_required": False,
                        "ram_upgrade_may_help": memory.value >= 0.88,
                    },
                    risk="low",
                    authority="recommend",
                    requires_confirmation=True,
                    rollback={"available": True, "method": "restore previous model profile"},
                    rank=55.0 + memory.value * 10,
                    confidence=0.88,
                )
            )
            if memory.severity == "critical":
                for candidate in hardware_candidates:
                    compatible, reasons = evaluate_hardware_candidate(profile, candidate)
                    if candidate.get("kind") != "memory" or not compatible:
                        continue
                    results.append(
                        Recommendation(
                            candidate_id=stable_id("candidate", candidate),
                            title=f"Consider {candidate['name']}",
                            rationale=(
                                f"Sustained memory pressure is {memory.value:.0%}",
                                "This exact option matches the declared architecture, slots, firmware, and power budget",
                            ),
                            alternatives=(
                                "Try the recommended smaller model first",
                                "Continue observing before purchasing hardware",
                            ),
                            expected_effects={
                                "memory_added_bytes": candidate["capacity_bytes"],
                                "benefit_basis": "sustained local memory pressure",
                                "hardware_purchase_required": True,
                            },
                            risk="medium",
                            authority="recommend",
                            requires_confirmation=True,
                            rollback={"available": False, "method": "physical change requires owner procedure"},
                            rank=42.0,
                            confidence=0.80,
                        )
                    )

        storage = by_metric.get("storage.used")
        if storage and storage.severity in {"warning", "critical"}:
            results.append(
                Recommendation(
                    candidate_id=stable_id("candidate", ["storage", storage.value]),
                    title="Protect storage headroom",
                    rationale=(f"Root storage is {storage.value:.0%} used",),
                    alternatives=(
                        "Remove verified disposable caches",
                        "Adjust local model inventory",
                        "Add supported storage if growth continues",
                    ),
                    expected_effects={"capacity_failure_risk": "reduced", "hardware_purchase_required": False},
                    risk="low",
                    authority="recommend",
                    requires_confirmation=True,
                    rollback={"available": True, "method": "no destructive cleanup without separate approval"},
                    rank=50.0 + storage.value * 10,
                    confidence=0.95,
                )
            )
        growth = trends.get("storage.growth_bytes_per_day", 0)
        if growth > 0:
            free = profile["storage"][0]["free_bytes"]
            days = free / growth
            if days <= 30:
                results.append(
                    Recommendation(
                        candidate_id=stable_id("candidate", ["storage-forecast", free, growth]),
                        title="Plan for storage capacity",
                        rationale=(f"At the current local growth rate, free space may be exhausted in {days:.0f} days",),
                        alternatives=(
                            "Reduce retained model and cache data",
                            "Review supported storage expansion before capacity becomes critical",
                        ),
                        expected_effects={"forecast_days_remaining": round(days, 1)},
                        risk="low",
                        authority="recommend",
                        requires_confirmation=True,
                        rollback={"available": True, "method": "forecast only; no change executed"},
                        rank=65.0 - days,
                        confidence=0.75,
                    )
                )
        return sorted(results, key=lambda item: (-item.rank, item.recommendation_id))
