#!/usr/bin/env bash
set -euo pipefail

PREFIX=${PREFIX:-/opt/unison-platform}
COMPOSE_FILE=${COMPOSE_FILE:-${PREFIX}/docker-compose.yml}
ENV_FILE=${ENV_FILE:-/etc/unison/platform.env}
SYSTEMD_UNIT=${SYSTEMD_UNIT:-unison-platform.service}
TAIL_LINES=${TAIL_LINES:-150}

readonly RED=$'\033[0;31m'
readonly GREEN=$'\033[0;32m'
readonly YELLOW=$'\033[1;33m'
readonly BLUE=$'\033[0;34m'
readonly NC=$'\033[0m'

readonly UNSAFE_ENV_MARKERS=(
  "UNISON_ENV=development"
  "POSTGRES_PASSWORD=unison_password"
  "JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production"
)

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_ok() { echo -e "${GREEN}[OK]${NC} $*"; }

require_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    log_error "This command requires sudo/root."
    exit 1
  fi
}

require_compose_bundle() {
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    log_error "Compose bundle not found at ${COMPOSE_FILE}"
    exit 1
  fi
}

has_systemd() {
  command -v systemctl >/dev/null 2>&1
}

compose_cmd() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

env_contains_unsafe_defaults() {
  [[ -f "${ENV_FILE}" ]] || return 1
  local marker
  for marker in "${UNSAFE_ENV_MARKERS[@]}"; do
    if grep -Fqx "${marker}" "${ENV_FILE}"; then
      return 0
    fi
  done
  return 1
}

print_status_summary() {
  echo
  echo "UnisonOS Milestone 1 Status"
  echo "  prefix: ${PREFIX}"
  echo "  env:    ${ENV_FILE}"
  echo "  unit:   ${SYSTEMD_UNIT}"
  echo
}

cmd_start() {
  require_root
  require_compose_bundle
  if env_contains_unsafe_defaults; then
    log_error "${ENV_FILE} still contains template or development defaults."
    log_error "Update the environment file before starting the platform."
    exit 1
  fi
  if has_systemd; then
    systemctl start "${SYSTEMD_UNIT}"
  else
    compose_cmd up -d --remove-orphans
  fi
  cmd_status
}

cmd_stop() {
  require_root
  if has_systemd; then
    systemctl stop "${SYSTEMD_UNIT}"
  else
    compose_cmd down
  fi
  cmd_status
}

cmd_restart() {
  require_root
  require_compose_bundle
  if env_contains_unsafe_defaults; then
    log_error "${ENV_FILE} still contains template or development defaults."
    log_error "Update the environment file before restarting the platform."
    exit 1
  fi
  if has_systemd; then
    systemctl restart "${SYSTEMD_UNIT}"
  else
    compose_cmd down
    compose_cmd up -d --remove-orphans
  fi
  cmd_status
}

cmd_status() {
  require_compose_bundle
  print_status_summary

  if has_systemd && systemctl is-active --quiet "${SYSTEMD_UNIT}"; then
    log_ok "systemd: ${SYSTEMD_UNIT} is active"
  elif ! has_systemd; then
    log_warn "systemd: unavailable, using direct compose operations"
  else
    log_warn "systemd: ${SYSTEMD_UNIT} is not active"
  fi

  if [[ -f "${ENV_FILE}" ]]; then
    if env_contains_unsafe_defaults; then
      log_warn "environment: production-safe bootstrap is incomplete"
    else
      log_ok "environment: bootstrap values look non-template"
    fi
  else
    log_warn "environment: ${ENV_FILE} is missing"
  fi

  echo
  log_info "compose services:"
  compose_cmd ps || true

  echo
  if curl -fsS http://localhost:8080/startup/status >/tmp/unison-startup-status.json 2>/dev/null; then
    log_info "startup status:"
    cat /tmp/unison-startup-status.json
    echo
    rm -f /tmp/unison-startup-status.json
  else
    log_warn "startup status endpoint unavailable at http://localhost:8080/startup/status"
  fi
}

cmd_logs() {
  require_compose_bundle
  local service="${1:-}"
  local lines="${2:-$TAIL_LINES}"
  if [[ -n "${service}" ]]; then
    compose_cmd logs --tail "${lines}" "${service}"
  else
    if has_systemd; then
      journalctl -u "${SYSTEMD_UNIT}" -n "${lines}" --no-pager
      echo
    fi
    compose_cmd logs --tail "${lines}"
  fi
}

cmd_follow() {
  require_compose_bundle
  local service="${1:-}"
  if [[ -n "${service}" ]]; then
    compose_cmd logs -f "${service}"
  else
    compose_cmd logs -f
  fi
}

cmd_health() {
  require_compose_bundle
  local overall=0
  local service

  print_status_summary
  while IFS= read -r service; do
    [[ -n "${service}" ]] || continue
    local cid
    cid="$(compose_cmd ps -q "${service}" 2>/dev/null || true)"
    if [[ -z "${cid}" ]]; then
      log_warn "${service}: container not created"
      overall=1
      continue
    fi
    local state
    state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${cid}" 2>/dev/null || echo unknown)"
    if [[ "${state}" == "healthy" || "${state}" == "running" ]]; then
      log_ok "${service}: ${state}"
    else
      log_warn "${service}: ${state}"
      overall=1
    fi
  done < <(compose_cmd config --services)

  if curl -fsS http://localhost:8080/startup/status >/tmp/unison-startup-health.json 2>/dev/null; then
    log_info "startup status:"
    cat /tmp/unison-startup-health.json
    echo
    rm -f /tmp/unison-startup-health.json
  fi

  return "${overall}"
}

cmd_doctor() {
  require_compose_bundle
  local ok=0

  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    log_ok "docker daemon reachable"
  else
    log_error "docker daemon unreachable"
    ok=1
  fi

  if has_systemd && systemctl status "${SYSTEMD_UNIT}" >/dev/null 2>&1; then
    log_ok "systemd unit present"
  elif ! has_systemd; then
    log_warn "systemd unavailable; compose-only mode"
  else
    log_warn "systemd unit missing or not loaded"
    ok=1
  fi

  if [[ -f "${ENV_FILE}" ]]; then
    log_ok "environment file present"
    if env_contains_unsafe_defaults; then
      log_warn "environment file still contains template defaults"
      ok=1
    fi
  else
    log_warn "environment file missing"
    ok=1
  fi

  if compose_cmd config >/dev/null 2>&1; then
    log_ok "compose bundle parses"
  else
    log_error "compose bundle invalid"
    ok=1
  fi

  return "${ok}"
}

cmd_recover() {
  require_root
  require_compose_bundle

  if env_contains_unsafe_defaults; then
    log_error "Refusing recovery while ${ENV_FILE} still contains unsafe defaults."
    exit 1
  fi

  log_info "Collecting pre-recovery status..."
  cmd_doctor || true
  echo
  log_info "Restarting ${SYSTEMD_UNIT}..."
  if has_systemd; then
    systemctl restart "${SYSTEMD_UNIT}"
  else
    compose_cmd down
    compose_cmd up -d --remove-orphans
  fi
  sleep 3
  echo
  cmd_health || true
}

cmd_help() {
  cat <<EOF
unisonctl - Milestone 1 operations for the installed Unison platform

Usage:
  unisonctl start
  unisonctl stop
  unisonctl restart
  unisonctl status
  unisonctl health
  unisonctl logs [service] [lines]
  unisonctl follow [service]
  unisonctl doctor
  unisonctl recover

Notes:
  - This command manages the compose-backed ${SYSTEMD_UNIT} stack.
  - It is the supported Milestone 1 operational path for native installs.
  - It refuses start/restart/recover if ${ENV_FILE} still contains template defaults.
EOF
}

main() {
  local cmd="${1:-help}"
  shift || true
  case "${cmd}" in
    start) cmd_start "$@" ;;
    stop) cmd_stop "$@" ;;
    restart) cmd_restart "$@" ;;
    status) cmd_status "$@" ;;
    health) cmd_health "$@" ;;
    logs) cmd_logs "$@" ;;
    follow) cmd_follow "$@" ;;
    doctor) cmd_doctor "$@" ;;
    recover) cmd_recover "$@" ;;
    help|-h|--help) cmd_help ;;
    *)
      log_error "Unknown command: ${cmd}"
      cmd_help
      exit 1
      ;;
  esac
}

main "$@"
