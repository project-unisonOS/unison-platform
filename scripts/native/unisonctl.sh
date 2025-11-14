#!/bin/bash
#
# unisonctl - Unison Control Script
#
# Manage Unison services on Ubuntu
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
UNISON_HOME="${UNISON_HOME:-/opt/unison}"
SERVICES=(
    "unison-orchestrator"
    "unison-auth"
    "unison-consent"
)

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This command requires root privileges (use sudo)"
        exit 1
    fi
}

# Start all services
cmd_start() {
    check_root
    log_info "Starting Unison services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Starting $service..."
        systemctl start "$service"
    done
    
    log_success "All services started"
    cmd_status
}

# Stop all services
cmd_stop() {
    check_root
    log_info "Stopping Unison services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Stopping $service..."
        systemctl stop "$service"
    done
    
    log_success "All services stopped"
}

# Restart all services
cmd_restart() {
    check_root
    log_info "Restarting Unison services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Restarting $service..."
        systemctl restart "$service"
    done
    
    log_success "All services restarted"
    cmd_status
}

# Show status of all services
cmd_status() {
    echo
    echo "═══════════════════════════════════════════════════════════"
    echo "                  Unison Service Status"
    echo "═══════════════════════════════════════════════════════════"
    echo
    
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            echo -e "${GREEN}●${NC} $service: ${GREEN}active${NC}"
        else
            echo -e "${RED}●${NC} $service: ${RED}inactive${NC}"
        fi
    done
    
    echo
    echo "═══════════════════════════════════════════════════════════"
}

# Show logs
cmd_logs() {
    local service="${1:-unison-orchestrator}"
    local lines="${2:-50}"
    
    log_info "Showing logs for $service (last $lines lines)..."
    journalctl -u "$service" -n "$lines" --no-pager
}

# Follow logs
cmd_logs_follow() {
    local service="${1:-unison-orchestrator}"
    
    log_info "Following logs for $service (Ctrl+C to stop)..."
    journalctl -u "$service" -f
}

# Enable services
cmd_enable() {
    check_root
    log_info "Enabling Unison services..."
    
    for service in "${SERVICES[@]}"; do
        systemctl enable "$service"
    done
    
    log_success "All services enabled (will start on boot)"
}

# Disable services
cmd_disable() {
    check_root
    log_info "Disabling Unison services..."
    
    for service in "${SERVICES[@]}"; do
        systemctl disable "$service"
    done
    
    log_success "All services disabled (will not start on boot)"
}

# Test audio
cmd_test_audio() {
    log_info "Testing audio configuration..."
    echo
    
    # Test speakers
    log_info "Testing speakers (you should hear a tone)..."
    if command -v speaker-test &> /dev/null; then
        speaker-test -t sine -f 1000 -l 1 &
        sleep 2
        killall speaker-test 2>/dev/null || true
        log_success "Speaker test complete"
    else
        log_warning "speaker-test not available"
    fi
    
    echo
    
    # Test microphone
    log_info "Testing microphone (recording 3 seconds)..."
    if command -v arecord &> /dev/null; then
        arecord -d 3 -f cd /tmp/test_recording.wav
        log_success "Recording complete"
        
        log_info "Playing back recording..."
        if command -v aplay &> /dev/null; then
            aplay /tmp/test_recording.wav
            log_success "Playback complete"
        fi
        
        rm -f /tmp/test_recording.wav
    else
        log_warning "arecord not available"
    fi
    
    echo
    log_success "Audio test complete"
}

# Health check
cmd_health() {
    log_info "Checking Unison health..."
    echo
    
    # Check orchestrator
    if curl -s http://localhost:8090/health > /dev/null 2>&1; then
        log_success "Orchestrator: healthy"
    else
        log_error "Orchestrator: unhealthy"
    fi
    
    # Check auth
    if curl -s http://localhost:8088/health > /dev/null 2>&1; then
        log_success "Auth: healthy"
    else
        log_error "Auth: unhealthy"
    fi
    
    # Check consent
    if curl -s http://localhost:7072/health > /dev/null 2>&1; then
        log_success "Consent: healthy"
    else
        log_error "Consent: unhealthy"
    fi
    
    # Check Redis
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis: healthy"
    else
        log_error "Redis: unhealthy"
    fi
    
    echo
}

# Version info
cmd_version() {
    echo "unisonctl version 1.0.0"
    echo "Unison installation: $UNISON_HOME"
    
    if [[ -f "$UNISON_HOME/.git/HEAD" ]]; then
        cd "$UNISON_HOME"
        echo "Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
        echo "Git branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
    fi
}

# Show help
cmd_help() {
    cat <<EOF
unisonctl - Unison Control Script

Usage: unisonctl <command> [options]

Commands:
  start              Start all Unison services
  stop               Stop all Unison services
  restart            Restart all Unison services
  status             Show status of all services
  enable             Enable services to start on boot
  disable            Disable services from starting on boot
  
  logs [service]     Show logs for a service (default: orchestrator)
  follow [service]   Follow logs for a service
  
  test audio         Test microphone and speakers
  health             Check health of all services
  
  version            Show version information
  help               Show this help message

Examples:
  sudo unisonctl start
  sudo unisonctl status
  sudo unisonctl logs unison-auth
  sudo unisonctl follow unison-orchestrator
  sudo unisonctl test audio
  sudo unisonctl health

For more information, visit: https://docs.unison.ai
EOF
}

# Main command dispatcher
main() {
    local command="${1:-help}"
    shift || true
    
    case "$command" in
        start)
            cmd_start "$@"
            ;;
        stop)
            cmd_stop "$@"
            ;;
        restart)
            cmd_restart "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        enable)
            cmd_enable "$@"
            ;;
        disable)
            cmd_disable "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        follow)
            cmd_logs_follow "$@"
            ;;
        test)
            local subcommand="${1:-}"
            shift || true
            case "$subcommand" in
                audio)
                    cmd_test_audio "$@"
                    ;;
                *)
                    log_error "Unknown test: $subcommand"
                    cmd_help
                    exit 1
                    ;;
            esac
            ;;
        health)
            cmd_health "$@"
            ;;
        version)
            cmd_version "$@"
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            log_error "Unknown command: $command"
            cmd_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
