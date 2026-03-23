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

echo "[recovery] PASS: orchestrator restart reconverged and golden-path checks still pass"
