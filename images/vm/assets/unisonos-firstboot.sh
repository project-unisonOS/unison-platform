#!/usr/bin/env bash
set -euo pipefail

STAMP="/var/lib/unisonos/firstboot.done"
mkdir -p "$(dirname "${STAMP}")"
if [ -f "${STAMP}" ]; then
  exit 0
fi

export DEBIAN_FRONTEND=noninteractive

ensure_pkg() {
  local pkg="$1"
  dpkg -s "${pkg}" >/dev/null 2>&1 && return 0
  apt-get update
  apt-get install -y "${pkg}"
}

ensure_pkg ca-certificates
ensure_pkg curl

if ! command -v docker >/dev/null 2>&1; then
  ensure_pkg docker.io
fi
if ! docker compose version >/dev/null 2>&1; then
  ensure_pkg docker-compose-v2
fi

systemctl enable --now docker

PREFIX="/opt/unison-platform"
ENV_FILE="/etc/unison/platform.env"
SYSTEMD_UNIT="/etc/systemd/system/unison-platform.service"
COMPOSE_FILE="${PREFIX}/docker-compose.yml"

mkdir -p "$(dirname "${ENV_FILE}")"
if [ ! -f "${ENV_FILE}" ] && [ -f "${PREFIX}/.env.template" ]; then
  cp "${PREFIX}/.env.template" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}" || true
fi

cat > "${SYSTEMD_UNIT}" <<UNIT
[Unit]
Description=Unison Platform (Docker Compose)
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${PREFIX}
EnvironmentFile=${ENV_FILE}
ExecStart=/usr/bin/docker compose -f ${COMPOSE_FILE} up -d --remove-orphans
ExecStop=/usr/bin/docker compose -f ${COMPOSE_FILE} down
TimeoutStartSec=300
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable unison-platform.service

(
  cd "${PREFIX}"
  docker compose -f docker-compose.yml pull || true
)
systemctl start unison-platform.service

if [ -x "${PREFIX}/installer/ensure-models.sh" ]; then
  "${PREFIX}/installer/ensure-models.sh" || true
fi

touch "${STAMP}"

