#!/usr/bin/env python3
"""Verify the complete public unsupported-preview asset set."""

import argparse
import hashlib
import json
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.release_bundle import verify_bundle


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--assets-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.assets_dir
    required = {
        "SHA256SUMS", "SHA256SUMS.ed25519", "RELEASE_NOTES.md",
        "unisonos-preview-bundle-ed25519.pem",
        f"unisonos-{args.version}-images.env",
        f"unisonos-{args.version}-manifest.json",
        f"unisonos-{args.version}-provenance.json",
        f"unisonos-{args.version}-sources.json",
        f"unisonos-{args.version}-support.json",
        f"unisonos-{args.version}.spdx.json",
        f"unisonos-{args.version}-x86_64.tar",
    }
    missing = required - {p.name for p in root.iterdir()}
    if missing:
        raise SystemExit(f"missing release assets: {sorted(missing)}")
    for line in (root / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if digest(root / name) != expected:
            raise SystemExit(f"checksum mismatch: {name}")
    subprocess.run([  # nosec B603
        "openssl", "pkeyutl", "-verify", "-rawin", "-pubin",
        "-inkey", str(root / "unisonos-preview-bundle-ed25519.pem"),
        "-in", str(root / "SHA256SUMS"),
        "-sigfile", str(root / "SHA256SUMS.ed25519"),
    ], check=True)
    manifest = json.loads((root / f"unisonos-{args.version}-manifest.json").read_text())
    sources = json.loads((root / f"unisonos-{args.version}-sources.json").read_text())
    if manifest["runtime"]["images"] != sources["resolved_images"]:
        raise SystemExit("manifest and source correspondence image sets differ")
    provenance = json.loads((root / f"unisonos-{args.version}-provenance.json").read_text())
    bundle = root / f"unisonos-{args.version}-x86_64.tar"
    if provenance["subject"][0]["digest"]["sha256"] != digest(bundle):
        raise SystemExit("bundle provenance digest mismatch")
    policy = json.loads((root / f"unisonos-{args.version}-support.json").read_text())
    if policy["status"] != "unsupported-preview" or policy["production_use"]:
        raise SystemExit("preview support policy is unsafe")
    verify_bundle(bundle, root / "unisonos-preview-bundle-ed25519.pem")
    print(f"verified complete public asset set for {args.version}")


if __name__ == "__main__":
    main()
