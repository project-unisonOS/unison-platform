#!/usr/bin/env python3
"""Generate the deterministic Phase 9 supported-appliance manifest."""

import argparse
import hashlib
import json
import os
import re
import subprocess  # nosec B404
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGEST = re.compile(r"^[^\s:@]+(?::[^\s@]+)?@sha256:([0-9a-f]{64})$")
ZERO = "0" * 64
SERVICE_ALIASES = {
    "UNISON_RENDERER_IMAGE": "experience-renderer",
    "UNISON_SPEECH_IMAGE": "io-speech",
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_images(path: Path, allow_placeholder: bool) -> dict[str, str]:
    images = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        match = DIGEST.fullmatch(value)
        if not match:
            fail(f"{key} is not an immutable digest reference")
        if match.group(1) == ZERO and not allow_placeholder:
            fail(f"{key} still uses the example zero digest")
        service = SERVICE_ALIASES.get(
            key,
            key.removeprefix("UNISON_").removesuffix("_IMAGE").lower().replace("_", "-"),
        )
        images[service] = value
    return dict(sorted(images.items()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--images-env", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source-date-epoch", type=int, default=None)
    parser.add_argument("--allow-placeholder", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    epoch = args.source_date_epoch
    if epoch is None:
        raw = os.environ.get("SOURCE_DATE_EPOCH")
        if not raw:
            fail("SOURCE_DATE_EPOCH or --source-date-epoch is required")
        epoch = int(raw)
    created = datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")
    compose = ROOT / "compose/compose.supported.yaml"
    models = ROOT / "model-packs/alpha/default.json"
    requirements = ROOT / "releases/supported-host-requirements.json"
    licenses = ROOT / "releases/supported-licenses.json"
    commit = subprocess.check_output(  # nosec B603
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    images = load_images(args.images_env, args.allow_placeholder)
    expected = load_json(licenses)["images"]
    if set(images) != set(expected):
        fail(f"image/license inventory drift: {sorted(set(images) ^ set(expected))}")

    manifest = {
        "schema_version": "unison.platform.supported-release.v1",
        "release": {
            "version": args.version,
            "channel": "stable" if "-" not in args.version else "preview",
            "source_date_epoch": epoch,
            "created_at": created,
            "source": {"repository": "unison-platform", "commit": commit},
        },
        "runtime": {
            "compose": {"path": "compose/compose.supported.yaml", "sha256": sha256(compose)},
            "images": images,
            "service_count": len(images),
        },
        "compatibility": load_json(requirements),
        "versions": {
            "database_schema": 1,
            "configuration": 1,
            "capability_package": 1,
            "backup": 1,
            "model_profile": load_json(models)["profile"],
            "model_profile_sha256": sha256(models),
        },
        "licenses": load_json(licenses),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
