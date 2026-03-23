#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
WORKSPACE_ROOT=$(cd -- "${REPO_ROOT}/.." && pwd)

COMMON_REPO="${WORKSPACE_ROOT}/unison-common"
PLATFORM_REPO="${WORKSPACE_ROOT}/unison-platform"

if [[ ! -d "${COMMON_REPO}" ]]; then
    echo "[local-build] missing repo: ${COMMON_REPO}" >&2
    exit 1
fi

if [[ ! -f "${COMMON_REPO}/Dockerfile.wheel" ]]; then
    echo "[local-build] missing wheel Dockerfile: ${COMMON_REPO}/Dockerfile.wheel" >&2
    exit 1
fi

echo "[local-build] building unison-common wheel image"
docker build \
    -f "${COMMON_REPO}/Dockerfile.wheel" \
    -t ghcr.io/project-unisonos/unison-common-wheel:latest \
    "${COMMON_REPO}"

echo "[local-build] building auth, orchestrator, renderer, agent-vdi, and updates from workspace source"
docker compose \
    --env-file "${PLATFORM_REPO}/.env" \
    -f "${PLATFORM_REPO}/compose/compose.yaml" \
    -f "${PLATFORM_REPO}/compose/compose.local-source.yaml" \
    build auth orchestrator experience-renderer agent-vdi updates
