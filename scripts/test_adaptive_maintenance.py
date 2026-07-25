#!/usr/bin/env python3
"""AM-0 through AM-3 acceptance and adversarial simulations."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maintenance.collector import collect_device_profile, evaluate_health  # noqa: E402
from maintenance.contracts import HealthObservation  # noqa: E402
from maintenance.intelligence import ExposureGraph, normalize_evidence  # noqa: E402
from maintenance.recommendations import RecommendationEngine, evaluate_hardware_candidate  # noqa: E402
from maintenance.simulator import MaintenanceSimulator  # noqa: E402
from maintenance.wellbeing import wellbeing_projection  # noqa: E402


AT = "2026-07-24T00:00:00Z"
COMPONENTS = [
    {"ecosystem": "deb", "name": "openssl", "version": "3.0.2"},
    {"ecosystem": "container", "name": "unison-core", "version": "0.6.0"},
]
PROFILE = {
    "profile_id": "fixture-device",
    "observed_at": AT,
    "architecture": "x86_64",
    "cpu": {"vendor": "fixture", "model": "fixture", "logical_cores": 4, "features": []},
    "memory": {"total_bytes": 8 * 1024 ** 3},
    "storage": [{
        "device": "root", "kind": "nvme", "capacity_bytes": 100 * 1024 ** 3,
        "free_bytes": 10 * 1024 ** 3, "health": "healthy",
    }],
    "accelerators": [],
    "firmware": {},
    "software": {
        "os": "ubuntu 24.04", "kernel": "6.8.0", "unison_release": "0.6.0",
        "components": COMPONENTS,
    },
    "support_tier": "compatible",
    "compatibility_matrix_version": "fixture-v1",
    "redactions": ["serial_numbers", "mac_addresses", "personal_content"],
}
REGISTRY = {
    "sources": [
        {"source_id": "ubuntu-security", "trust_tier": "authoritative", "enabled": True},
        {"source_id": "community", "trust_tier": "discovery-only", "enabled": True},
    ]
}


def raw_evidence(
    source_id: str,
    trust_tier: str,
    affected: list[dict[str, str]],
    *,
    signed: bool,
    severity: str = "high",
) -> dict:
    return {
        "source_id": source_id,
        "source_class": "security" if trust_tier == "authoritative" else "community",
        "trust_tier": trust_tier,
        "signature_verified": signed,
        "canonical_url": "https://example.test/advisory",
        "payload": {
            "affected_components": affected,
            "claims": ["security update available"],
            "severity": severity,
            "fixed_versions": ["3.0.3"],
            "corroborating_evidence_ids": [],
        },
    }


def test_private_inventory_and_observations() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        meminfo = root / "meminfo"
        os_release = root / "os-release"
        meminfo.write_text("MemTotal: 8388608 kB\nMemAvailable: 4194304 kB\n")
        os_release.write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
        profile = collect_device_profile(
            root=root, meminfo_path=meminfo, os_release_path=os_release,
            components=COMPONENTS, observed_at=AT,
        )
    serialized = json.dumps(profile).lower()
    for canary in ("alice", "message subject", "aa:bb:cc", "serial-123"):
        assert canary not in serialized
    assert profile["memory"]["total_bytes"] == 8 * 1024 ** 3
    observations = evaluate_health(
        profile,
        {"cpu.saturation": 0.95, "memory.pressure": 0.82, "storage.used": 0.93},
        stamp=AT,
    )
    assert [item.severity for item in observations] == ["critical", "warning", "critical"]
    assert all(not item.contains_personal_content for item in observations)
    try:
        HealthObservation(
            metric="bad", component="host", value=1, unit="count", severity="warning",
            window_start=AT, window_end=AT, contains_personal_content=True,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("personal-content observation was accepted")


def test_security_exposure_is_exact_and_community_cannot_authorize() -> None:
    authoritative = normalize_evidence(
        raw_evidence(
            "ubuntu-security", "authoritative",
            [{"ecosystem": "deb", "name": "openssl", "introduced": "3.0.0", "fixed": "3.0.3"}],
            signed=True,
        ),
        REGISTRY,
    )
    community = normalize_evidence(
        raw_evidence(
            "community", "discovery-only",
            [{"ecosystem": "container", "name": "unison-core", "introduced": "0", "fixed": "99"}],
            signed=False,
        ),
        REGISTRY,
    )
    exposures = ExposureGraph(COMPONENTS).evaluate([authoritative, community])
    assert len(exposures) == 1
    assert exposures[0].component["name"] == "openssl"
    unaffected = normalize_evidence(
        raw_evidence(
            "ubuntu-security", "authoritative",
            [{"ecosystem": "deb", "name": "curl", "introduced": "1", "fixed": "99"}],
            signed=True,
        ),
        REGISTRY,
    )
    assert not ExposureGraph(COMPONENTS).evaluate([unaffected])
    for tampered in (
        raw_evidence("ubuntu-security", "authoritative", [], signed=False),
        raw_evidence("community", "authoritative", [], signed=True),
    ):
        try:
            normalize_evidence(tampered, REGISTRY)
        except ValueError:
            pass
        else:
            raise AssertionError("untrusted evidence promoted itself")


def test_hardware_fit_recommends_software_before_purchase() -> None:
    profile = {
        **PROFILE,
        "memory": {
            **PROFILE["memory"],
            "upgrade_slots_total": 2,
            "upgrade_slots_free": 1,
        },
    }
    observations = evaluate_health(
        profile, {"memory.pressure": 0.91, "storage.used": 0.84}, stamp=AT
    )
    compatible_ram = {
        "kind": "memory", "name": "Supported 16 GiB memory kit",
        "architectures": ["x86_64"], "support_tier": "compatible",
        "firmware_compatible": True, "required_power_watts": 5,
        "available_power_watts": 20, "capacity_bytes": 16 * 1024 ** 3,
    }
    incompatible_ram = {
        **compatible_ram, "name": "Unsupported kit", "architectures": ["aarch64"],
    }
    assert evaluate_hardware_candidate(profile, compatible_ram)[0]
    assert not evaluate_hardware_candidate(profile, incompatible_ram)[0]
    recommendations = RecommendationEngine().recommend(
        profile,
        observations,
        [],
        trends={"storage.growth_bytes_per_day": 1024 ** 3},
        hardware_candidates=[incompatible_ram, compatible_ram],
    )
    memory = next(item for item in recommendations if item.title == "Reduce memory pressure")
    assert memory.authority == "recommend"
    assert memory.requires_confirmation
    assert memory.expected_effects["hardware_purchase_required"] is False
    assert memory.alternatives[0].startswith("Use a smaller")
    storage = next(item for item in recommendations if item.title == "Protect storage headroom")
    assert "Add supported storage" in storage.alternatives[-1]
    assert any(item.title == "Consider Supported 16 GiB memory kit" for item in recommendations)
    assert not any(item.title == "Consider Unsupported kit" for item in recommendations)
    forecast = next(item for item in recommendations if item.title == "Plan for storage capacity")
    assert forecast.expected_effects["forecast_days_remaining"] == 10.0


def test_deterministic_simulation_and_no_external_execution_authority() -> None:
    evidence = raw_evidence(
        "ubuntu-security", "authoritative",
        [{"ecosystem": "deb", "name": "openssl", "introduced": "3.0.0", "fixed": "3.0.3"}],
        signed=True,
        severity="critical",
    )
    scenario = {
        "at": AT,
        "device_profile": PROFILE,
        "samples": {"memory.pressure": 0.91},
        "source_registry": REGISTRY,
        "evidence": [evidence],
    }
    first = MaintenanceSimulator().run(scenario)
    second = MaintenanceSimulator().run(scenario)
    assert first == second
    patch = next(item for item in first["recommendations"] if item["title"] == "Patch openssl")
    assert patch["authority"] == "prepare"
    assert patch["requires_confirmation"]
    assert patch["rollback"]["available"]
    assert hashlib.sha256(json.dumps(first, sort_keys=True).encode()).hexdigest()
    projection = wellbeing_projection(first, observed_at=AT)
    assert projection["privacy"]["personal_content_collected"] is False
    assert projection["autonomy"]["execution_available"] is False


def main() -> None:
    test_private_inventory_and_observations()
    test_security_exposure_is_exact_and_community_cannot_authorize()
    test_hardware_fit_recommends_software_before_purchase()
    test_deterministic_simulation_and_no_external_execution_authority()
    print(
        "[PASS] Adaptive maintenance contracts, private health, security exposure, "
        "hardware-fit recommendations, and hostile-source boundaries pass."
    )


if __name__ == "__main__":
    main()
