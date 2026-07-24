#!/usr/bin/env python3
"""Dependency-free transaction, interruption, repair, and removal tests."""

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from installer.transaction import Installer, PURGE_CONFIRMATION


def bundle(root: Path, version: str) -> Path:
    path = root / f"bundle-{version}"
    path.mkdir()
    (path / "manifest.json").write_text(f'{{"version":"{version}"}}\n')
    (path / "compose.yaml").write_text(f"# {version}\n")
    return path


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        prefix, data = root / "opt", root / "personal-data"
        engine = Installer(prefix, data)
        v1, v2 = bundle(root, "v1"), bundle(root, "v2")

        assert engine.install(v1, "v1")["status"] == "installed"
        assert engine.current.resolve() == prefix / "releases/v1"
        (data / "canary").write_text("personal")
        assert engine.install(v1, "v1")["status"] == "already-installed"

        for point in ("after-copy", "before-activate"):
            try:
                engine.install(v2, "v2", fail_at=point)
                raise AssertionError(f"{point} did not fail")
            except RuntimeError:
                pass
            assert engine.current.resolve() == prefix / "releases/v1"
            assert (data / "canary").read_text() == "personal"

        engine.current.unlink()
        assert engine.repair()["version"] == "v2"
        assert engine.current.resolve() == prefix / "releases/v2"

        assert engine.uninstall()["personal_data"] == "preserved"
        assert (data / "canary").read_text() == "personal"
        engine.install(v1, "v1")
        try:
            engine.uninstall(purge_data=True, confirmation="yes")
            raise AssertionError("weak factory-reset confirmation was accepted")
        except PermissionError:
            pass
        assert data.exists()
        result = engine.uninstall(purge_data=True, confirmation=PURGE_CONFIRMATION)
        assert result["personal_data"] == "destroyed"
        assert not data.exists()
    print("[PASS] Installer transactions survive interruption and separate removal from data destruction.")


if __name__ == "__main__":
    main()
