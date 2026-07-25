"""Signed-registry, read-only scheduled intelligence collection."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess  # nosec B404: OpenSSL verifies the pinned Ed25519 registry key.
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .state import MaintenanceState


def verify_signed_registry(envelope: dict, public_key: Path) -> dict:
    payload = json.dumps(
        envelope["signed"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    signature = base64.b64decode(envelope["signature"], validate=True)
    with tempfile.NamedTemporaryFile() as payload_file, tempfile.NamedTemporaryFile() as sig_file:
        payload_file.write(payload)
        payload_file.flush()
        sig_file.write(signature)
        sig_file.flush()
        result = subprocess.run(  # nosec B603
            [
                "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
                "-rawin", "-in", payload_file.name, "-sigfile", sig_file.name,
            ],
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        raise ValueError("source registry signature is invalid")
    return envelope["signed"]


@dataclass(frozen=True)
class FeedResult:
    source_id: str
    retrieved_at: str
    content_sha256: str
    byte_count: int
    trust_tier: str
    status: str
    snapshot_path: str


class ScheduledFeedCollector:
    def __init__(
        self,
        registry: dict,
        state: MaintenanceState,
        *,
        maximum_bytes: int = 5_000_000,
        snapshot_dir: Path | None = None,
        opener=urllib.request.urlopen,
    ) -> None:
        self.registry = registry
        self.state = state
        self.maximum_bytes = maximum_bytes
        self.snapshot_dir = snapshot_dir or state.path.parent / "intelligence"
        self.opener = opener

    def due(self, source: dict, *, at: datetime) -> bool:
        prior = [
            item for item in self.state.read().get("source_runs", [])
            if item["source_id"] == source["source_id"] and item["status"] == "collected"
        ]
        if not prior:
            return True
        latest = datetime.fromisoformat(prior[-1]["retrieved_at"].replace("Z", "+00:00"))
        return (at - latest).total_seconds() >= int(source["interval_seconds"])

    def collect(self, source: dict, *, at: datetime) -> FeedResult:
        if not source.get("enabled"):
            raise ValueError("source is disabled")
        url = source["url"]
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in source["allowed_hosts"]:
            raise ValueError("feed URL is outside the signed registry boundary")
        request = urllib.request.Request(
            url, headers={"User-Agent": "UnisonOS-maintenance/1", "Accept": "application/json"}
        )
        with self.opener(request, timeout=10) as response:
            final = urlparse(response.geturl())
            if final.scheme != "https" or final.hostname not in source["allowed_hosts"]:
                raise ValueError("feed redirected outside the signed registry boundary")
            source_limit = min(int(source.get("maximum_bytes", self.maximum_bytes)), self.maximum_bytes)
            content = response.read(source_limit + 1)
        if len(content) > source_limit:
            raise ValueError("feed exceeded the signed collector size limit")
        if source.get("parser") == "json":
            json.loads(content)
        stamp = at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        content_sha256 = hashlib.sha256(content).hexdigest()
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshot_dir / f"{source['source_id']}-{content_sha256}.json"
        if not snapshot.exists():
            snapshot.write_bytes(content)
            snapshot.chmod(0o600)
        result = FeedResult(
            source_id=source["source_id"],
            retrieved_at=stamp,
            content_sha256=content_sha256,
            byte_count=len(content),
            trust_tier=source["trust_tier"],
            status="collected",
            snapshot_path=str(snapshot),
        )
        self.state.append("source_runs", result.__dict__)
        return result

    def run_due(self, *, at: datetime | None = None) -> list[FeedResult]:
        stamp = at or datetime.now(timezone.utc)
        return [
            self.collect(source, at=stamp)
            for source in self.registry.get("sources", [])
            if self.due(source, at=stamp)
        ]
