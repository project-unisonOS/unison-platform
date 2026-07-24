#!/usr/bin/env python3
"""Deterministic signed release bundles and pre-privilege bootstrap verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess  # nosec B404 - openssl is the explicit release signing boundary
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

BUNDLE_SCHEMA = "unison.platform.release-bundle.v1"
PLAN_SCHEMA = "unison.platform.install-plan.v1"
RECEIPT_SCHEMA = "unison.platform.install-receipt.v1"
INDEX_NAME = "bundle-index.json"
SIGNATURE_NAME = "bundle-index.sig"
PUBLIC_KEY_NAME = "bundle-signing-key.pem"
MANIFEST_NAME = "release-manifest.json"
REQUIRED_PAYLOAD = {
    MANIFEST_NAME,
    "compose/compose.supported.yaml",
    "release/supported-images.env",
    "release/supported-host-requirements.json",
    "release/supported-licenses.json",
    "release/model-profile.json",
}
DIGEST_REFERENCE = re.compile(r"^[^\s:@]+(?::[^\s@]+)?@sha256:[0-9a-f]{64}$")
IMAGE_ALIASES = {
    "UNISON_RENDERER_IMAGE": "experience-renderer",
    "UNISON_SPEECH_IMAGE": "io-speech",
}


class BundleError(RuntimeError):
    """A bundle cannot be trusted or reconciled."""


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _openssl(*args: str, input_bytes: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(  # nosec B603
            ["openssl", *args],
            input=input_bytes,
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", b"").decode(errors="replace").strip()
        raise BundleError(f"OpenSSL operation failed: {detail or type(error).__name__}") from error
    return result.stdout


def sign(index_bytes: bytes, private_key: Path) -> bytes:
    with tempfile.NamedTemporaryFile() as index_file:
        index_file.write(index_bytes)
        index_file.flush()
        return _openssl(
            "pkeyutl", "-sign", "-rawin", "-inkey", str(private_key), "-in", index_file.name
        )


def public_key(private_key: Path) -> bytes:
    return _openssl("pkey", "-in", str(private_key), "-pubout")


def verify_signature(index_bytes: bytes, signature: bytes, public_key_path: Path) -> None:
    with tempfile.NamedTemporaryFile() as signature_file, tempfile.NamedTemporaryFile() as index_file:
        signature_file.write(signature)
        signature_file.flush()
        index_file.write(index_bytes)
        index_file.flush()
        _openssl(
            "pkeyutl", "-verify", "-rawin", "-pubin", "-inkey", str(public_key_path),
            "-sigfile", signature_file.name, "-in", index_file.name,
        )


def _validate_member_name(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise BundleError(f"unsafe bundle member: {name}")


def _read_tar(bundle: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    try:
        with tarfile.open(bundle, "r:") as archive:
            for member in archive:
                _validate_member_name(member.name)
                if not member.isfile():
                    raise BundleError(f"non-regular bundle member: {member.name}")
                if member.name in files:
                    raise BundleError(f"duplicate bundle member: {member.name}")
                handle = archive.extractfile(member)
                if handle is None:
                    raise BundleError(f"unreadable bundle member: {member.name}")
                files[member.name] = handle.read()
    except (tarfile.TarError, OSError) as error:
        raise BundleError("bundle is not a readable uncompressed tar archive") from error
    return files


def _validate_manifest(manifest: dict, payload: dict[str, bytes]) -> None:
    if manifest.get("schema_version") != "unison.platform.supported-release.v1":
        raise BundleError("unsupported release manifest schema")
    runtime = manifest.get("runtime", {})
    images = runtime.get("images", {})
    if runtime.get("service_count") != 13 or len(images) != 13:
        raise BundleError("release manifest must declare exactly 13 services")
    if any(
        not DIGEST_REFERENCE.fullmatch(str(image)) or str(image).endswith("0" * 64)
        for image in images.values()
    ):
        raise BundleError("release manifest contains a mutable or placeholder image")
    compose = payload["compose/compose.supported.yaml"]
    if runtime.get("compose", {}).get("sha256") != sha256_bytes(compose):
        raise BundleError("Compose content does not match the release manifest")
    image_lines = {
        IMAGE_ALIASES.get(
            line.split("=", 1)[0],
            line.split("=", 1)[0]
            .removeprefix("UNISON_")
            .removesuffix("_IMAGE")
            .lower()
            .replace("_", "-"),
        ): line.split("=", 1)[1]
        for line in payload["release/supported-images.env"].decode().splitlines()
        if line and not line.startswith("#")
    }
    if image_lines != images:
        raise BundleError("image environment does not match the release manifest")
    declared_licenses = json.loads(payload["release/supported-licenses.json"])
    if declared_licenses != manifest.get("licenses"):
        raise BundleError("license inventory does not match the release manifest")
    requirements = json.loads(payload["release/supported-host-requirements.json"])
    if requirements != manifest.get("compatibility"):
        raise BundleError("host requirements do not match the release manifest")
    model = json.loads(payload["release/model-profile.json"])
    if sha256_bytes(payload["release/model-profile.json"]) != manifest.get("versions", {}).get(
        "model_profile_sha256"
    ):
        raise BundleError("model profile does not match the release manifest")
    if model.get("profile") != manifest.get("versions", {}).get("model_profile"):
        raise BundleError("model profile identity does not match the release manifest")


@dataclass(frozen=True)
class VerifiedBundle:
    files: dict[str, bytes]
    index: dict
    manifest: dict
    index_sha256: str
    trusted_public_key_sha256: str

    def installation_plan(self, prefix: Path, data_dir: Path) -> dict:
        version = self.manifest["release"]["version"]
        return {
            "schema_version": PLAN_SCHEMA,
            "version": version,
            "bundle_index_sha256": self.index_sha256,
            "trusted_public_key_sha256": self.trusted_public_key_sha256,
            "requires_privilege_after_confirmation": True,
            "personal_data_destroyed": False,
            "changes": [
                {"action": "create-or-reuse", "path": str(prefix / "releases" / version)},
                {"action": "atomically-point", "path": str(prefix / "current")},
                {"action": "create-if-missing", "path": str(data_dir)},
                {"action": "write", "path": str(prefix / "install-state.json")},
                {"action": "write", "path": str(prefix / "install-receipt.json")},
            ],
        }

    def plan_sha256(self, prefix: Path, data_dir: Path) -> str:
        return sha256_bytes(canonical_json(self.installation_plan(prefix, data_dir)))

    def materialize(self, destination: Path) -> Path:
        destination.mkdir(parents=True, exist_ok=False)
        for name, content in sorted(self.files.items()):
            if name in {INDEX_NAME, SIGNATURE_NAME, PUBLIC_KEY_NAME}:
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return destination

    def receipt(self, installed_tree_sha256: str) -> dict:
        return {
            "schema_version": RECEIPT_SCHEMA,
            "release": self.manifest["release"],
            "bundle_index_sha256": self.index_sha256,
            "release_manifest_sha256": sha256_bytes(self.files[MANIFEST_NAME]),
            "installed_tree_sha256": installed_tree_sha256,
            "files": self.index["files"],
        }


def verify_bundle(bundle: Path, trusted_public_key: Path) -> VerifiedBundle:
    files = _read_tar(bundle)
    required = REQUIRED_PAYLOAD | {INDEX_NAME, SIGNATURE_NAME, PUBLIC_KEY_NAME}
    if set(files) != required:
        raise BundleError(f"bundle inventory mismatch: {sorted(set(files) ^ required)}")
    if files[PUBLIC_KEY_NAME] != trusted_public_key.read_bytes():
        raise BundleError("embedded signing key does not match the trusted release key")
    try:
        index = json.loads(files[INDEX_NAME])
        manifest = json.loads(files[MANIFEST_NAME])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BundleError("bundle metadata is not valid JSON") from error
    index_bytes = canonical_json(index)
    if files[INDEX_NAME] != index_bytes:
        raise BundleError("bundle index is not canonical JSON")
    verify_signature(index_bytes, files[SIGNATURE_NAME], trusted_public_key)
    if index.get("schema_version") != BUNDLE_SCHEMA:
        raise BundleError("unsupported bundle schema")
    indexed = index.get("files")
    if not isinstance(indexed, dict) or set(indexed) != REQUIRED_PAYLOAD:
        raise BundleError("signed bundle index inventory is incomplete")
    for name, metadata in indexed.items():
        content = files[name]
        if metadata != {"length": len(content), "sha256": sha256_bytes(content)}:
            raise BundleError(f"signed metadata mismatch for {name}")
    if index.get("release") != manifest.get("release"):
        raise BundleError("bundle and release identities do not match")
    _validate_manifest(manifest, files)
    return VerifiedBundle(
        files,
        index,
        manifest,
        sha256_bytes(index_bytes),
        sha256_file(trusted_public_key),
    )


def assemble_bundle(
    manifest_path: Path,
    images_env: Path,
    output: Path,
    private_key: Path,
    root: Path,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload_paths = {
        MANIFEST_NAME: manifest_path,
        "compose/compose.supported.yaml": root / "compose/compose.supported.yaml",
        "release/supported-images.env": images_env,
        "release/supported-host-requirements.json": root / "releases/supported-host-requirements.json",
        "release/supported-licenses.json": root / "releases/supported-licenses.json",
        "release/model-profile.json": root / "model-packs/alpha/default.json",
    }
    payload = {name: path.read_bytes() for name, path in payload_paths.items()}
    _validate_manifest(manifest, payload)
    index = {
        "schema_version": BUNDLE_SCHEMA,
        "release": manifest["release"],
        "files": {
            name: {"length": len(content), "sha256": sha256_bytes(content)}
            for name, content in sorted(payload.items())
        },
    }
    index_bytes = canonical_json(index)
    all_files = {
        **payload,
        INDEX_NAME: index_bytes,
        SIGNATURE_NAME: sign(index_bytes, private_key),
        PUBLIC_KEY_NAME: public_key(private_key),
    }
    epoch = int(manifest["release"]["source_date_epoch"])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with tarfile.open(temporary, "w", format=tarfile.PAX_FORMAT) as archive:
        for name, content in sorted(all_files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = epoch
            archive.addfile(info, fileobj=_BytesReader(content))
    os.replace(temporary, output)
    return index


class _BytesReader:
    def __init__(self, value: bytes):
        self.value = value
        self.offset = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.value) - self.offset
        result = self.value[self.offset : self.offset + size]
        self.offset += len(result)
        return result
