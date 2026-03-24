#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path, *, container_service: str) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raw = subprocess.check_output(
        [
            "docker",
            "compose",
            "--env-file",
            str(_REPO_ROOT / ".env"),
            "-f",
            str(_REPO_ROOT / "compose/compose.yaml"),
            "-f",
            str(_REPO_ROOT / "compose/compose.local-source.yaml"),
            "exec",
            "-T",
            container_service,
            "python3",
            "-c",
            (
                "from pathlib import Path; import json; "
                f"print(Path({str(path)!r}).read_text(encoding='utf-8'))"
            ),
        ],
        text=True,
    )
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, help="Path to emitted updates override artifact JSON")
    parser.add_argument(
        "--manifest",
        default="releases/local-dev-manifest.json",
        help="Path to platform release manifest JSON",
    )
    parser.add_argument(
        "--container-service",
        default="updates",
        help="Compose service name to query when the artifact path is container-local",
    )
    ns = parser.parse_args()

    artifact_path = Path(ns.artifact).resolve()
    manifest_path = Path(ns.manifest).resolve()

    artifact = _load_json(artifact_path, container_service=ns.container_service)
    manifest = _load_json(manifest_path, container_service=ns.container_service)

    if artifact.get("schema_version") != "unison.updates.compose.override.v1":
        raise SystemExit("unexpected artifact schema")

    execution_plan = artifact.get("execution_plan") if isinstance(artifact.get("execution_plan"), dict) else {}
    services = artifact.get("services") if isinstance(artifact.get("services"), dict) else {}
    manifest_images = (
        ((manifest.get("compose") if isinstance(manifest.get("compose"), dict) else {}).get("images_pinned"))
        if isinstance(manifest, dict)
        else {}
    ) or {}

    if not services:
        raise SystemExit("artifact services map is empty")

    target_version = execution_plan.get("target_version")
    manifest_version = ((manifest.get("release") if isinstance(manifest.get("release"), dict) else {}).get("version"))
    if target_version and manifest_version and target_version != manifest_version:
        raise SystemExit(f"target_version mismatch: artifact={target_version} manifest={manifest_version}")

    for service, meta in services.items():
        if not isinstance(meta, dict):
            raise SystemExit(f"invalid service entry for {service}")
        target = str(meta.get("image") or "")
        expected = str(manifest_images.get(service) or "")
        if expected and target != expected:
            raise SystemExit(f"target mismatch for {service}: artifact={target} manifest={expected}")

    print(
        json.dumps(
            {
                "ok": True,
                "artifact": str(artifact_path),
                "manifest": str(manifest_path),
                "service_count": len(services),
                "target_version": target_version,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
