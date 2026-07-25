#!/usr/bin/env python3
"""Inspect local wellbeing or evaluate a deterministic maintenance scenario."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maintenance.collector import collect_device_profile, evaluate_health  # noqa: E402
from maintenance.simulator import MaintenanceSimulator  # noqa: E402
from maintenance.wellbeing import wellbeing_projection  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, help="evaluate a synthetic JSON scenario")
    parser.add_argument("--samples", type=Path, help="local aggregate sample JSON")
    parser.add_argument("--wellbeing-out", type=Path, help="write the renderer-safe wellbeing projection")
    args = parser.parse_args()
    if args.scenario:
        scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
        result = MaintenanceSimulator().run(scenario)
        observed_at = scenario["at"]
    else:
        profile = collect_device_profile()
        samples = json.loads(args.samples.read_text(encoding="utf-8")) if args.samples else {}
        result = {
            "device_profile": profile,
            "observations": [item.__dict__ for item in evaluate_health(profile, samples)],
            "privacy": {
                "personal_content_collected": False,
                "redactions": profile["redactions"],
            },
        }
        observed_at = profile["observed_at"]
    if args.wellbeing_out:
        args.wellbeing_out.parent.mkdir(parents=True, exist_ok=True)
        args.wellbeing_out.write_text(
            json.dumps(wellbeing_projection(result, observed_at=observed_at), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
