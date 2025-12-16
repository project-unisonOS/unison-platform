#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/common.sh"

require_root
require_docker

echo "Installing Unison Platform (Docker) into ${PREFIX}"
cd "${ROOT_DIR}"
copy_bundle
seed_env
write_systemd_unit
pull_images
start_stack

if [ -x "${PREFIX}/installer/ensure-models.sh" ]; then
  "${PREFIX}/installer/ensure-models.sh" || true
fi

echo "Installation complete. Edit ${ENV_FILE} for secrets and rerun: systemctl restart unison-platform"
