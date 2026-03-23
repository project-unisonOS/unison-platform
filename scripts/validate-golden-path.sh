#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)

REPO_ROOT="${REPO_ROOT}" python3 - <<'PY'
import json
import os
import sys
import urllib.request
from pathlib import Path


def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as resp:
        if resp.status != 200:
            raise SystemExit(f"[golden-path] {url} returned HTTP {resp.status}")
        return json.loads(resp.read().decode("utf-8"))


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


env = load_env(Path(os.environ["REPO_ROOT"]) / ".env")

inference_port = env.get("INFERENCE_HOST_PORT", "8087")
auth_port = env.get("AUTH_HOST_PORT", "8083")
orchestrator_port = env.get("ORCHESTRATOR_HOST_PORT", "8090")
renderer_port = env.get("EXPERIENCE_RENDERER_HOST_PORT", "8092")
expected_model = env.get("UNISON_INFERENCE_MODEL", "qwen2.5:1.5b")

checks = {
    "inference": fetch(f"http://127.0.0.1:{inference_port}/ready"),
    "bootstrap": fetch(f"http://127.0.0.1:{auth_port}/bootstrap/status"),
    "startup": fetch(f"http://127.0.0.1:{orchestrator_port}/startup/status"),
    "onboarding": fetch(f"http://127.0.0.1:{renderer_port}/onboarding-status"),
}

failures: list[str] = []

inference = checks["inference"]
if inference.get("ready") is not True:
    failures.append("inference is not ready")
provider = inference.get("provider") or {}
if provider.get("model") != expected_model:
    failures.append(f"inference model mismatch: expected {expected_model}, got {provider.get('model')}")

bootstrap = checks["bootstrap"]
if bootstrap.get("enabled") is not True:
    failures.append("auth bootstrap is not enabled")
if bootstrap.get("admin_exists") is not True:
    failures.append("no admin user exists")
if bootstrap.get("bootstrap_required") is not False:
    failures.append("bootstrap is still required")

startup = checks["startup"]
if startup.get("ok") is not True:
    failures.append("startup status is not ok")
if startup.get("state") != "READY_LISTENING":
    failures.append(f"startup state mismatch: expected READY_LISTENING, got {startup.get('state')}")

onboarding = checks["onboarding"]
if onboarding.get("ready_to_finish") is not True:
    failures.append("onboarding is not ready to finish")
if onboarding.get("blocked_steps"):
    failures.append(f"onboarding still has blocked steps: {onboarding.get('blocked_steps')}")

if failures:
    for failure in failures:
        print(f"[golden-path] FAIL: {failure}", file=sys.stderr)
    sys.exit(1)

print(json.dumps(checks, indent=2))
PY
