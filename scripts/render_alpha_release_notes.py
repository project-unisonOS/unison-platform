#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


def render_template(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--template", default="release-notes/alpha.md")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    assets_dir = Path(args.assets_dir)
    assets = sorted([p.name for p in assets_dir.iterdir() if p.is_file()])
    assets_bullets = "\n".join([f"- `{name}`" for name in assets])

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    template = Path(args.template).read_text(encoding="utf-8")
    body = render_template(
        template,
        {
            "VERSION": args.version,
            "BUILT_AT": built_at,
            "ASSETS_BULLETS": assets_bullets or "- (no assets found)",
            # Placeholders to be filled by release engineer during draft finalization.
            "WHATS_NEW_1": "TBD",
            "WHATS_NEW_2": "TBD",
            "WHATS_NEW_3": "TBD",
            "MVP_WSL2": "TBD",
            "MVP_VM": "TBD",
            "MVP_BAREMETAL": "TBD",
            "MVP_READY": "TBD",
            "MVP_INFERENCE": "TBD",
            "MVP_RENDERER": "TBD",
            "MVP_SMOKE": "TBD",
            "MVP_MODEL_MISSING": "TBD",
            "KNOWN_ISSUE_1": "TBD",
            "KNOWN_ISSUE_2": "TBD",
        },
    ).strip() + "\n"

    Path(args.out).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

