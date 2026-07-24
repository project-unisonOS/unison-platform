#!/usr/bin/env python3
"""Transactional filesystem primitive for supported appliance installation."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

SCHEMA = "unison.platform.install-transaction.v1"
PURGE_CONFIRMATION = "DESTROY-UNISON-PERSONAL-DATA"


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class Installer:
    def __init__(self, prefix: Path, data_dir: Path):
        self.prefix = prefix
        self.data_dir = data_dir
        self.releases = prefix / "releases"
        self.state = prefix / "install-state.json"
        self.current = prefix / "current"

    def _write_state(self, **values) -> None:
        self.prefix.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": SCHEMA, **values}
        temporary = self.state.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, self.state)

    def _activate(self, target: Path) -> None:
        link = self.prefix / ".current.next"
        link.unlink(missing_ok=True)
        link.symlink_to(target.relative_to(self.prefix))
        os.replace(link, self.current)

    def install(self, bundle: Path, version: str, fail_at: str = "") -> dict:
        if not bundle.is_dir() or not version or "/" in version:
            raise ValueError("bundle directory and simple version are required")
        bundle_hash = tree_digest(bundle)
        target = self.releases / version
        if target.is_dir() and tree_digest(target) == bundle_hash:
            self._activate(target)
            self._write_state(status="installed", version=version, bundle_sha256=bundle_hash)
            return {"status": "already-installed", "version": version}

        staging = self.releases / f".{version}.staging"
        previous = self.current.resolve() if self.current.exists() else None
        shutil.rmtree(staging, ignore_errors=True)
        self.releases.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._write_state(status="staging", version=version, bundle_sha256=bundle_hash)
        try:
            shutil.copytree(bundle, staging)
            if fail_at == "after-copy":
                raise RuntimeError("injected interruption after copy")
            if tree_digest(staging) != bundle_hash:
                raise RuntimeError("staged bundle digest mismatch")
            if target.exists():
                shutil.rmtree(target)
            os.replace(staging, target)
            if fail_at == "before-activate":
                raise RuntimeError("injected interruption before activation")
            self._activate(target)
            self._write_state(status="installed", version=version, bundle_sha256=bundle_hash)
            return {"status": "installed", "version": version}
        except Exception as error:
            shutil.rmtree(staging, ignore_errors=True)
            if previous and previous.exists():
                self._activate(previous)
            self._write_state(
                status="interrupted", version=version, bundle_sha256=bundle_hash,
                error=type(error).__name__,
            )
            raise

    def repair(self) -> dict:
        candidates = sorted(
            (path for path in self.releases.iterdir() if path.is_dir() and not path.name.startswith(".")),
            key=lambda path: path.stat().st_mtime_ns,
        ) if self.releases.exists() else []
        if not candidates:
            raise RuntimeError("no installed release is available for repair")
        target = candidates[-1]
        self._activate(target)
        self._write_state(status="installed", version=target.name, bundle_sha256=tree_digest(target))
        return {"status": "repaired", "version": target.name}

    def uninstall(self, purge_data: bool = False, confirmation: str = "") -> dict:
        if purge_data and confirmation != PURGE_CONFIRMATION:
            raise PermissionError("factory reset requires the exact destruction confirmation")
        self.current.unlink(missing_ok=True)
        shutil.rmtree(self.releases, ignore_errors=True)
        self.state.unlink(missing_ok=True)
        if purge_data:
            shutil.rmtree(self.data_dir, ignore_errors=True)
        return {"status": "removed", "personal_data": "destroyed" if purge_data else "preserved"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install")
    install.add_argument("--bundle", required=True, type=Path)
    install.add_argument("--version", required=True)
    sub.add_parser("repair")
    remove = sub.add_parser("uninstall")
    remove.add_argument("--purge-data", action="store_true")
    remove.add_argument("--confirmation", default="")
    args = parser.parse_args()
    engine = Installer(args.prefix, args.data_dir)
    if args.command == "install":
        result = engine.install(args.bundle, args.version)
    elif args.command == "repair":
        result = engine.repair()
    else:
        result = engine.uninstall(args.purge_data, args.confirmation)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
