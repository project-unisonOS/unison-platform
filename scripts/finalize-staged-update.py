#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import requests


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="/opt/unison-platform", help="Install prefix with staged metadata")
    parser.add_argument("--updates-base-url", default="http://127.0.0.1:8094", help="Base URL for unison-updates")
    parser.add_argument("--retain-staged", action="store_true", help="Retain staged files after finalize")
    ns = parser.parse_args()

    prefix = Path(ns.prefix)
    staged_dir = prefix / "staged"
    metadata_path = staged_dir / "compose.next-boot.metadata.json"
    override_path = staged_dir / "compose.next-boot.override.yaml"
    if not metadata_path.exists():
        raise SystemExit(f"missing staged metadata: {metadata_path}")
    metadata = _load_json(metadata_path)
    job_id = metadata.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise SystemExit("staged metadata missing job_id")

    resp = requests.post(
        f"{ns.updates_base_url}/v1/tools/updates.record_applied",
        json={"arguments": {"job_id": job_id}},
        timeout=5,
    )
    resp.raise_for_status()
    body = resp.json()

    archive_dir = staged_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived: dict[str, str] = {}
    for path in (override_path, metadata_path):
        if not path.exists():
            continue
        archived_path = archive_dir / path.name.replace("compose.next-boot", f"{job_id}.next-boot")
        shutil.copy2(path, archived_path)
        archived[path.name] = str(archived_path)
        if not ns.retain_staged:
            path.unlink()

    print(
        json.dumps(
            {
                "ok": True,
                "job_id": job_id,
                "archived": archived,
                "retained": bool(ns.retain_staged),
                "last_known_good": body.get("last_known_good"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
