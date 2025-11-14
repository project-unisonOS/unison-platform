#!/bin/bash
#
# Unison Ubuntu Installation Script
# 
# This script installs and configures Unison on Ubuntu 22.04/24.04
# Usage: curl -sSL https://install.unison.ai | bash
#        or: ./ubuntu_install.sh
#
# Requirements: Fresh Ubuntu 22.04 or 24.04 installation
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
UNISON_USER="${UNISON_USER:-unison}"
UNISON_HOME="${UNISON_HOME:-/opt/unison}"
UNISON_VERSION="${UNISON_VERSION:-latest}"
INSTALL_DIR="${INSTALL_DIR:-/opt/unison}"
LOG_DIR="/var/log/unison"
DATA_DIR="/var/lib/unison"

# Logging functions
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
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Detect Ubuntu version
detect_ubuntu_version() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" != "ubuntu" ]]; then
            log_error "This script is designed for Ubuntu only. Detected: $ID"
            exit 1
        fi
        
        UBUNTU_VERSION="$VERSION_ID"
        log_info "Detected Ubuntu $UBUNTU_VERSION"
        
        if [[ "$UBUNTU_VERSION" != "22.04" && "$UBUNTU_VERSION" != "24.04" ]]; then
            log_warning "This script is tested on Ubuntu 22.04 and 24.04. Your version: $UBUNTU_VERSION"
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        log_error "Cannot detect OS version"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    apt-get update -qq
    
    # Core dependencies
    apt-get install -y -qq \
        curl \
        wget \
        git \
        build-essential \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    # Python 3.12
    log_info "Installing Python 3.12..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        python3-pip
    
    # Docker
    log_info "Installing Docker..."
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
    else
        log_success "Docker already installed"
    fi
    
    # Docker Compose
    log_info "Installing Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        apt-get install -y -qq docker-compose-plugin
    else
        log_success "Docker Compose already installed"
    fi
    
    # Audio dependencies
    log_info "Installing audio dependencies..."
    apt-get install -y -qq \
        pulseaudio \
        pulseaudio-utils \
        alsa-utils \
        portaudio19-dev \
        libsndfile1 \
        ffmpeg
    
    # Redis (for local development)
    log_info "Installing Redis..."
    apt-get install -y -qq redis-server
    systemctl enable redis-server
    systemctl start redis-server
    
    log_success "System dependencies installed"
}

# Create unison user
create_user() {
    log_info "Creating unison user..."
    
    if id "$UNISON_USER" &>/dev/null; then
        log_success "User $UNISON_USER already exists"
    else
        useradd -r -s /bin/bash -d "$UNISON_HOME" -m "$UNISON_USER"
        log_success "Created user $UNISON_USER"
    fi
    
    # Add to audio and docker groups
    usermod -aG audio "$UNISON_USER"
    usermod -aG docker "$UNISON_USER"
    
    log_success "User $UNISON_USER configured"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$DATA_DIR/keys"
    mkdir -p "$DATA_DIR/storage"
    mkdir -p "$DATA_DIR/postgres"
    
    chown -R "$UNISON_USER:$UNISON_USER" "$INSTALL_DIR"
    chown -R "$UNISON_USER:$UNISON_USER" "$LOG_DIR"
    chown -R "$UNISON_USER:$UNISON_USER" "$DATA_DIR"
    
    log_success "Directory structure created"
}

# Clone or update Unison repository
install_unison() {
    log_info "Installing Unison..."
    
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_info "Updating existing installation..."
        cd "$INSTALL_DIR"
        sudo -u "$UNISON_USER" git pull
    else
        log_info "Cloning Unison repository..."
        # TODO: Update with actual repository URL
        # sudo -u "$UNISON_USER" git clone https://github.com/project-unisonos/unison.git "$INSTALL_DIR"
        
        # For now, copy from current directory if running from repo
        if [[ -d "$(pwd)/.git" ]]; then
            log_info "Copying from current directory..."
            cp -r "$(pwd)/." "$INSTALL_DIR/"
            chown -R "$UNISON_USER:$UNISON_USER" "$INSTALL_DIR"
        else
            log_error "Cannot find Unison repository. Please clone manually to $INSTALL_DIR"
            exit 1
        fi
    fi
    
    log_success "Unison installed to $INSTALL_DIR"
}

# Configure audio
configure_audio() {
    log_info "Configuring audio..."
    
    # Enable PulseAudio for unison user
    if [[ ! -d "/home/$UNISON_USER/.config/pulse" ]]; then
        sudo -u "$UNISON_USER" mkdir -p "/home/$UNISON_USER/.config/pulse"
    fi
    
    # Set up PulseAudio to run as system service
    cat > /etc/systemd/system/pulseaudio.service <<EOF
[Unit]
Description=PulseAudio system server
After=sound.target

[Service]
Type=notify
ExecStart=/usr/bin/pulseaudio --daemonize=no --system --realtime --log-target=journal
Restart=on-failure
User=pulse
Group=pulse

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable pulseaudio
    systemctl start pulseaudio
    
    log_success "Audio configured"
}

# Generate RSA keys
generate_keys() {
    log_info "Generating RSA keys for auth and consent services..."
    
    KEYS_DIR="$DATA_DIR/keys"
    
    # Auth service keys
    if [[ ! -f "$KEYS_DIR/auth-primary_private.pem" ]]; then
        log_info "Generating auth service keys..."
        sudo -u "$UNISON_USER" python3.12 -c "
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import json
from datetime import datetime

# Generate RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

# Save private key
with open('$KEYS_DIR/auth-primary_private.pem', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Save public key
with open('$KEYS_DIR/auth-primary_public.pem', 'wb') as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))

# Save metadata
metadata = {
    'kid': 'auth-primary',
    'created_at': datetime.utcnow().isoformat(),
    'active': True
}
with open('$KEYS_DIR/auth-primary_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print('Auth keys generated')
"
    else
        log_success "Auth keys already exist"
    fi
    
    # Consent service keys
    if [[ ! -f "$KEYS_DIR/consent-primary_private.pem" ]]; then
        log_info "Generating consent service keys..."
        sudo -u "$UNISON_USER" python3.12 -c "
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import json
from datetime import datetime

# Generate RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

# Save private key
with open('$KEYS_DIR/consent-primary_private.pem', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Save public key
with open('$KEYS_DIR/consent-primary_public.pem', 'wb') as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))

# Save metadata
metadata = {
    'kid': 'consent-primary',
    'created_at': datetime.utcnow().isoformat(),
    'active': True
}
with open('$KEYS_DIR/consent-primary_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print('Consent keys generated')
"
    else
        log_success "Consent keys already exist"
    fi
    
    chown -R "$UNISON_USER:$UNISON_USER" "$KEYS_DIR"
    chmod 600 "$KEYS_DIR"/*_private.pem
    
    log_success "RSA keys generated"
}

# Install systemd services
install_systemd_services() {
    log_info "Installing systemd services..."
    
    # Copy service files from unison-platform/systemd/
    if [[ -d "$INSTALL_DIR/unison-platform/systemd" ]]; then
        cp "$INSTALL_DIR"/unison-platform/systemd/*.service /etc/systemd/system/
        systemctl daemon-reload
        log_success "Systemd services installed"
    else
        log_warning "Systemd service files not found. Will be created in next step."
    fi
}

# Create environment file
create_env_file() {
    log_info "Creating environment configuration..."
    
    cat > "$INSTALL_DIR/.env" <<EOF
# Unison Environment Configuration
# Generated on $(date)

# Paths
UNISON_HOME=$INSTALL_DIR
UNISON_DATA_DIR=$DATA_DIR
UNISON_LOG_DIR=$LOG_DIR
UNISON_KEYS_DIR=$DATA_DIR/keys

# Services
UNISON_ORCHESTRATOR_HOST=localhost
UNISON_ORCHESTRATOR_PORT=8090

UNISON_AUTH_HOST=localhost
UNISON_AUTH_PORT=8088

UNISON_CONSENT_HOST=localhost
UNISON_CONSENT_PORT=7072

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Jaeger
JAEGER_HOST=localhost
JAEGER_PORT=16686
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Security (CHANGE THESE IN PRODUCTION!)
UNISON_JWT_SECRET=$(openssl rand -hex 32)
UNISON_CONSENT_SECRET=$(openssl rand -hex 32)

# Audio
PULSE_SERVER=unix:/run/pulse/native
EOF
    
    chown "$UNISON_USER:$UNISON_USER" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    
    log_success "Environment configuration created"
}

# Install unisonctl
install_unisonctl() {
    log_info "Installing unisonctl..."
    
    if [[ -f "$INSTALL_DIR/unison-platform/scripts/native/unisonctl.sh" ]]; then
        ln -sf "$INSTALL_DIR/unison-platform/scripts/native/unisonctl.sh" /usr/local/bin/unisonctl
        chmod +x /usr/local/bin/unisonctl
        log_success "unisonctl installed to /usr/local/bin/unisonctl"
    else
        log_warning "unisonctl script not found. Will be created in next step."
    fi
}

# Run audio tests
test_audio() {
    log_info "Testing audio configuration..."
    
    if command -v aplay &> /dev/null && command -v arecord &> /dev/null; then
        log_info "Audio tools available"
        log_info "Run 'unisonctl test audio' to test microphone and speakers"
    else
        log_warning "Audio tools not found"
    fi
}

# Print summary
print_summary() {
    echo
    echo "═══════════════════════════════════════════════════════════"
    log_success "Unison Installation Complete!"
    echo "═══════════════════════════════════════════════════════════"
    echo
    echo "Installation Details:"
    echo "  • Install Directory: $INSTALL_DIR"
    echo "  • Data Directory: $DATA_DIR"
    echo "  • Log Directory: $LOG_DIR"
    echo "  • User: $UNISON_USER"
    echo
    echo "Next Steps:"
    echo "  1. Start services:"
    echo "     sudo unisonctl start"
    echo
    echo "  2. Check status:"
    echo "     sudo unisonctl status"
    echo
    echo "  3. Test audio:"
    echo "     sudo unisonctl test audio"
    echo
    echo "  4. View logs:"
    echo "     sudo unisonctl logs"
    echo
    echo "  5. Try the echo skill:"
    echo "     Say: 'echo hello world'"
    echo
    echo "Documentation: $INSTALL_DIR/unison-platform/docs/deployment/ubuntu-native.md"
    echo "═══════════════════════════════════════════════════════════"
    echo
}

# Main installation flow
main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "           Unison Ubuntu Installation Script"
    echo "═══════════════════════════════════════════════════════════"
    echo
    
    check_root
    detect_ubuntu_version
    
    log_info "Starting installation..."
    
    install_dependencies
    create_user
    create_directories
    install_unison
    configure_audio
    generate_keys
    create_env_file
    install_systemd_services
    install_unisonctl
    test_audio
    
    print_summary
    
    log_success "Installation completed successfully!"
}

# Run main function
main "$@"
