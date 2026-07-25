"""Source-governed security and improvement intelligence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Iterable

from .contracts import Evidence


VERSION_PART = re.compile(r"\d+")


def version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in VERSION_PART.findall(value))


def normalize_evidence(raw: dict, registry: dict) -> Evidence:
    source = next(
        (item for item in registry.get("sources", []) if item.get("source_id") == raw.get("source_id")),
        None,
    )
    if not source or not source.get("enabled"):
        raise ValueError("evidence source is not enabled")
    trust_tier = source["trust_tier"]
    if raw.get("trust_tier") != trust_tier:
        raise ValueError("source cannot promote its configured trust tier")
    signature_verified = bool(raw.get("signature_verified"))
    if trust_tier == "authoritative" and not signature_verified:
        raise ValueError("authoritative evidence requires a verified signature")
    payload = json.dumps(raw.get("payload", {}), sort_keys=True, separators=(",", ":")).encode()
    return Evidence(
        source_id=raw["source_id"],
        source_class=raw["source_class"],
        trust_tier=trust_tier,
        content_sha256=hashlib.sha256(payload).hexdigest(),
        affected_components=tuple(raw["payload"].get("affected_components", [])),
        claims=tuple(raw["payload"].get("claims", [])),
        severity=raw["payload"].get("severity", "none"),
        fixed_versions=tuple(raw["payload"].get("fixed_versions", [])),
        signature_verified=signature_verified,
        corroborating_evidence_ids=tuple(raw["payload"].get("corroborating_evidence_ids", [])),
        canonical_url=raw.get("canonical_url", ""),
    )


@dataclass(frozen=True)
class Exposure:
    component: dict[str, str]
    evidence_id: str
    severity: str
    fixed_versions: tuple[str, ...]
    fix_available: bool
    reason: str


class ExposureGraph:
    def __init__(self, components: Iterable[dict[str, str]]):
        self.components = tuple(components)

    def evaluate(self, evidence: Iterable[Evidence]) -> list[Exposure]:
        exposures: list[Exposure] = []
        for item in evidence:
            if item.trust_tier == "discovery-only":
                continue
            for affected in item.affected_components:
                for installed in self.components:
                    if (
                        affected.get("ecosystem") == installed.get("ecosystem")
                        and affected.get("name") == installed.get("name")
                    ):
                        introduced = affected.get("introduced", "0")
                        fixed = affected.get("fixed")
                        current = version_key(installed["version"])
                        vulnerable = current >= version_key(introduced)
                        if fixed:
                            vulnerable = vulnerable and current < version_key(fixed)
                        if vulnerable:
                            exposures.append(
                                Exposure(
                                    component=installed,
                                    evidence_id=item.evidence_id,
                                    severity=item.severity,
                                    fixed_versions=item.fixed_versions or ((fixed,) if fixed else ()),
                                    fix_available=bool(item.fixed_versions or fixed),
                                    reason=f"{installed['name']} {installed['version']} matches affected range",
                                )
                            )
        return sorted(exposures, key=lambda value: (value.component["name"], value.evidence_id))
