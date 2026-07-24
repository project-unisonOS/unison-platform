#!/usr/bin/env python3
"""Determinism, trust, preview, receipt, and adversarial bundle acceptance."""

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from installer.release_bundle import BundleError, assemble_bundle, verify_bundle
from installer.transaction import Installer

GENERATE = ROOT / "scripts/generate_supported_manifest.py"
EXAMPLE_IMAGES = ROOT / "releases/supported-images.example.env"


def test_images(path: Path) -> None:
    lines = []
    for line in EXAMPLE_IMAGES.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        key, image = line.split("=", 1)
        digest = hashlib.sha256(key.encode()).hexdigest()
        lines.append(f"{key}={image[:-64]}{digest}")
    path.write_text("\n".join(lines) + "\n")


def mutate(source: Path, target: Path, change) -> None:
    with tarfile.open(source, "r:") as archive:
        files = {
            member.name: archive.extractfile(member).read()
            for member in archive
            if member.isfile()
        }
    change(files)
    with tarfile.open(target, "w", format=tarfile.PAX_FORMAT) as archive:
        for name, content in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def rejected(bundle: Path, key: Path, expected: str) -> None:
    try:
        verify_bundle(bundle, key)
        raise AssertionError(f"accepted invalid bundle: {bundle}")
    except BundleError as error:
        assert expected in str(error), str(error)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        images = root / "images.env"
        manifest = root / "manifest.json"
        private_key = root / "release-private.pem"
        public_key = root / "release-public.pem"
        test_images(images)
        subprocess.run([
            str(GENERATE), "--version", "v0.1.0-rc.2", "--images-env", str(images),
            "--out", str(manifest), "--source-date-epoch", "1784764800",
        ], check=True)
        subprocess.run([
            "openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private_key)
        ], check=True, capture_output=True)
        public_key.write_bytes(subprocess.run([
            "openssl", "pkey", "-in", str(private_key), "-pubout"
        ], check=True, capture_output=True).stdout)

        first, second = root / "first.tar", root / "second.tar"
        assemble_bundle(manifest, images, first, private_key, ROOT)
        assemble_bundle(manifest, images, second, private_key, ROOT)
        assert first.read_bytes() == second.read_bytes()
        swapped_images = root / "swapped-images.env"
        swapped = images.read_text().splitlines()
        first_value = swapped[0].split("=", 1)[1]
        second_value = swapped[1].split("=", 1)[1]
        swapped[0] = swapped[0].split("=", 1)[0] + "=" + second_value
        swapped[1] = swapped[1].split("=", 1)[0] + "=" + first_value
        swapped_images.write_text("\n".join(swapped) + "\n")
        try:
            assemble_bundle(manifest, swapped_images, root / "swapped.tar", private_key, ROOT)
            raise AssertionError("accepted images assigned to the wrong services")
        except BundleError as error:
            assert "image environment" in str(error)

        verified = verify_bundle(first, public_key)
        assert len(verified.index["files"]) == 6

        prefix, data = root / "opt", root / "personal-data"
        plan = verified.installation_plan(prefix, data)
        assert plan["requires_privilege_after_confirmation"] is True
        assert plan["personal_data_destroyed"] is False
        assert plan["changes"][0]["path"] == str(prefix / "releases/v0.1.0-rc.2")
        assert plan["changes"][2]["path"] == str(data)
        assert plan["trusted_public_key_sha256"] == hashlib.sha256(public_key.read_bytes()).hexdigest()
        assert verified.plan_sha256(prefix, data) != verified.plan_sha256(prefix, root / "other-data")
        bootstrap = [
            str(ROOT / "installer/bootstrap.py"),
            "--bundle", str(first),
            "--trusted-public-key", str(public_key),
            "--prefix", str(prefix),
            "--data-dir", str(data),
        ]
        preview = json.loads(subprocess.run(
            [*bootstrap, "verify"], check=True, capture_output=True, text=True
        ).stdout)
        assert preview["plan"] == plan
        assert preview["plan_sha256"] == verified.plan_sha256(prefix, data)
        refused = subprocess.run(
            [*bootstrap, "install", "--accept-plan-sha256", "wrong"],
            capture_output=True,
            text=True,
        )
        assert refused.returncode != 0
        assert not prefix.exists()
        installed = json.loads(subprocess.run([
            *bootstrap, "install", "--accept-plan-sha256", preview["plan_sha256"]
        ], check=True, capture_output=True, text=True).stdout)
        assert installed["status"] == "installed"
        engine = Installer(prefix, data)
        receipt = json.loads(engine.receipt.read_text())
        assert receipt["bundle_index_sha256"] == verified.index_sha256
        installed_again = json.loads(subprocess.run([
            *bootstrap, "install", "--accept-plan-sha256", preview["plan_sha256"]
        ], check=True, capture_output=True, text=True).stdout)
        assert installed_again["status"] == "already-installed"
        (data / "canary").write_text("personal")
        assert engine.uninstall()["personal_data"] == "preserved"
        assert (data / "canary").read_text() == "personal"
        assert not engine.receipt.exists()

        corrupt = root / "corrupt.tar"
        mutate(first, corrupt, lambda files: files.__setitem__(
            "compose/compose.supported.yaml",
            files["compose/compose.supported.yaml"] + b"\n# corruption\n",
        ))
        rejected(corrupt, public_key, "signed metadata mismatch")

        bad_signature = root / "bad-signature.tar"
        mutate(first, bad_signature, lambda files: files.__setitem__(
            "bundle-index.sig", bytes([files["bundle-index.sig"][0] ^ 1]) + files["bundle-index.sig"][1:]
        ))
        rejected(bad_signature, public_key, "OpenSSL operation failed")

        missing = root / "missing.tar"
        mutate(first, missing, lambda files: files.pop("release/supported-licenses.json"))
        rejected(missing, public_key, "bundle inventory mismatch")

        extra = root / "extra.tar"
        mutate(first, extra, lambda files: files.__setitem__("undeclared", b"unsafe"))
        rejected(extra, public_key, "bundle inventory mismatch")

        other_private = root / "other-private.pem"
        other_public = root / "other-public.pem"
        subprocess.run([
            "openssl", "genpkey", "-algorithm", "ED25519", "-out", str(other_private)
        ], check=True, capture_output=True)
        other_public.write_bytes(subprocess.run([
            "openssl", "pkey", "-in", str(other_private), "-pubout"
        ], check=True, capture_output=True).stdout)
        rejected(first, other_public, "embedded signing key")

    print(
        "[PASS] Signed bundles are reproducible, verified before privilege, "
        "receipt-reconciled, idempotent, and fail closed."
    )


if __name__ == "__main__":
    main()
