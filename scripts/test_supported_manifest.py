#!/usr/bin/env python3
"""Dependency-free reproducibility and negative tests for release manifests."""

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_supported_manifest.py"
IMAGES = ROOT / "releases/supported-images.example.env"


def generate(path: Path) -> dict:
    subprocess.run(
        [
            str(SCRIPT), "--version", "v0.1.0-rc.1",
            "--images-env", str(IMAGES), "--out", str(path),
            "--source-date-epoch", "1784764800", "--allow-placeholder",
        ],
        check=True,
    )
    return json.loads(path.read_text())


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        first = root / "a/manifest.json"
        second = root / "b/manifest.json"
        one = generate(first)
        two = generate(second)
        assert one == two
        assert first.read_bytes() == second.read_bytes()
        assert one["runtime"]["service_count"] == 13
        assert set(one["runtime"]["images"]) == set(one["licenses"]["images"])
        assert one["release"]["created_at"] == "2026-07-23T00:00:00Z"
        assert str(ROOT) not in first.read_text()

        result = subprocess.run(
            [
                str(SCRIPT), "--version", "v0.1.0",
                "--images-env", str(IMAGES), "--out", str(root / "publish.json"),
                "--source-date-epoch", "1784764800",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "zero digest" in result.stderr
    print("[PASS] Supported release manifest is complete and reproducible.")


if __name__ == "__main__":
    main()
