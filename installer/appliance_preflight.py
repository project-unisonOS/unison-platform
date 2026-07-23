#!/usr/bin/env python3
"""Phase 9 native-appliance preflight with a deterministic simulation mode."""

import argparse
import json
import os
import platform
import shutil
import subprocess  # nosec B404
from pathlib import Path

MIN_CPU = 4
MIN_RAM_GB = 8
MIN_DISK_GB = 20


def collect() -> dict:
    os_release = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            os_release[key] = value.strip('"')
    memory_kib = 0
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            memory_kib = int(line.split()[1])
    flags = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    disk = shutil.disk_usage("/")
    return {
        "os_id": os_release.get("ID", ""),
        "os_version": os_release.get("VERSION_ID", ""),
        "architecture": platform.machine(),
        "cpu_cores": os.cpu_count() or 0,
        "ram_gb": memory_kib // (1024 * 1024),
        "disk_free_gb": disk.free // (1024**3),
        "virtualization": " vmx " in f" {flags} " or " svm " in f" {flags} ",
        "uefi": Path("/sys/firmware/efi").is_dir(),
        "docker": shutil.which("docker") is not None,
        "compose": subprocess.run(  # nosec B603
            ["docker", "compose", "version"], capture_output=True
        ).returncode == 0 if shutil.which("docker") else False,
        "clock_synchronized": Path("/run/systemd/timesync/synchronized").exists(),
        "microphone_detected": False,
        "speaker_detected": False,
    }


def evaluate(facts: dict) -> dict:
    blockers = []
    warnings = []
    checks = {
        "os": facts.get("os_id") == "ubuntu" and facts.get("os_version") == "24.04",
        "architecture": facts.get("architecture") in {"x86_64", "amd64"},
        "cpu": int(facts.get("cpu_cores", 0)) >= MIN_CPU,
        "memory": int(facts.get("ram_gb", 0)) >= MIN_RAM_GB,
        "storage": int(facts.get("disk_free_gb", 0)) >= MIN_DISK_GB,
        "virtualization": bool(facts.get("virtualization")),
        "uefi": bool(facts.get("uefi")),
        "docker": bool(facts.get("docker") and facts.get("compose")),
    }
    for name, passed in checks.items():
        if not passed:
            blockers.append(name)
    for name in ("clock_synchronized", "microphone_detected", "speaker_detected"):
        if not facts.get(name):
            warnings.append(name)
    return {
        "schema_version": "unison.platform.preflight.v1",
        "eligible": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
        "facts": facts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", type=Path, help="Use a synthetic facts file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    facts = json.loads(args.facts.read_text()) if args.facts else collect()
    report = evaluate(facts)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["eligible"] else 2)


if __name__ == "__main__":
    main()
