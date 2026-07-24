#!/usr/bin/env python3
"""Checkpointed release-bundle activation with health promotion and rollback."""

from __future__ import annotations

import hashlib
import base64
import json
import os
import shutil
import subprocess  # nosec B404 - OpenSSL is the pinned Ed25519 verification boundary
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from installer.release_bundle import VerifiedBundle, sha256_file, verify_bundle
from installer.transaction import tree_digest

AUTHORIZATION_SCHEMA = "unison.updates.verified-target.v1"
STATE_SCHEMA = "unison.platform.update-transaction.v1"
SUPPORTED_HARDWARE = {"os": "ubuntu-24.04", "architecture": "x86_64"}


class UpdateError(RuntimeError):
    """The target was rejected or could not be safely promoted."""


def directory_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


class UpdateTransaction:
    def __init__(
        self,
        prefix: Path,
        data_dir: Path,
        trusted_public_key: Path,
        trusted_update_root: Path,
        health_check: Callable[[int, str], bool],
        *,
        channel: str = "stable",
        health_attempts: int = 3,
        available_bytes: Callable[[Path], int] | None = None,
    ):
        self.prefix = prefix
        self.data_dir = data_dir
        self.trusted_public_key = trusted_public_key
        self.trusted_update_root = trusted_update_root
        self.health_check = health_check
        self.channel = channel
        self.health_attempts = health_attempts
        self.available_bytes = available_bytes or (
            lambda path: shutil.disk_usage(path if path.exists() else path.parent).free
        )
        self.releases = prefix / "releases"
        self.current = prefix / "current"
        self.receipt = prefix / "install-receipt.json"
        self.state_path = prefix / "update-state.json"
        self.checkpoints = prefix / "update-checkpoints"

    def _state(self) -> dict:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, **values) -> None:
        self.prefix.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"schema_version": STATE_SCHEMA, **values}, indent=2, sort_keys=True) + "\n"
        )
        os.replace(temporary, self.state_path)

    def _activate(self, target: Path) -> None:
        link = self.prefix / ".current.update"
        link.unlink(missing_ok=True)
        link.symlink_to(target.relative_to(self.prefix))
        os.replace(link, self.current)

    def _validate_authorization(
        self, bundle_path: Path, verified: VerifiedBundle, authorization: dict
    ) -> dict:
        if authorization.get("schema_version") != AUTHORIZATION_SCHEMA:
            raise UpdateError("target lacks a verified update authorization")
        self._verify_authorization_metadata(authorization)
        if authorization.get("channel") != self.channel:
            raise UpdateError("target authorization is for the wrong channel")
        target = authorization.get("target", {})
        if target.get("length") != bundle_path.stat().st_size:
            raise UpdateError("authorized target length does not match the bundle")
        if target.get("sha256") != sha256_file(bundle_path):
            raise UpdateError("authorized target digest does not match the bundle")
        if target.get("hardware") != SUPPORTED_HARDWARE:
            raise UpdateError("authorized target does not match supported hardware")
        release_version = verified.manifest["release"]["version"]
        if target.get("release_version") != release_version:
            raise UpdateError("authorized release version does not match the bundle")
        if target.get("backup_required") is not True or target.get("restart") is not True:
            raise UpdateError("target must require a checkpoint and restart")
        target_version = int(target.get("version", 0))
        metadata_version = int(authorization.get("channel_metadata_version", 0))
        state = self._state()
        existing_version = int(state.get("target_version", 0))
        existing_metadata_version = int(state.get("channel_metadata_version", 0))
        resumable = (
            target_version == existing_version
            and metadata_version == existing_metadata_version
            and state.get("status") == "interrupted"
            and state.get("authorized_bundle_sha256") == target.get("sha256")
        )
        if (
            target_version < existing_version
            or metadata_version < existing_metadata_version
            or (
                (target_version == existing_version or metadata_version == existing_metadata_version)
                and not resumable
            )
        ):
            raise UpdateError("target version is not newer than installed update state")
        return target

    def _verify_authorization_metadata(self, authorization: dict) -> None:
        try:
            root_envelope = json.loads(self.trusted_update_root.read_text(encoding="utf-8"))
            root = root_envelope["signed"]
            envelope = authorization["evidence"]["channel_metadata"]
            signed = envelope["signed"]
            role = root["roles"]["targets"]
            keys = root["keys"]
        except (KeyError, OSError, json.JSONDecodeError) as error:
            raise UpdateError("update authorization lacks trusted signed metadata evidence") from error
        if root.get("_type") != "root" or signed.get("_type") != "targets":
            raise UpdateError("update authorization metadata types are invalid")
        root_expires = datetime.fromisoformat(str(root["expires"]).replace("Z", "+00:00"))
        if root_expires <= datetime.now(timezone.utc):
            raise UpdateError("trusted update root is expired")
        if authorization.get("trusted_root_version") != int(root.get("version", 0)):
            raise UpdateError("update authorization uses the wrong trusted root version")
        expires = datetime.fromisoformat(str(signed["expires"]).replace("Z", "+00:00"))
        if expires <= datetime.now(timezone.utc):
            raise UpdateError("update authorization metadata is expired")
        payload = json.dumps(
            signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        accepted = set()
        for signature in envelope.get("signatures", []):
            keyid = signature.get("keyid")
            if keyid in accepted or keyid not in role["keyids"] or keyid not in keys:
                continue
            try:
                raw_public = base64.b64decode(keys[keyid]["public"], validate=True)
                raw_signature = base64.b64decode(signature["sig"], validate=True)
                if len(raw_public) != 32:
                    continue
                # RFC 8410 SubjectPublicKeyInfo prefix for an Ed25519 raw public key.
                public_der = bytes.fromhex("302a300506032b6570032100") + raw_public
                with (
                    tempfile.NamedTemporaryFile() as key_file,
                    tempfile.NamedTemporaryFile() as payload_file,
                    tempfile.NamedTemporaryFile() as signature_file,
                ):
                    key_file.write(public_der)
                    key_file.flush()
                    payload_file.write(payload)
                    payload_file.flush()
                    signature_file.write(raw_signature)
                    signature_file.flush()
                    subprocess.run(  # nosec B603
                        [
                            "openssl", "pkeyutl", "-verify", "-pubin",
                            "-inkey", key_file.name, "-keyform", "DER", "-rawin",
                            "-in", payload_file.name, "-sigfile", signature_file.name,
                        ],
                        check=True,
                        capture_output=True,
                    )
                accepted.add(keyid)
            except Exception:
                continue
        if len(accepted) < int(role["threshold"]):
            raise UpdateError("update authorization signature threshold not met")
        signed_target = signed["target"]
        custom = signed_target["custom"]
        expected = {
            "path": signed_target["path"],
            "version": int(signed_target["version"]),
            "release_version": str(custom["release_version"]),
            "length": int(signed_target["length"]),
            "sha256": signed_target["hashes"]["sha256"],
            "hardware": custom["hardware"],
            "restart": bool(custom.get("restart")),
            "backup_required": bool(custom.get("backup_required")),
        }
        if authorization.get("channel") != signed.get("channel"):
            raise UpdateError("authorization channel differs from signed metadata")
        if authorization.get("channel_metadata_version") != int(signed.get("version", 0)):
            raise UpdateError("authorization metadata version differs from signed metadata")
        if authorization.get("target") != expected:
            raise UpdateError("authorization target differs from signed metadata")

    def _checkpoint(self, transaction_id: str, previous: Path) -> tuple[Path, str]:
        checkpoint = self.checkpoints / transaction_id
        shutil.rmtree(checkpoint, ignore_errors=True)
        (checkpoint / "data").mkdir(parents=True)
        if self.data_dir.exists():
            shutil.copytree(self.data_dir, checkpoint / "data", dirs_exist_ok=True)
        data_sha256 = tree_digest(self.data_dir) if self.data_dir.exists() else tree_digest(
            checkpoint / "data"
        )
        if tree_digest(checkpoint / "data") != data_sha256:
            raise UpdateError("pre-update checkpoint verification failed")
        receipt_present = self.receipt.exists()
        if receipt_present:
            shutil.copy2(self.receipt, checkpoint / "install-receipt.json")
        metadata = {
            "schema_version": "unison.platform.update-checkpoint.v1",
            "previous_release": previous.name,
            "data_tree_sha256": data_sha256,
            "receipt_present": receipt_present,
            "verified": True,
        }
        (checkpoint / "checkpoint.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )
        return checkpoint, data_sha256

    def _restore(self, checkpoint: Path) -> str:
        metadata = json.loads((checkpoint / "checkpoint.json").read_text())
        if metadata.get("verified") is not True:
            raise UpdateError("rollback checkpoint is not verified")
        previous = self.releases / metadata["previous_release"]
        if not previous.is_dir():
            raise UpdateError("last-known-good release is unavailable")
        restored = self.data_dir.with_name(self.data_dir.name + ".rollback")
        shutil.rmtree(restored, ignore_errors=True)
        shutil.copytree(checkpoint / "data", restored)
        if tree_digest(restored) != metadata["data_tree_sha256"]:
            shutil.rmtree(restored, ignore_errors=True)
            raise UpdateError("rollback data failed checkpoint verification")
        displaced = self.data_dir.with_name(self.data_dir.name + ".failed-update")
        shutil.rmtree(displaced, ignore_errors=True)
        if self.data_dir.exists():
            os.replace(self.data_dir, displaced)
        os.replace(restored, self.data_dir)
        shutil.rmtree(displaced, ignore_errors=True)
        checkpoint_receipt = checkpoint / "install-receipt.json"
        if checkpoint_receipt.exists():
            shutil.copy2(checkpoint_receipt, self.receipt)
        else:
            self.receipt.unlink(missing_ok=True)
        self._activate(previous)
        return previous.name

    def apply(
        self,
        bundle_path: Path,
        authorization: dict,
        *,
        fail_at: str = "",
        migration: Callable[[Path], None] | None = None,
    ) -> dict:
        if not self.current.exists():
            raise UpdateError("an installed last-known-good release is required")
        if fail_at == "download":
            raise UpdateError("simulated download interruption")
        verified = verify_bundle(bundle_path, self.trusted_public_key)
        target = self._validate_authorization(bundle_path, verified, authorization)
        previous = self.current.resolve()
        version = verified.manifest["release"]["version"]
        transaction_id = hashlib.sha256(
            f"{previous.name}\0{version}\0{target['sha256']}".encode()
        ).hexdigest()[:24]
        required = bundle_path.stat().st_size + directory_size(self.data_dir) * 2
        if self.available_bytes(self.prefix) < required:
            existing = self._state()
            existing.pop("schema_version", None)
            self._write_state(**existing, last_rejection={
                "reason": "disk-full",
                "target_version": int(target["version"]),
                "version": version,
                "required_bytes": required,
            })
            raise UpdateError("insufficient disk space for bundle, checkpoint, and rollback")

        checkpoint, checkpoint_digest = self._checkpoint(transaction_id, previous)
        if fail_at == "after-checkpoint":
            self._write_state(
                status="interrupted",
                transaction_id=transaction_id,
                target_version=int(target["version"]),
                channel_metadata_version=int(authorization["channel_metadata_version"]),
                version=version,
                authorized_bundle_sha256=target["sha256"],
                checkpoint=str(checkpoint),
                active=previous.name,
            )
            raise UpdateError("simulated interruption after checkpoint")

        staging = self.releases / f".{version}.update-staging"
        target_release = self.releases / version
        shutil.rmtree(staging, ignore_errors=True)
        verified.materialize(staging)
        staged_digest = tree_digest(staging)
        receipt = verified.receipt(staged_digest)
        if fail_at == "after-stage":
            self._write_state(
                status="interrupted",
                transaction_id=transaction_id,
                target_version=int(target["version"]),
                channel_metadata_version=int(authorization["channel_metadata_version"]),
                version=version,
                authorized_bundle_sha256=target["sha256"],
                checkpoint=str(checkpoint),
                staged_tree_sha256=staged_digest,
                active=previous.name,
            )
            raise UpdateError("simulated interruption after staging")
        if target_release.exists():
            shutil.rmtree(target_release)
        os.replace(staging, target_release)
        self._write_state(
            status="activating",
            transaction_id=transaction_id,
            target_version=int(target["version"]),
            channel_metadata_version=int(authorization["channel_metadata_version"]),
            version=version,
            authorized_bundle_sha256=target["sha256"],
            previous=previous.name,
            checkpoint=str(checkpoint),
            checkpoint_data_sha256=checkpoint_digest,
            staged_tree_sha256=staged_digest,
        )
        try:
            self._activate(target_release)
            if migration:
                migration(self.data_dir)
            if fail_at == "after-activate":
                raise UpdateError("simulated interruption after activation")
            attempts = []
            healthy = False
            for attempt in range(1, self.health_attempts + 1):
                healthy = bool(self.health_check(attempt, version))
                attempts.append({"attempt": attempt, "healthy": healthy})
                if healthy:
                    break
            if not healthy:
                raise UpdateError("bounded health checks failed")
            temporary = self.receipt.with_suffix(".tmp")
            temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            os.replace(temporary, self.receipt)
            self._write_state(
                status="promoted",
                transaction_id=transaction_id,
                target_version=int(target["version"]),
                channel_metadata_version=int(authorization["channel_metadata_version"]),
                version=version,
                authorized_bundle_sha256=target["sha256"],
                previous=previous.name,
                checkpoint=str(checkpoint),
                checkpoint_data_sha256=checkpoint_digest,
                staged_tree_sha256=staged_digest,
                health_attempts=attempts,
            )
            return {"status": "promoted", "version": version, "previous": previous.name}
        except Exception as error:
            restored = self._restore(checkpoint)
            self._write_state(
                status="rolled-back",
                transaction_id=transaction_id,
                target_version=int(target["version"]),
                channel_metadata_version=int(authorization["channel_metadata_version"]),
                version=version,
                authorized_bundle_sha256=target["sha256"],
                previous=previous.name,
                checkpoint=str(checkpoint),
                restored=restored,
                reason=str(error),
                automatic=True,
            )
            raise UpdateError(f"update rolled back automatically: {error}") from error

    def rollback(self) -> dict:
        state = self._state()
        if state.get("status") != "promoted":
            raise UpdateError("no promoted update is available for explicit rollback")
        checkpoint = Path(state["checkpoint"])
        restored = self._restore(checkpoint)
        self._write_state(
            **{
                **state,
                "status": "rolled-back",
                "restored": restored,
                "reason": "explicit owner rollback",
                "automatic": False,
            }
        )
        return {"status": "rolled-back", "restored": restored}
