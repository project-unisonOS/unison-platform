#!/bin/bash
# Blue/Green deployment script for Unison Platform
# Provides zero-downtime deployments with Docker Compose

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BLUE_PROJECT="unison-blue"
GREEN_PROJECT="unison-green"
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_CHECK_TIMEOUT=300
LOAD_BALANCER_CONFIG="/etc/nginx/conf.d/unison.conf"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running"
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker compose >/dev/null 2>&1; then
        error "Docker Compose is not available"
    fi
    
    # Check if compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Compose file $COMPOSE_FILE not found"
    fi
    
    # Check if cosign is available for image verification
    if ! command -v cosign >/dev/null 2>&1; then
        warn "cosign not found - skipping image signature verification"
        COSIGN_AVAILABLE=false
    else
        COSIGN_AVAILABLE=true
    fi
    
    log "Prerequisites check completed"
}

# Get current active environment
get_current_environment() {
    local current_env
    current_env=$(docker compose ls --format "{{.Name}}" | grep "unison-" | cut -d- -f2 | head -1 || echo "none")
    echo "$current_env"
}

# Determine target environment
get_target_environment() {
    local current_env
    current_env=$(get_current_environment)
    
    if [[ "$current_env" == "blue" ]]; then
        echo "green"
    elif [[ "$current_env" == "green" ]]; then
        echo "blue"
    else
        echo "blue"  # Default to blue for initial deployment
    fi
}

# Pull and validate images
pull_and_validate_images() {
    log "Pulling and validating images..."
    
    # Pull all images
    docker compose -f "$COMPOSE_FILE" pull
    
    # Extract image references from compose file
    local images
    images=$(docker compose -f "$COMPOSE_FILE" config | grep 'image:' | awk '{print $2}')
    
    # Verify image signatures if cosign is available
    if [[ "$COSIGN_AVAILABLE" == true ]]; then
        log "Verifying image signatures..."
        for image in $images; do
            info "Verifying signature for $image"
            if ! cosign verify "$image" 2>/dev/null; then
                warn "Signature verification failed for $image - continuing anyway"
            fi
        done
    else
        warn "Skipping image signature verification (cosign not available)"
    fi
    
    log "Image pull and validation completed"
}

# Deploy to target environment
deploy_to_environment() {
    local target_env="$1"
    
    log "Deploying to environment: $target_env"
    
    # Deploy services
    docker compose -f "$COMPOSE_FILE" -p "$target_env" up -d
    
    log "Deployment to $target_env initiated"
}

# Wait for services to be healthy
wait_for_health() {
    local target_env="$1"
    local start_time
    start_time=$(date +%s)
    
    log "Waiting for services to become healthy..."
    
    while true; do
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $HEALTH_CHECK_TIMEOUT ]]; then
            error "Health check timeout after ${HEALTH_CHECK_TIMEOUT} seconds"
        fi
        
        # Check if all services are healthy
        local unhealthy_services
        unhealthy_services=$(docker compose -f "$COMPOSE_FILE" -p "$target_env" ps --format "{{.Service}} {{.Status}}" | grep -v "healthy\|exited" || true)
        
        if [[ -z "$unhealthy_services" ]]; then
            log "All services are healthy"
            break
        fi
        
        info "Waiting for services... (${elapsed}s elapsed)"
        info "Unhealthy services: $unhealthy_services"
        sleep 10
    done
}

# Run smoke tests
run_smoke_tests() {
    local target_env="$1"
    
    log "Running smoke tests..."
    
    # Test identity service
    if ! curl -f -s "http://localhost:8095/health" >/dev/null; then
        error "Identity service health check failed"
    fi
    
    # Test consent service
    if ! curl -f -s "http://localhost:8096/health" >/dev/null; then
        error "Consent service health check failed"
    fi
    
    # Test connector broker
    if ! curl -f -s "http://localhost:8097/health" >/dev/null; then
        error "Connector broker health check failed"
    fi
    
    # Test MCP proxy
    if ! curl -f -s "http://localhost:8098/health" >/dev/null; then
        error "MCP proxy health check failed"
    fi
    
    log "Smoke tests passed"
}

# Switch load balancer
switch_load_balancer() {
    local target_env="$1"
    
    log "Switching load balancer to $target_env"
    
    # Update Nginx configuration
    cat > "$LOAD_BALANCER_CONFIG" << EOF
# Unison Platform Load Balancer Configuration
# Active environment: $target_env

upstream unison_backend {
    server 127.0.0.1:8095;  # Identity service
    server 127.0.0.1:8096;  # Consent service
    server 127.0.0.1:8097;  # Connector broker
    server 127.0.0.1:8098;  # MCP proxy
}

server {
    listen 80;
    server_name unisonos.org app.unisonos.org;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name unisonos.org app.unisonos.org;
    
    # SSL configuration
    ssl_certificate /etc/nginx/certs/unisonos.org.crt;
    ssl_certificate_key /etc/nginx/certs/unisonos.org.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Identity service
    location /identity/ {
        proxy_pass http://127.0.0.1:8095/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Consent service
    location /consent/ {
        proxy_pass http://127.0.0.1:8096/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Connector broker
    location /connectors/ {
        proxy_pass http://127.0.0.1:8097/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # MCP proxy
    location /mcp/ {
        proxy_pass http://127.0.0.1:8098/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Default location
    location / {
        return 404;
    }
}
EOF
    
    # Test Nginx configuration
    if ! nginx -t; then
        error "Nginx configuration test failed"
    fi
    
    # Reload Nginx
    nginx -s reload
    
    log "Load balancer switched to $target_env"
}

# Cleanup old environment
cleanup_old_environment() {
    local old_env="$1"
    
    if [[ "$old_env" != "none" ]]; then
        log "Cleaning up old environment: $old_env"
        
        # Stop and remove old environment
        docker compose -f "$COMPOSE_FILE" -p "$old_env" down
        
        # Remove old volumes (optional - comment out if you want to keep them)
        # docker volume rm "unison-${old_env}_postgres_data" 2>/dev/null || true
        # docker volume rm "unison-${old_env}_vault_data" 2>/dev/null || true
        
        log "Old environment $old_env cleaned up"
    fi
}

# Rollback function
rollback() {
    local current_env="$1"
    local rollback_env="$2"
    
    warn "Initiating rollback to $rollback_env"
    
    # Switch load balancer back
    switch_load_balancer "$rollback_env"
    
    # Stop current environment
    docker compose -f "$COMPOSE_FILE" -p "$current_env" down
    
    log "Rollback completed to $rollback_env"
}

# Main deployment function
deploy() {
    local current_env
    local target_env
    
    log "Starting blue/green deployment..."
    
    # Check prerequisites
    check_prerequisites
    
    # Get environments
    current_env=$(get_current_environment)
    target_env=$(get_target_environment)
    
    info "Current environment: $current_env"
    info "Target environment: $target_env"
    
    # Pull and validate images
    pull_and_validate_images
    
    # Deploy to target environment
    deploy_to_environment "$target_env"
    
    # Wait for health checks
    wait_for_health "$target_env"
    
    # Run smoke tests
    run_smoke_tests "$target_env"
    
    # Switch load balancer
    switch_load_balancer "$target_env"
    
    # Cleanup old environment
    cleanup_old_environment "$current_env"
    
    log "Deployment completed successfully!"
    log "Active environment: $target_env"
}

# Status function
status() {
    local current_env
    current_env=$(get_current_environment)
    
    info "Current active environment: $current_env"
    
    if [[ "$current_env" != "none" ]]; then
        echo ""
        docker compose -f "$COMPOSE_FILE" -p "$current_env" ps
    else
        warn "No active environment found"
    fi
}

# Rollback function
rollback_command() {
    local current_env
    local rollback_env
    
    current_env=$(get_current_environment)
    
    if [[ "$current_env" == "none" ]]; then
        error "No active environment to rollback from"
    fi
    
    if [[ "$current_env" == "blue" ]]; then
        rollback_env="green"
    else
        rollback_env="blue"
    fi
    
    # Check if rollback environment exists
    if ! docker compose -f "$COMPOSE_FILE" -p "$rollback_env" ps >/dev/null 2>&1; then
        error "Rollback environment $rollback_env does not exist"
    fi
    
    rollback "$current_env" "$rollback_env"
}

# Show usage
usage() {
    echo "Usage: $0 {deploy|status|rollback|help}"
    echo ""
    echo "Commands:"
    echo "  deploy   - Deploy new version using blue/green strategy"
    echo "  status   - Show current deployment status"
    echo "  rollback - Rollback to previous version"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy"
    echo "  $0 status"
    echo "  $0 rollback"
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    status)
        status
        ;;
    rollback)
        rollback_command
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        error "Unknown command: $1. Use 'help' for usage information."
        ;;
esac
