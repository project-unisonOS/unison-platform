#!/usr/bin/env python3
"""Static gate for the digest-pinned supported Compose profile."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose/compose.supported.yaml"
EXAMPLE = ROOT / "releases/supported-images.example.env"
REQUIRED = {
    "redis", "postgres", "nats", "auth", "context", "policy",
    "orchestrator", "intent-graph", "context-graph",
    "experience-renderer", "io-speech", "inference", "storage",
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    source = COMPOSE.read_text(encoding="utf-8")
    if re.search(r"^include:", source, re.MULTILINE):
        fail("supported profile must be a Compose override, not a conflicting include")
    if "latest" in source or "UNISON_IMAGE_TAG" in source:
        fail("supported profile contains a mutable image selector")
    services = set(re.findall(r"^  ([a-z0-9-]+):$", source, re.MULTILINE))
    if services != REQUIRED:
        fail(f"supported service set drift: {sorted(services ^ REQUIRED)}")
    variables = set(re.findall(r"\$\{(UNISON_[A-Z_]+_IMAGE):\?", source))
    values = {}
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    if variables != set(values):
        fail("supported image variable contract drift")
    digest = re.compile(r"^[^\s:@]+(?::[^\s@]+)?@sha256:[0-9a-f]{64}$")
    for key, value in values.items():
        if not digest.fullmatch(value):
            fail(f"{key} is not a digest reference")
    for internal in REQUIRED - {"orchestrator", "experience-renderer"}:
        match = re.search(
            rf"^  {re.escape(internal)}:\n(.*?)(?=^  [a-z0-9-]+:|\Z)",
            source,
            re.MULTILINE | re.DOTALL,
        )
        block = match.group(1) if match else ""
        if "ports: !reset []" not in block:
            fail(f"{internal} does not reset developer host ports")
    if source.count('"127.0.0.1:') != 2:
        fail("supported profile must expose exactly two loopback surfaces")
    registry_contract = (
        'UNISON_REQUIRE_GOVERNED_REGISTRY: "true"',
        "UNISON_MODEL_REGISTRY_MANIFESTS_DIR: /etc/unison/model-registry/manifests",
        "UNISON_MODEL_REGISTRY_TRUSTED_KEYS_DIR: /etc/unison/model-registry/keys",
        "UNISON_MODEL_REGISTRY_INVENTORY_FILE: /etc/unison/model-registry/inventory.json",
        "${UNISON_MODEL_REGISTRY_DIR:?signed model registry directory required}:/etc/unison/model-registry:ro",
        "${UNISON_MODEL_ARTIFACTS_DIR:?verified model artifact directory required}:/var/lib/unison/models:ro",
        'UNISON_REQUIRE_PERSISTENT_MODEL_LIFECYCLE: "true"',
        "UNISON_MODEL_LIFECYCLE_STATE_FILE: /var/lib/unison/model-lifecycle/state.json",
        "UNISON_MODEL_ROLLBACK_ARTIFACTS_DIR: /var/lib/unison/model-lifecycle/rollback-artifacts",
        "${UNISON_MODEL_LIFECYCLE_DIR:?persistent model lifecycle directory required}:/var/lib/unison/model-lifecycle",
    )
    missing = [value for value in registry_contract if value not in source]
    if missing:
        fail(f"supported inference registry boundary drift: {missing}")
    print("[PASS] Supported runtime has 13 digest-required services and two loopback-only surfaces.")


if __name__ == "__main__":
    main()
