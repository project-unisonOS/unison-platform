"""Content-free host inventory and health evaluation."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Iterable

from .contracts import HealthObservation, now, stable_id


def _meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    values: dict[str, int] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        name, raw = line.split(":", 1)
        token = raw.strip().split()[0]
        values[name] = int(token) * 1024
    return values


def _os_release(path: Path = Path("/etc/os-release")) -> str:
    if not path.exists():
        return platform.system()
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip('"')
    return f"{values.get('ID', 'unknown')} {values.get('VERSION_ID', '')}".strip()


def collect_device_profile(
    *,
    root: Path = Path("/"),
    meminfo_path: Path = Path("/proc/meminfo"),
    os_release_path: Path = Path("/etc/os-release"),
    components: Iterable[dict[str, str]] = (),
    observed_at: str | None = None,
) -> dict:
    """Collect only facts needed for compatibility and capacity decisions."""
    stamp = observed_at or now()
    memory = _meminfo(meminfo_path)
    usage = shutil.disk_usage(root)
    architecture = platform.machine().lower()
    architecture = {"amd64": "x86_64", "arm64": "aarch64"}.get(architecture, architecture)
    if architecture not in {"x86_64", "aarch64"}:
        architecture = "unknown"
    facts = {
        "observed_at": stamp,
        "architecture": architecture,
        "cpu": {
            "vendor": platform.processor() or "unknown",
            "model": platform.machine() or "unknown",
            "logical_cores": os.cpu_count() or 1,
            "features": [],
        },
        "memory": {"total_bytes": memory.get("MemTotal", 1)},
        "storage": [{
            "device": "root",
            "kind": "unknown",
            "capacity_bytes": usage.total,
            "free_bytes": usage.free,
            "health": "unknown",
        }],
        "accelerators": [],
        "firmware": {},
        "software": {
            "os": _os_release(os_release_path),
            "kernel": platform.release(),
            "unison_release": os.environ.get("UNISON_RELEASE"),
            "components": sorted(components, key=lambda item: (item["ecosystem"], item["name"])),
        },
        "support_tier": "unknown",
        "compatibility_matrix_version": None,
        "redactions": ["serial_numbers", "mac_addresses", "personal_content"],
    }
    facts["profile_id"] = stable_id("device", facts)
    return facts


def evaluate_health(profile: dict, samples: dict[str, float], *, stamp: str | None = None) -> list[HealthObservation]:
    """Turn normalized samples into deterministic, explainable observations."""
    at = stamp or now()
    thresholds = {
        "cpu.saturation": (0.75, 0.90, "ratio"),
        "memory.pressure": (0.70, 0.88, "ratio"),
        "storage.used": (0.80, 0.92, "ratio"),
        "service.error_rate": (0.02, 0.10, "ratio"),
        "backup.age_hours": (24.0, 72.0, "hours"),
        "model.first_token_ms": (2000.0, 5000.0, "milliseconds"),
    }
    observations: list[HealthObservation] = []
    for metric, value in sorted(samples.items()):
        if metric not in thresholds:
            continue
        warning, critical, unit = thresholds[metric]
        severity = "critical" if value >= critical else "warning" if value >= warning else "healthy"
        observations.append(
            HealthObservation(
                metric=metric,
                component="host" if not metric.startswith(("service.", "model.")) else metric.split(".", 1)[0],
                value=float(value),
                unit=unit,
                severity=severity,
                window_start=at,
                window_end=at,
                collection_method="privacy-minimized-local-aggregate",
            )
        )
    return observations
