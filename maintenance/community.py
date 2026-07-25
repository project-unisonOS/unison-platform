"""Sandbox boundary and corroboration for discovery-only community claims."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .contracts import stable_id


COMMAND_PATTERN = re.compile(r"(sudo\s|curl.+\|\s*(sh|bash)|ignore previous|system prompt)", re.I)


@dataclass(frozen=True)
class CommunityClaim:
    claim_id: str
    source_id: str
    canonical_url: str
    subject: str
    statement: str
    content_sha256: str
    corroborating_sources: tuple[str, ...]
    conflicts: tuple[str, ...]
    trust_tier: str = "discovery-only"
    executable: bool = False


class SandboxedCollector:
    def __init__(self, registry: dict, *, maximum_bytes: int = 256_000) -> None:
        self.registry = registry
        self.maximum_bytes = maximum_bytes

    def collect(self, raw: dict) -> CommunityClaim:
        source = next(
            (item for item in self.registry.get("sources", []) if item["source_id"] == raw.get("source_id")),
            None,
        )
        if not source or not source.get("enabled") or source.get("trust_tier") != "discovery-only":
            raise ValueError("community source is not enabled for discovery")
        host = urlparse(raw.get("canonical_url", "")).hostname
        if host not in source.get("allowed_hosts", []):
            raise ValueError("source URL is outside the registry allowlist")
        payload = raw.get("content", "").encode()
        if len(payload) > self.maximum_bytes:
            raise ValueError("community payload exceeds the sandbox limit")
        if COMMAND_PATTERN.search(raw.get("content", "")):
            raise ValueError("instruction-like community content was rejected")
        statement = " ".join(raw.get("statement", "").split())
        if not statement:
            raise ValueError("a normalized claim is required")
        return CommunityClaim(
            claim_id=stable_id("claim", [raw["source_id"], raw["canonical_url"], statement]),
            source_id=raw["source_id"],
            canonical_url=raw["canonical_url"],
            subject=raw.get("subject", "unspecified"),
            statement=statement,
            content_sha256=hashlib.sha256(payload).hexdigest(),
            corroborating_sources=tuple(sorted(set(raw.get("corroborating_sources", [])))),
            conflicts=tuple(sorted(set(raw.get("conflicts", [])))),
        )


def cluster_claims(claims: list[CommunityClaim]) -> list[dict]:
    groups: dict[tuple[str, str], list[CommunityClaim]] = {}
    for claim in claims:
        groups.setdefault((claim.subject.casefold(), claim.statement.casefold()), []).append(claim)
    return [
        {
            "cluster_id": stable_id("cluster", key),
            "subject": values[0].subject,
            "statement": values[0].statement,
            "source_count": len({item.source_id for item in values}),
            "conflicts": sorted({value for item in values for value in item.conflicts}),
            "eligible_for_local_test": len({item.source_id for item in values}) >= 2
            and not any(item.conflicts for item in values),
            "authority": "test-proposal-only",
            "claims": [json.loads(json.dumps(item.__dict__)) for item in values],
        }
        for key, values in sorted(groups.items())
    ]
