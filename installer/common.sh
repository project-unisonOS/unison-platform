#!/usr/bin/env bash
set -euo pipefail

PREFIX=${PREFIX:-/opt/unison-platform}
ENV_FILE=${ENV_FILE:-/etc/unison/platform.env}
SYSTEMD_UNIT=${SYSTEMD_UNIT:-/etc/systemd/system/unison-platform.service}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}

require_root() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "This installer must be run as root (or via sudo)." >&2
    exit 1
  fi
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed. Please install Docker/Compose and re-run." >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not running or not accessible." >&2
    exit 1
  fi
}

copy_bundle() {
  mkdir -p "${PREFIX}"
  cp "${COMPOSE_FILE}" "${PREFIX}/docker-compose.yml"
  cp -r config "${PREFIX}/config"
  cp -r compose "${PREFIX}/compose"
  mkdir -p "${PREFIX}/scripts"
  if [ -f "./scripts/health-check.sh" ]; then
    cp ./scripts/health-check.sh "${PREFIX}/scripts/"
  fi
}

seed_env() {
  mkdir -p "$(dirname "${ENV_FILE}")"
  if [ ! -f "${ENV_FILE}" ]; then
    cp .env.template "${ENV_FILE}"
    chmod 600 "${ENV_FILE}"
    echo "Seeded ${ENV_FILE} from .env.template. Update secrets before starting." >&2
  fi
}

write_systemd_unit() {
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
ExecStart=/usr/bin/docker compose -f ${PREFIX}/docker-compose.yml up -d --remove-orphans
ExecStop=/usr/bin/docker compose -f ${PREFIX}/docker-compose.yml down
TimeoutStartSec=300
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable unison-platform.service
}

start_stack() {
  if command -v systemctl >/dev/null 2>&1; then
    systemctl start unison-platform.service
  else
    (cd "${PREFIX}" && docker compose -f docker-compose.yml up -d --remove-orphans)
  fi
}

pull_images() {
  (cd "${PREFIX}" && docker compose -f docker-compose.yml pull || true)
}
