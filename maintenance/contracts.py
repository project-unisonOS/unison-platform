"""Canonical in-process records for adaptive maintenance.

The JSON interchange authority lives in unison-common's
adaptive-maintenance.v1.schema.json. These dataclasses keep the platform
implementation dependency-free.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:16]}"


def asdict(value: object) -> dict[str, Any]:
    return dataclasses.asdict(value)


@dataclass(frozen=True)
class HealthObservation:
    metric: str
    component: str
    value: float
    unit: str
    severity: str
    window_start: str
    window_end: str
    aggregation: str = "instant"
    confidence: float = 1.0
    collection_method: str = "local"
    retention_class: str = "operational"
    contains_personal_content: bool = False
    observation_id: str = ""

    def __post_init__(self) -> None:
        if self.contains_personal_content:
            raise ValueError("operational observations cannot contain personal content")
        if self.severity not in {"healthy", "notice", "warning", "critical"}:
            raise ValueError("unsupported observation severity")
        if not self.observation_id:
            object.__setattr__(
                self,
                "observation_id",
                stable_id("obs", [self.metric, self.component, self.window_end, self.value]),
            )


@dataclass(frozen=True)
class Evidence:
    source_id: str
    source_class: str
    trust_tier: str
    content_sha256: str
    affected_components: tuple[dict[str, str], ...]
    claims: tuple[str, ...]
    severity: str = "none"
    fixed_versions: tuple[str, ...] = ()
    signature_verified: bool = False
    corroborating_evidence_ids: tuple[str, ...] = ()
    canonical_url: str = ""
    retrieved_at: str = field(default_factory=now)
    untrusted_content: bool = True
    evidence_id: str = ""

    def __post_init__(self) -> None:
        if not self.untrusted_content:
            raise ValueError("external evidence must remain marked untrusted")
        if self.trust_tier == "authoritative" and not self.signature_verified:
            raise ValueError("authoritative evidence must be signature verified")
        if not self.evidence_id:
            object.__setattr__(
                self,
                "evidence_id",
                stable_id("evidence", [self.source_id, self.content_sha256]),
            )


@dataclass(frozen=True)
class Recommendation:
    candidate_id: str
    title: str
    rationale: tuple[str, ...]
    alternatives: tuple[str, ...]
    expected_effects: dict[str, Any]
    risk: str
    authority: str
    requires_confirmation: bool
    rollback: dict[str, Any]
    rank: float
    confidence: float
    recommendation_id: str = ""

    def __post_init__(self) -> None:
        if self.authority not in {"observe", "recommend", "prepare", "maintain", "emergency-protect"}:
            raise ValueError("unsupported autonomy level")
        if not self.recommendation_id:
            object.__setattr__(
                self,
                "recommendation_id",
                stable_id("recommendation", [self.candidate_id, self.title]),
            )
