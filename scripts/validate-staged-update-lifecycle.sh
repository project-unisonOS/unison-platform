#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
STAGE_PREFIX="${STAGE_PREFIX:-/tmp/unison-stage-lifecycle}"
UPDATES_BASE_URL="${UPDATES_BASE_URL:-http://127.0.0.1:8094}"

rm -rf "${STAGE_PREFIX}"

job_payload=$(
python3 - <<'PY'
import json
import urllib.request

base = "http://127.0.0.1:8094/v1/tools"
headers = {"Content-Type": "application/json"}

def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())

plan = post("/updates.plan", {"arguments": {"selection": {"platform_version": "local-dev"}, "constraints": {"approved": True}}})
job = post("/updates.apply", {"arguments": {"plan_id": plan["plan_id"]}})
print(json.dumps(job))
PY
)

artifact_path=$(printf '%s' "${job_payload}" | python3 -c 'import json,sys; print((json.load(sys.stdin)["result"]["artifacts"]["apply_override"]["path"]))')
job_id=$(printf '%s' "${job_payload}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')

echo "[staged-update] validating emitted apply artifact"
python3 "${REPO_ROOT}/scripts/validate-update-artifact.py" --artifact "${artifact_path}" --manifest "${REPO_ROOT}/releases/local-dev-manifest.json"

echo "[staged-update] installing staged override into ${STAGE_PREFIX}"
sg docker -c "cd '${REPO_ROOT}' && python3 scripts/install-staged-update.py --artifact '${artifact_path}' --prefix '${STAGE_PREFIX}'" >/dev/null

test -f "${STAGE_PREFIX}/staged/compose.next-boot.override.yaml"
test -f "${STAGE_PREFIX}/staged/compose.next-boot.metadata.json"

echo "[staged-update] finalizing staged override"
python3 "${REPO_ROOT}/scripts/finalize-staged-update.py" --prefix "${STAGE_PREFIX}" --updates-base-url "${UPDATES_BASE_URL}" >/tmp/unison-staged-finalize.json

test ! -f "${STAGE_PREFIX}/staged/compose.next-boot.override.yaml"
test ! -f "${STAGE_PREFIX}/staged/compose.next-boot.metadata.json"

python3 - <<'PY'
import json
import sys
from pathlib import Path

stage_prefix = Path("/tmp/unison-stage-lifecycle")
archive_dir = stage_prefix / "staged" / "archive"
if not archive_dir.exists():
    raise SystemExit("archive directory missing")
files = sorted(p.name for p in archive_dir.iterdir() if p.is_file())
if len(files) < 2:
    raise SystemExit(f"archive files missing: {files}")
print(json.dumps({"archived_files": files}, indent=2))
PY

status_payload=$(
python3 - <<PY
import json
import urllib.request

base = "${UPDATES_BASE_URL}/v1/tools"
headers = {"Content-Type": "application/json"}
job_id = "${job_id}"

def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())

status = post("/updates.status", {"arguments": {"job_id": job_id}})
rollback = post("/updates.rollback", {"arguments": {}})
print(json.dumps({"status": status, "rollback": rollback}))
PY
)

printf '%s' "${status_payload}" | python3 -c '
import json
import sys

payload = json.load(sys.stdin)
status = payload["status"]
rollback = payload["rollback"]

if status.get("status") != "applied":
    raise SystemExit("job not applied: %s" % status.get("status"))
if (status.get("result") or {}).get("applied") is not True:
    raise SystemExit("job result.applied is not true")
target = rollback.get("target") or {}
if target.get("platform_version") != "local-dev":
    raise SystemExit("last_known_good mismatch: %s" % target.get("platform_version"))

print(json.dumps({
    "ok": True,
    "job_id": status.get("job_id"),
    "status": status.get("status"),
    "last_known_good": target.get("platform_version"),
}, indent=2))
'

echo "[staged-update] PASS: stage -> finalize -> applied-state flow validated"
