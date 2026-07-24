#!/usr/bin/env python3
"""Complete signed-bundle update, health promotion, and rollback simulations."""

import hashlib
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.release_bundle import assemble_bundle, sha256_file, sign, verify_bundle
from installer.transaction import Installer, tree_digest
from installer.update_transaction import UpdateError, UpdateTransaction

GENERATE = ROOT / "scripts/generate_supported_manifest.py"
EXAMPLE_IMAGES = ROOT / "releases/supported-images.example.env"


def image_environment(path: Path) -> None:
    lines = []
    for line in EXAMPLE_IMAGES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        key, image = line.split("=", 1)
        lines.append(f"{key}={image[:-64]}{hashlib.sha256(key.encode()).hexdigest()}")
    path.write_text("\n".join(lines) + "\n")


def release(root: Path, version: str, key: Path, images: Path) -> Path:
    manifest = root / f"{version}.manifest.json"
    bundle = root / f"unisonos-{version}.tar"
    subprocess.run([
        str(GENERATE), "--version", version, "--images-env", str(images),
        "--out", str(manifest), "--source-date-epoch", "1784764800",
    ], check=True)
    assemble_bundle(manifest, images, bundle, key, ROOT)
    return bundle


def update_root(private_key: Path, path: Path) -> None:
    public_der = subprocess.run([
        "openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"
    ], check=True, capture_output=True).stdout
    root = {
        "signed": {
            "_type": "root",
            "version": 1,
            "expires": "2027-07-24T00:00:00Z",
            "keys": {
                "update-k0": {
                    "keytype": "ed25519",
                    "public": base64.b64encode(public_der[-32:]).decode(),
                }
            },
            "roles": {"targets": {"keyids": ["update-k0"], "threshold": 1}},
        },
        "signatures": [],
    }
    path.write_text(json.dumps(root, sort_keys=True) + "\n")


def authorization(
    bundle: Path, version: str, target_version: int, private_key: Path
) -> dict:
    signed = {
        "_type": "targets",
        "version": target_version,
        "channel": "stable",
        "expires": "2026-08-24T00:00:00Z",
        "target": {
            "path": bundle.name,
            "version": target_version,
            "length": bundle.stat().st_size,
            "hashes": {"sha256": sha256_file(bundle)},
            "custom": {
                "release_version": version,
                "hardware": {"os": "ubuntu-24.04", "architecture": "x86_64"},
                "restart": True,
                "backup_required": True,
            },
        },
    }
    payload = json.dumps(
        signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    envelope = {
        "signed": signed,
        "signatures": [{
            "keyid": "update-k0",
            "sig": base64.b64encode(sign(payload, private_key)).decode(),
        }],
    }
    return {
        "schema_version": "unison.updates.verified-target.v1",
        "verified_at": "2026-07-24T00:00:00Z",
        "trusted_root_version": 1,
        "channel": "stable",
        "channel_metadata_version": target_version,
        "target": {
            "path": signed["target"]["path"],
            "version": signed["target"]["version"],
            "release_version": version,
            "length": signed["target"]["length"],
            "sha256": signed["target"]["hashes"]["sha256"],
            "hardware": {"os": "ubuntu-24.04", "architecture": "x86_64"},
            "restart": True,
            "backup_required": True,
        },
        "evidence": {"channel_metadata": envelope},
    }


def install_base(root: Path, bundle: Path, public_key: Path) -> tuple[Path, Path]:
    prefix, data = root / "opt", root / "personal-data"
    verified = verify_bundle(bundle, public_key)
    materialized = verified.materialize(root / "base-materialized")
    Installer(prefix, data).install(
        materialized,
        verified.manifest["release"]["version"],
        receipt=verified.receipt(tree_digest(materialized)),
    )
    (data / "state").write_text("known-good")
    return prefix, data


def engine(
    prefix: Path,
    data: Path,
    public_key: Path,
    trusted_update_root: Path,
    health,
    available=lambda _path: 10**12,
) -> UpdateTransaction:
    return UpdateTransaction(
        prefix, data, public_key, trusted_update_root, health,
        health_attempts=3, available_bytes=available
    )


def expect_failure(call, phrase: str) -> None:
    try:
        call()
        raise AssertionError(f"expected failure containing {phrase}")
    except UpdateError as error:
        assert phrase in str(error), str(error)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        fixtures = Path(directory)
        images = fixtures / "images.env"
        private_key = fixtures / "release-private.pem"
        public_key = fixtures / "release-public.pem"
        trusted_update_root = fixtures / "trusted-update-root.json"
        image_environment(images)
        subprocess.run([
            "openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)
        ], check=True, capture_output=True)
        public_key.write_bytes(subprocess.run([
            "openssl", "pkey", "-in", str(private_key), "-pubout"
        ], check=True, capture_output=True).stdout)
        update_root(private_key, trusted_update_root)
        v1 = release(fixtures, "v0.1.0", private_key, images)
        v2 = release(fixtures, "v0.2.0", private_key, images)
        v3 = release(fixtures, "v0.3.0", private_key, images)

        # N-1 -> N promotion and explicit owner rollback.
        case = fixtures / "promote"
        case.mkdir()
        prefix, data = install_base(case, v1, public_key)
        result = engine(
            prefix, data, public_key, trusted_update_root,
            lambda attempt, version: attempt == 2
        ).apply(
            v2, authorization(v2, "v0.2.0", 2, private_key)
        )
        assert result == {"status": "promoted", "version": "v0.2.0", "previous": "v0.1.0"}
        assert prefix.joinpath("current").resolve().name == "v0.2.0"
        assert json.loads(prefix.joinpath("update-state.json").read_text())["health_attempts"] == [
            {"attempt": 1, "healthy": False}, {"attempt": 2, "healthy": True}
        ]
        assert engine(prefix, data, public_key, trusted_update_root, lambda *_: True).rollback() == {
            "status": "rolled-back", "restored": "v0.1.0"
        }
        assert prefix.joinpath("current").resolve().name == "v0.1.0"
        assert data.joinpath("state").read_text() == "known-good"

        # N -> N+1 migration/health failure restores release, receipt, and data.
        case = fixtures / "automatic"
        case.mkdir()
        prefix, data = install_base(case, v1, public_key)
        engine(prefix, data, public_key, trusted_update_root, lambda *_: True).apply(
            v2, authorization(v2, "v0.2.0", 2, private_key)
        )
        receipt_before = prefix.joinpath("install-receipt.json").read_bytes()
        expect_failure(
            lambda: engine(prefix, data, public_key, trusted_update_root, lambda *_: False).apply(
                v3,
                authorization(v3, "v0.3.0", 3, private_key),
                migration=lambda path: path.joinpath("state").write_text("bad-migration"),
            ),
            "rolled back automatically",
        )
        assert prefix.joinpath("current").resolve().name == "v0.2.0"
        assert data.joinpath("state").read_text() == "known-good"
        assert prefix.joinpath("install-receipt.json").read_bytes() == receipt_before
        rolled_back = json.loads(prefix.joinpath("update-state.json").read_text())
        assert rolled_back["status"] == "rolled-back" and rolled_back["automatic"] is True

        # Staging interruption never changes current and the same verified target can resume.
        case = fixtures / "interruption"
        case.mkdir()
        prefix, data = install_base(case, v1, public_key)
        auth_v2 = authorization(v2, "v0.2.0", 2, private_key)
        expect_failure(
            lambda: engine(prefix, data, public_key, trusted_update_root, lambda *_: True).apply(
                v2, auth_v2, fail_at="after-stage"
            ),
            "interruption after staging",
        )
        assert prefix.joinpath("current").resolve().name == "v0.1.0"
        assert engine(prefix, data, public_key, trusted_update_root, lambda *_: True).apply(
            v2, auth_v2
        )["status"] == "promoted"

        # Post-activation interruption is automatically rolled back.
        case = fixtures / "post-activate"
        case.mkdir()
        prefix, data = install_base(case, v1, public_key)
        expect_failure(
            lambda: engine(prefix, data, public_key, trusted_update_root, lambda *_: True).apply(
                v2, authorization(v2, "v0.2.0", 2, private_key), fail_at="after-activate"
            ),
            "rolled back automatically",
        )
        assert prefix.joinpath("current").resolve().name == "v0.1.0"

        # Disk rejection occurs before checkpoint/staging and remains retryable.
        case = fixtures / "disk-full"
        case.mkdir()
        prefix, data = install_base(case, v1, public_key)
        auth_v2 = authorization(v2, "v0.2.0", 2, private_key)
        expect_failure(
            lambda: engine(
                prefix, data, public_key, trusted_update_root,
                lambda *_: True, available=lambda _path: 0
            ).apply(v2, auth_v2),
            "insufficient disk space",
        )
        assert prefix.joinpath("current").resolve().name == "v0.1.0"
        assert not prefix.joinpath("update-checkpoints").exists()
        assert engine(prefix, data, public_key, trusted_update_root, lambda *_: True).apply(
            v2, auth_v2
        )["status"] == "promoted"

        # Replacement-restored state remains intact through the update.
        case = fixtures / "restored-device"
        case.mkdir()
        prefix, data = install_base(case, v1, public_key)
        data.joinpath("replacement-restore-proof").write_text("verified")
        engine(prefix, data, public_key, trusted_update_root, lambda *_: True).apply(
            v2, authorization(v2, "v0.2.0", 2, private_key)
        )
        assert data.joinpath("replacement-restore-proof").read_text() == "verified"

        # Authorization cannot be reused for different bytes, versions, channels, or hardware.
        case = fixtures / "authorization"
        case.mkdir()
        prefix, data = install_base(case, v1, public_key)
        for mutate, phrase in (
            (lambda value: value["target"].update(sha256="0" * 64), "differs from signed metadata"),
            (lambda value: value["target"].update(release_version="v9"), "differs from signed metadata"),
            (lambda value: value.update(channel="preview"), "channel differs"),
            (lambda value: value["target"].update(hardware={
                "os": "ubuntu-24.04", "architecture": "arm64"
            }), "differs from signed metadata"),
        ):
            candidate = authorization(v2, "v0.2.0", 2, private_key)
            mutate(candidate)
            expect_failure(
                lambda value=candidate: engine(
                    prefix, data, public_key, trusted_update_root, lambda *_: True
                ).apply(v2, value),
                phrase,
            )
        tampered = authorization(v2, "v0.2.0", 2, private_key)
        tampered["target"]["sha256"] = "0" * 64
        tampered["evidence"]["channel_metadata"]["signed"]["target"]["hashes"]["sha256"] = "0" * 64
        expect_failure(
            lambda: engine(
                prefix, data, public_key, trusted_update_root, lambda *_: True
            ).apply(v2, tampered),
            "signature threshold",
        )
        expired_root = fixtures / "expired-update-root.json"
        expired = json.loads(trusted_update_root.read_text())
        expired["signed"]["expires"] = "2026-07-23T00:00:00Z"
        expired_root.write_text(json.dumps(expired) + "\n")
        expect_failure(
            lambda: engine(
                prefix, data, public_key, expired_root, lambda *_: True
            ).apply(v2, authorization(v2, "v0.2.0", 2, private_key)),
            "trusted update root is expired",
        )

    print(
        "[PASS] Verified targets checkpoint, stage, promote, resume, and roll back "
        "without data loss across lifecycle failures."
    )


if __name__ == "__main__":
    main()
