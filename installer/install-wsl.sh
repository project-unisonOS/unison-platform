#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/common.sh"

require_root

detect_wsl() {
  if ! grep -qi microsoft /proc/version; then
    echo "This installer is intended for WSL (Windows Subsystem for Linux)." >&2
    exit 1
  fi
}

install_prereqs() {
  if ! command -v docker >/dev/null 2>&1; then
    apt-get update
    apt-get install -y docker.io docker-compose git
    # In WSL, dockerd may be managed externally; start if available
    if command -v systemctl >/dev/null 2>&1; then
      systemctl enable --now docker || true
    fi
  fi
}

detect_wsl
install_prereqs
require_docker

echo "Installing Unison Platform for WSL into ${PREFIX}"
cd "${ROOT_DIR}"
copy_bundle
seed_env
pull_images

# WSL may not support systemd; start directly
if command -v systemctl >/dev/null 2>&1; then
  write_systemd_unit
fi
start_stack

echo "Installation complete. Edit ${ENV_FILE} for secrets. Restart with docker compose -f ${PREFIX}/docker-compose.yml up -d (or systemctl if available)."
