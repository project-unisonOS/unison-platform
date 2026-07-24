#!/usr/bin/env python3
"""Verify, preview, and transactionally install a supported release bundle."""

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.release_bundle import verify_bundle
from installer.transaction import Installer, tree_digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--trusted-public-key", required=True, type=Path)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("verify")
    install = subcommands.add_parser("install")
    install.add_argument("--accept-plan-sha256", required=True)
    args = parser.parse_args()

    verified = verify_bundle(args.bundle, args.trusted_public_key)
    plan = verified.installation_plan(args.prefix, args.data_dir)
    plan_sha256 = verified.plan_sha256(args.prefix, args.data_dir)
    if args.command == "verify":
        print(json.dumps({
            "status": "verified",
            "plan_sha256": plan_sha256,
            "plan": plan,
        }, indent=2, sort_keys=True))
        return
    if args.accept_plan_sha256 != plan_sha256:
        raise SystemExit(
            "refusing installation: verify the bundle and accept the exact system-change plan"
        )
    with tempfile.TemporaryDirectory() as directory:
        materialized = verified.materialize(Path(directory) / "release")
        engine = Installer(args.prefix, args.data_dir)
        result = engine.install(
            materialized,
            verified.manifest["release"]["version"],
            receipt=verified.receipt(tree_digest(materialized)),
        )
    print(json.dumps({
        **result,
        "plan_sha256": plan_sha256,
        "receipt": str(args.prefix / "install-receipt.json"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
