"""Deterministic AM-0 through AM-3 simulation harness."""

from __future__ import annotations

from .collector import evaluate_health
from .intelligence import ExposureGraph, normalize_evidence
from .recommendations import RecommendationEngine


class MaintenanceSimulator:
    def run(self, scenario: dict) -> dict:
        profile = scenario["device_profile"]
        observations = evaluate_health(profile, scenario.get("samples", {}), stamp=scenario["at"])
        evidence = [
            normalize_evidence(item, scenario["source_registry"])
            for item in scenario.get("evidence", [])
        ]
        exposures = ExposureGraph(profile["software"]["components"]).evaluate(evidence)
        recommendations = RecommendationEngine().recommend(
            profile,
            observations,
            exposures,
            trends=scenario.get("trends", {}),
            hardware_candidates=scenario.get("hardware_candidates", []),
        )
        return {
            "observations": [item.__dict__ for item in observations],
            "exposures": [
                {
                    "component": item.component,
                    "evidence_id": item.evidence_id,
                    "severity": item.severity,
                    "fixed_versions": list(item.fixed_versions),
                    "fix_available": item.fix_available,
                    "reason": item.reason,
                }
                for item in exposures
            ],
            "recommendations": [item.__dict__ for item in recommendations],
        }
