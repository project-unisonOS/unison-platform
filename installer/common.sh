#!/usr/bin/env bash
set -euo pipefail

PREFIX=${PREFIX:-/opt/unison-platform}
ENV_FILE=${ENV_FILE:-/etc/unison/platform.env}
SYSTEMD_UNIT=${SYSTEMD_UNIT:-/etc/systemd/system/unison-platform.service}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
UNISON_AUTO_START=${UNISON_AUTO_START:-0}
UNISON_SKIP_START=${UNISON_SKIP_START:-0}

readonly UNSAFE_ENV_MARKERS=(
  "UNISON_ENV=development"
  "POSTGRES_PASSWORD=unison_password"
  "JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production"
)

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
  if [ -d "./model-packs" ]; then
    cp -r model-packs "${PREFIX}/model-packs"
  fi
  if [ -d "./installer" ]; then
    cp -r installer "${PREFIX}/installer"
  fi
  mkdir -p "${PREFIX}/scripts"
  if [ -f "./scripts/health-check.sh" ]; then
    cp ./scripts/health-check.sh "${PREFIX}/scripts/"
  fi
}

install_control_cli() {
  if [ -f "./installer/unisonctl.sh" ]; then
    install -m 0755 "./installer/unisonctl.sh" /usr/local/bin/unisonctl
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

env_contains_unsafe_defaults() {
  local marker
  for marker in "${UNSAFE_ENV_MARKERS[@]}"; do
    if grep -Fqx "${marker}" "${ENV_FILE}"; then
      return 0
    fi
  done
  return 1
}

print_manual_start_instructions() {
  local start_cmd="systemctl start unison-platform.service"
  local status_cmd="systemctl status unison-platform.service"

  if ! command -v systemctl >/dev/null 2>&1; then
    start_cmd="docker compose -f ${PREFIX}/docker-compose.yml up -d --remove-orphans"
    status_cmd="docker compose -f ${PREFIX}/docker-compose.yml ps"
  fi

  cat >&2 <<EOF
Unison Platform is installed but not started yet.

Before first start:
  1. Edit ${ENV_FILE}
  2. Set production-safe values for:
     - UNISON_ENV
     - POSTGRES_PASSWORD
     - JWT_SECRET_KEY

After updating the environment:
  ${start_cmd}
  ${status_cmd}
EOF
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

maybe_start_stack() {
  if [ "${UNISON_SKIP_START}" = "1" ]; then
    echo "Skipping first start because UNISON_SKIP_START=1." >&2
    print_manual_start_instructions
    return 0
  fi

  if env_contains_unsafe_defaults; then
    echo "Refusing first start because ${ENV_FILE} still contains template or development defaults." >&2
    print_manual_start_instructions
    return 0
  fi

  if [ "${UNISON_AUTO_START}" != "1" ]; then
    echo "Installation completed without auto-start. Set UNISON_AUTO_START=1 to opt in." >&2
    print_manual_start_instructions
    return 0
  fi

  start_stack
}

pull_images() {
  (cd "${PREFIX}" && docker compose -f docker-compose.yml pull || true)
}
