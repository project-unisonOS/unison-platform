#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=_REPO_ROOT, text=True).strip()


def _infer_channel(version: str) -> str:
    v = version.lower()
    if "-alpha." in v or v.endswith("-alpha") or "-alpha" in v:
        return "alpha"
    if "-beta." in v or v.endswith("-beta") or "-beta" in v:
        return "beta"
    return "stable"


def _parse_artifacts_lock(lock_path: Path) -> dict[str, str]:
    """
    Parse artifacts.lock format produced by scripts/pin-images.sh:
      service = "ghcr.io/project-unisonos/<service>@sha256:..."
    """
    images: dict[str, str] = {}
    if not lock_path.exists():
        return images
    for raw in lock_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        service = name.strip()
        image = value.strip().strip('"')
        if service and image:
            images[service] = image
    return images


def _parse_compose_images(compose_path: Path) -> dict[str, str]:
    """
    Best-effort parse `image:` lines (service -> image ref).
    This avoids adding a YAML dependency in the release pipeline.
    """
    images: dict[str, str] = {}
    current_service: str | None = None
    for raw in compose_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            # "  service:"
            current_service = line.strip().rstrip(":")
            continue
        if current_service and "image:" in line:
            stripped = line.strip()
            if stripped.startswith("image:"):
                img = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                images[current_service] = img
                continue
    return images


_ENV_EXPR = re.compile(r"\$\{([^}:]+)(?:(:?[-])([^}]*))?\}")


def _expand_env_ref(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        operator = match.group(2) or ""
        default = match.group(3) or ""
        current = os.getenv(name)
        if operator in {":-", "-"}:
            return current if current not in {None, ""} else default
        return current or ""

    return _ENV_EXPR.sub(repl, value)


def _resolve_local_images(images: dict[str, str]) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for service, requested_ref in images.items():
        expanded_ref = _expand_env_ref(requested_ref)
        try:
            raw = subprocess.check_output(
                ["docker", "image", "inspect", expanded_ref],
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list) or not payload:
            continue
        image = payload[0] if isinstance(payload[0], dict) else {}
        image_id = str(image.get("Id") or "")
        repo_digests = [str(v) for v in (image.get("RepoDigests") or []) if str(v).strip()]
        repo_tags = [str(v) for v in (image.get("RepoTags") or []) if str(v).strip()]
        pinned_ref = repo_digests[0] if repo_digests else ""
        if not pinned_ref and image_id.startswith("sha256:"):
            pinned_ref = f"{expanded_ref}@{image_id}"
        resolved[service] = {
            "requested_ref": requested_ref,
            "resolved_ref": expanded_ref,
            "pinned_ref": pinned_ref,
            "image_id": image_id,
            "repo_digests": repo_digests,
            "repo_tags": repo_tags,
            "source": "local-docker",
        }
    return resolved


@dataclass(frozen=True)
class Args:
    version: str
    out: Path
    compose_file: Path
    artifacts_lock: Path | None
    resolve_local_images: bool
    model_pack_profile: str
    model_pack_manifest: Path
    assets_dir: Path | None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="Release version tag (e.g. v0.5.0-alpha.1)")
    parser.add_argument("--out", required=True, help="Output manifest path (json)")
    parser.add_argument("--compose-file", default="compose/compose.yaml", help="Compose file to hash and parse for image refs")
    parser.add_argument("--artifacts-lock", default="artifacts.lock", help="Optional artifacts.lock with pinned digests")
    parser.add_argument(
        "--resolve-local-images",
        action="store_true",
        help="Resolve compose image refs against the local Docker daemon and record image IDs/digests",
    )
    parser.add_argument("--model-pack-profile", default="alpha/default", help="Default model pack profile name")
    parser.add_argument(
        "--model-pack-manifest",
        default="model-packs/alpha/default.json",
        help="Model pack profile manifest path to hash (in this repo)",
    )
    parser.add_argument("--assets-dir", default="", help="Optional directory of staged release assets to summarize")
    ns = parser.parse_args()

    args = Args(
        version=str(ns.version),
        out=Path(ns.out),
        compose_file=(Path(ns.compose_file) if str(ns.compose_file).strip() else Path("compose/compose.yaml")),
        artifacts_lock=(Path(ns.artifacts_lock) if str(ns.artifacts_lock).strip() else None),
        resolve_local_images=bool(ns.resolve_local_images),
        model_pack_profile=str(ns.model_pack_profile),
        model_pack_manifest=Path(ns.model_pack_manifest),
        assets_dir=Path(ns.assets_dir).resolve() if str(ns.assets_dir).strip() else None,
    )
    # Resolve relative paths against the unison-platform repo root so the script
    # works when invoked from other working directories (CI, monorepo, etc).
    if not args.out.is_absolute():
        args = Args(**{**args.__dict__, "out": (_REPO_ROOT / args.out).resolve()})
    if not args.compose_file.is_absolute():
        args = Args(**{**args.__dict__, "compose_file": (_REPO_ROOT / args.compose_file).resolve()})
    if args.artifacts_lock and not args.artifacts_lock.is_absolute():
        args = Args(**{**args.__dict__, "artifacts_lock": (_REPO_ROOT / args.artifacts_lock).resolve()})
    if not args.model_pack_manifest.is_absolute():
        args = Args(**{**args.__dict__, "model_pack_manifest": (_REPO_ROOT / args.model_pack_manifest).resolve()})

    build_ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    channel = _infer_channel(args.version)
    commit = _git("rev-parse", "HEAD")

    compose_hashes = {}
    if args.compose_file.exists():
        compose_hashes[str(args.compose_file)] = _sha256_file(args.compose_file)
    docker_compose_prod = _REPO_ROOT / "docker-compose.prod.yml"
    if docker_compose_prod.exists():
        compose_hashes[str(docker_compose_prod)] = _sha256_file(docker_compose_prod)

    pinned_images = _parse_artifacts_lock(args.artifacts_lock) if args.artifacts_lock else {}
    compose_images = _parse_compose_images(args.compose_file) if args.compose_file.exists() else {}
    resolved_images = _resolve_local_images(compose_images) if args.resolve_local_images else {}
    if not pinned_images and resolved_images:
        pinned_images = {
            service: meta["pinned_ref"]
            for service, meta in resolved_images.items()
            if isinstance(meta, dict) and str(meta.get("pinned_ref") or "").strip()
        }

    model_pack_hash = _sha256_file(args.model_pack_manifest) if args.model_pack_manifest.exists() else ""

    assets_summary: dict[str, Any] = {}
    if args.assets_dir and args.assets_dir.exists():
        for p in sorted(args.assets_dir.iterdir()):
            if not p.is_file():
                continue
            assets_summary[p.name] = {"size_bytes": p.stat().st_size, "sha256": _sha256_file(p)}

    manifest: dict[str, Any] = {
        "schema_version": "unison.platform.release.manifest.v1",
        "release": {
            "version": args.version,
            "channel": channel,
            "built_at": build_ts,
            "git": {"repo": "unison-platform", "commit": commit},
        },
        "assets": assets_summary,
        "compose": {
            "files": compose_hashes,
            "images_from_compose": compose_images,
            "images_pinned": pinned_images,
            "images_resolved": resolved_images,
        },
        "model_packs": {
            "default_profile": args.model_pack_profile,
            "profile_manifest_sha256": model_pack_hash,
        },
        "requirements": {
            "cpu_cores_min": 4,
            "ram_gb_min": 8,
            "disk_gb_min": 20,
            "notes": "Alpha sizing; increase RAM/disk for larger Qwen variants and additional packs.",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
