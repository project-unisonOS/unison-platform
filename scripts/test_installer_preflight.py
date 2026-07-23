#!/usr/bin/env python3
"""Dependency-free Phase 9 installer preflight simulations."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "installer"))
from appliance_preflight import evaluate  # noqa: E402

SUPPORTED = {
    "os_id": "ubuntu", "os_version": "24.04", "architecture": "x86_64",
    "cpu_cores": 4, "ram_gb": 8, "disk_free_gb": 20,
    "virtualization": True, "uefi": True, "docker": True, "compose": True,
    "clock_synchronized": True, "microphone_detected": True,
    "speaker_detected": True,
}


def main() -> None:
    assert evaluate(SUPPORTED)["eligible"]
    for field, bad in (
        ("os_version", "22.04"), ("architecture", "aarch64"),
        ("cpu_cores", 2), ("ram_gb", 4), ("disk_free_gb", 19),
        ("virtualization", False), ("uefi", False),
        ("docker", False), ("compose", False),
    ):
        facts = {**SUPPORTED, field: bad}
        report = evaluate(facts)
        assert not report["eligible"], field
        expected = {
            "os_version": "os", "architecture": "architecture",
            "cpu_cores": "cpu", "ram_gb": "memory", "disk_free_gb": "storage",
            "virtualization": "virtualization", "uefi": "uefi",
            "docker": "docker", "compose": "docker",
        }[field]
        assert expected in report["blockers"]
    audio = evaluate({**SUPPORTED, "microphone_detected": False, "speaker_detected": False})
    assert audio["eligible"]
    assert audio["warnings"] == ["microphone_detected", "speaker_detected"]
    print("[PASS] Installer preflight accepts the target and blocks nine incompatible cases.")


if __name__ == "__main__":
    main()
