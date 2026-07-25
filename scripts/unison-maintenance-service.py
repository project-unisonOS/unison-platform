#!/usr/bin/env python3
"""Run one crash-safe adaptive-maintenance service cycle."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maintenance.service import MaintenanceService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=Path("/var/lib/unison/maintenance"))
    parser.add_argument("--registry", type=Path, default=Path("/etc/unison/maintenance-sources.json"))
    parser.add_argument(
        "--registry-public-key",
        type=Path,
        default=Path("/etc/unison/trust/maintenance-sources-ed25519.pem"),
    )
    parser.add_argument("--device-id", default=os.getenv("UNISON_DEVICE_ID", "local-appliance"))
    parser.add_argument("--no-collect", action="store_true")
    args = parser.parse_args()
    service = MaintenanceService(
        state_path=args.state_dir / "state.json",
        command_dir=args.state_dir / "commands",
        wellbeing_path=args.state_dir / "wellbeing.json",
        registry_path=args.registry,
        registry_public_key=args.registry_public_key,
        device_id=args.device_id,
    )
    print(json.dumps(service.run_once(collect=not args.no_collect), sort_keys=True))


if __name__ == "__main__":
    main()
