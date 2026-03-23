#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
ENV_FILE="${REPO_ROOT}/.env"

load_env_value() {
    local key="$1"
    local default_value="$2"
    if [[ ! -f "${ENV_FILE}" ]]; then
        printf '%s' "${default_value}"
        return
    fi

    local line
    line=$(awk -F= -v target="${key}" '
        $0 !~ /^[[:space:]]*#/ && $1 == target {
            sub(/^[[:space:]]+/, "", $2)
            sub(/[[:space:]]+$/, "", $2)
            print $2
            exit
        }
    ' "${ENV_FILE}" || true)

    if [[ -n "${line}" ]]; then
        printf '%s' "${line}"
    else
        printf '%s' "${default_value}"
    fi
}

ORCHESTRATOR_PORT=$(load_env_value "ORCHESTRATOR_PORT" "8090")
RENDERER_PORT=$(load_env_value "EXPERIENCE_RENDERER_HOST_PORT" "8092")
AUTH_PORT=$(load_env_value "AUTH_HOST_PORT" "8083")
INFERENCE_PORT=$(load_env_value "INFERENCE_HOST_PORT" "8087")
CONTEXT_PORT=$(load_env_value "CONTEXT_HOST_PORT" "8081")
AGENT_VDI_PORT=$(load_env_value "AGENT_VDI_HOST_PORT" "8093")
STORAGE_PORT=$(load_env_value "STORAGE_HOST_PORT" "8082")

MILESTONE1_USERNAME="${MILESTONE1_ACCEPTANCE_USERNAME:-}"
MILESTONE1_PASSWORD="${MILESTONE1_ACCEPTANCE_PASSWORD:-}"
MILESTONE1_PERSON_ID="${MILESTONE1_ACCEPTANCE_PERSON_ID:-local-person}"

wait_http_ok() {
    local url="$1"
    local timeout="${2:-30}"
    local start
    start=$(date +%s)
    while true; do
        if curl -fsS "${url}" >/dev/null 2>&1; then
            return 0
        fi
        if (( $(date +%s) - start >= timeout )); then
            echo "[recovery] FAIL: ${url} did not become ready within ${timeout}s" >&2
            return 1
        fi
        sleep 1
    done
}

echo "[recovery] verifying pre-restart health"
wait_http_ok "http://127.0.0.1:${ORCHESTRATOR_PORT}/health" 20
wait_http_ok "http://127.0.0.1:${RENDERER_PORT}/health" 20
wait_http_ok "http://127.0.0.1:${AUTH_PORT}/health" 20
wait_http_ok "http://127.0.0.1:${INFERENCE_PORT}/ready" 20

echo "[recovery] restarting orchestrator via compose"
docker compose --env-file "${ENV_FILE}" -f "${REPO_ROOT}/compose/compose.yaml" restart orchestrator >/dev/null

echo "[recovery] waiting for stack reconvergence"
wait_http_ok "http://127.0.0.1:${ORCHESTRATOR_PORT}/health" 45
wait_http_ok "http://127.0.0.1:${RENDERER_PORT}/health" 45
wait_http_ok "http://127.0.0.1:${AUTH_PORT}/health" 45
wait_http_ok "http://127.0.0.1:${INFERENCE_PORT}/ready" 45
wait_http_ok "http://127.0.0.1:${ORCHESTRATOR_PORT}/startup/status" 45
wait_http_ok "http://127.0.0.1:${RENDERER_PORT}/onboarding-status" 45

echo "[recovery] validating golden path after restart"
"${REPO_ROOT}/scripts/validate-golden-path.sh" >/dev/null

if [[ -n "${MILESTONE1_USERNAME}" && -n "${MILESTONE1_PASSWORD}" ]]; then
    echo "[recovery] validating briefing and VDI flows after restart"
    RUN_NATIVE_INSTALL_ACCEPTANCE=1 \
    ORCHESTRATOR_BASE_URL="http://localhost:${ORCHESTRATOR_PORT}" \
    RENDERER_BASE_URL="http://localhost:${RENDERER_PORT}" \
    AUTH_BASE_URL="http://localhost:${AUTH_PORT}" \
    CONTEXT_BASE_URL="http://localhost:${CONTEXT_PORT}" \
    AGENT_VDI_BASE_URL="http://localhost:${AGENT_VDI_PORT}" \
    STORAGE_BASE_URL="http://localhost:${STORAGE_PORT}" \
    MILESTONE1_ACCEPTANCE_USERNAME="${MILESTONE1_USERNAME}" \
    MILESTONE1_ACCEPTANCE_PASSWORD="${MILESTONE1_PASSWORD}" \
    MILESTONE1_ACCEPTANCE_PERSON_ID="${MILESTONE1_PERSON_ID}" \
    "${REPO_ROOT}/.venv/bin/python" -m pytest "${REPO_ROOT}/qa/test_native_install_acceptance.py" \
        -k 'briefing or vdi' -q >/dev/null
else
    echo "[recovery] WARN: skipping post-restart briefing/VDI acceptance; set MILESTONE1_ACCEPTANCE_USERNAME and MILESTONE1_ACCEPTANCE_PASSWORD to enable it"
fi

echo "[recovery] PASS: orchestrator restart reconverged and post-restart validation passed"
