"""Privacy-preserving adaptive maintenance for the UnisonOS appliance."""

from .collector import collect_device_profile, evaluate_health
from .intelligence import ExposureGraph, normalize_evidence
from .recommendations import RecommendationEngine
from .simulator import MaintenanceSimulator

__all__ = [
    "ExposureGraph",
    "MaintenanceSimulator",
    "RecommendationEngine",
    "collect_device_profile",
    "evaluate_health",
    "normalize_evidence",
]
