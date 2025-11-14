#!/bin/bash
# Security hardening script for Unison Platform
# Run this script on your production VMs to secure the environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
}

# Setup Docker security
setup_docker_security() {
    log "Setting up Docker security configuration..."
    
    # Create Docker daemon configuration
    cat > /etc/docker/daemon.json << 'EOF'
{
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "seccomp-profile": "default",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "exec-opts": ["native.cgroupdriver=systemd"]
}
EOF

    # Restart Docker to apply configuration
    systemctl restart docker
    systemctl enable docker
    
    log "Docker security configuration applied"
}

# Setup firewall rules
setup_firewall() {
    log "Configuring firewall rules..."
    
    # Reset firewall
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (with rate limiting)
    ufw limit ssh
    
    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow Vault admin access from internal network only
    ufw allow from 10.0.0.0/8 to any port 8200
    ufw allow from 172.16.0.0/12 to any port 8200
    ufw allow from 192.168.0.0/16 to any port 8200
    
    # Enable firewall
    ufw --force enable
    
    log "Firewall rules configured"
}

# Setup mTLS certificates
setup_mtls() {
    log "Setting up mTLS certificates..."
    
    CERT_DIR="/etc/unison/tls"
    mkdir -p "$CERT_DIR"
    chmod 700 "$CERT_DIR"
    
    # Generate CA certificate
    if [[ ! -f "$CERT_DIR/ca.crt" ]]; then
        log "Generating CA certificate..."
        openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" -days 365 -nodes \
            -subj "/C=US/ST=California/L=San Francisco/O=Unison/OU=Platform/CN=Unison CA"
        
        chmod 600 "$CERT_DIR/ca.key"
        chmod 644 "$CERT_DIR/ca.crt"
    fi
    
    # Generate service certificates
    SERVICES=("identity" "consent" "connector-broker" "mcp-proxy" "vault")
    
    for service in "${SERVICES[@]}"; do
        if [[ ! -f "$CERT_DIR/${service}.crt" ]]; then
            log "Generating certificate for $service service..."
            
            # Create certificate signing request
            openssl req -new -newkey rsa:2048 -nodes \
                -keyout "$CERT_DIR/${service}.key" \
                -out "$CERT_DIR/${service}.csr" \
                -subj "/C=US/ST=California/L=San Francisco/O=Unison/OU=Platform/CN=${service}.unisonos.org"
            
            # Sign certificate with CA
            openssl x509 -req -in "$CERT_DIR/${service}.csr" \
                -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
                -CAcreateserial -out "$CERT_DIR/${service}.crt" -days 365 \
                -extensions v3_req -extfile <(cat <<EOF
[v3_req]
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${service}.unisonos.org
DNS.2 = ${service}
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF
)
            
            # Set permissions
            chmod 600 "$CERT_DIR/${service}.key"
            chmod 644 "$CERT_DIR/${service}.crt"
            
            # Remove CSR
            rm "$CERT_DIR/${service}.csr"
        fi
    done
    
    log "mTLS certificates generated"
}

# Setup secure secrets
setup_secrets() {
    log "Setting up secure secrets..."
    
    SECRETS_DIR="./secrets"
    mkdir -p "$SECRETS_DIR"
    chmod 700 "$SECRETS_DIR"
    
    # Generate secure passwords if they don't exist
    if [[ ! -f "$SECRETS_DIR/db_password.txt" ]]; then
        openssl rand -base64 32 > "$SECRETS_DIR/db_password.txt"
    fi
    
    if [[ ! -f "$SECRETS_DIR/redis_password.txt" ]]; then
        openssl rand -base64 32 > "$SECRETS_DIR/redis_password.txt"
    fi
    
    if [[ ! -f "$SECRETS_DIR/jwt_signing_key.txt" ]]; then
        openssl rand -base64 64 > "$SECRETS_DIR/jwt_signing_key.txt"
    fi
    
    if [[ ! -f "$SECRETS_DIR/admin_password.txt" ]]; then
        openssl rand -base64 16 > "$SECRETS_DIR/admin_password.txt"
    fi
    
    # Set secure permissions
    chmod 600 "$SECRETS_DIR"/*.txt
    
    log "Secure secrets generated"
}

# Setup log aggregation
setup_logging() {
    log "Setting up log aggregation..."
    
    # Create log directory
    mkdir -p /var/log/unison
    chmod 750 /var/log/unison
    
    # Configure rsyslog for centralized logging
    cat > /etc/rsyslog.d/unison.conf << 'EOF'
# Unison Platform log aggregation
# Ship all Unison service logs to centralized storage
:programname, isequal, "unison-vault" @@log-collector.unisonos.org:514;UnisonFormat
:programname, isequal, "unison-identity" @@log-collector.unisonos.org:514;UnisonFormat
:programname, isequal, "unison-consent" @@log-collector.unisonos.org:514;UnisonFormat
:programname, isequal, "unison-connector-broker" @@log-collector.unisonos.org:514;UnisonFormat
:programname, isequal, "unison-mcp-proxy" @@log-collector.unisonos.org:514;UnisonFormat
& stop

# Local log rotation for audit trails
$template UnisonAuditFormat,"%timestamp% %hostname% %programname% %msg%\n"
:programname, contains, "unison-" /var/log/unison/audit.log;UnisonAuditFormat
& stop
EOF

    # Setup log rotation
    cat > /etc/logrotate.d/unison << 'EOF'
/var/log/unison/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 syslog adm
    postrotate
        systemctl reload rsyslog
    endscript
    lastaction
        # Ship to immutable storage
        aws s3 cp /var/log/unison/audit.log.1.gz s3://unison-backups/audit/$(date +%Y)/$(date +%m)/$(date +%d)-audit.log.gz --server-side-encryption
    endscript
}
EOF

    # Restart rsyslog
    systemctl restart rsyslog
    
    log "Log aggregation configured"
}

# Setup system hardening
setup_system_hardening() {
    log "Applying system hardening..."
    
    # Create unison user for running services
    if ! id "unison" &>/dev/null; then
        useradd -r -s /bin/false -d /opt/unison unison
    fi
    
    # Secure SSH configuration
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
    
    cat > /etc/ssh/sshd_config << 'EOF'
# SSH hardening configuration
Port 22
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
PrintMotd no
PrintLastLog yes
TCPKeepAlive yes
UsePrivilegeSeparation yes
Subsystem sftp /usr/lib/openssh/sftp-server
MaxAuthTries 3
MaxSessions 2
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

    # Restart SSH
    systemctl restart ssh
    
    # Setup automatic security updates
    apt-get update
    apt-get install -y unattended-upgrades
    
    cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESM:${distro_codename}";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
EOF

    cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

    log "System hardening applied"
}

# Setup monitoring and alerting
setup_monitoring() {
    log "Setting up monitoring and alerting..."
    
    # Create monitoring directory
    mkdir -p /opt/unison/monitoring
    
    # Setup basic health check script
    cat > /opt/unison/monitoring/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for Unison Platform

SERVICES=("vault" "unison-identity" "unison-consent" "unison-connector-broker" "unison-mcp-proxy")
FAILED_SERVICES=()

for service in "${SERVICES[@]}"; do
    if ! docker compose -f /opt/unison/docker-compose.prod.yml ps "$service" | grep -q "Up.*healthy"; then
        FAILED_SERVICES+=("$service")
    fi
done

if [[ ${#FAILED_SERVICES[@]} -gt 0 ]]; then
    echo "ALERT: Failed services: ${FAILED_SERVICES[*]}"
    # Send alert (configure your preferred alerting method)
    # curl -X POST "https://alerts.unisonos.org/webhook" -d "services=${FAILED_SERVICES[*]}"
    exit 1
fi

echo "All services healthy"
exit 0
EOF

    chmod +x /opt/unison/monitoring/health-check.sh
    
    # Setup cron job for health checks
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/unison/monitoring/health-check.sh") | crontab -
    
    log "Monitoring and alerting configured"
}

# Setup backup configuration
setup_backups() {
    log "Setting up backup configuration..."
    
    # Create backup directory
    mkdir -p /opt/unison/backups
    chmod 700 /opt/unison/backups
    
    # Setup backup script
    cat > /opt/unison/backups/backup.sh << 'EOF'
#!/bin/bash
# Backup script for Unison Platform

BACKUP_DIR="/opt/unison/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="unison_backup_${DATE}.tar.gz"

# Create backup
docker compose -f /opt/unison/docker-compose.prod.yml exec -T postgres pg_dump -U unison unison_identity > "$BACKUP_DIR/postgres_${DATE}.sql"

# Backup Vault data
docker run --rm -v unison-platform_vault_data:/data -v "$BACKUP_DIR":/backup alpine tar czf "/backup/vault_${DATE}.tar.gz" -C /data .

# Create compressed backup
tar czf "$BACKUP_DIR/$BACKUP_FILE" -C "$BACKUP_DIR" "postgres_${DATE}.sql" "vault_${DATE}.tar.gz"

# Upload to S3 (configure your AWS credentials)
aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://unison-backups/daily/$BACKUP_FILE" --server-side-encryption

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -name "unison_backup_*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "postgres_*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "vault_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

    chmod +x /opt/unison/backups/backup.sh
    
    # Setup cron job for daily backups at 2 AM
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/unison/backups/backup.sh") | crontab -
    
    log "Backup configuration completed"
}

# Main execution
main() {
    log "Starting Unison Platform security setup..."
    
    check_root
    setup_docker_security
    setup_firewall
    setup_mtls
    setup_secrets
    setup_logging
    setup_system_hardening
    setup_monitoring
    setup_backups
    
    log "Security setup completed successfully!"
    log ""
    log "Next steps:"
    log "1. Copy .env.prod.template to .env.prod and update with your values"
    log "2. Review generated certificates in /etc/unison/tls"
    log "3. Configure your external monitoring and alerting"
    log "4. Test backup script: /opt/unison/backups/backup.sh"
    log "5. Deploy services: docker compose -f docker-compose.prod.yml up -d"
    
    # Display generated passwords (only show once)
    if [[ -f "./secrets/db_password.txt" ]]; then
        warn "Generated passwords (save these securely):"
        echo "Database password: $(cat ./secrets/db_password.txt)"
        echo "Redis password: $(cat ./secrets/redis_password.txt)"
        echo "Admin password: $(cat ./secrets/admin_password.txt)"
        warn "These passwords will not be shown again. Save them securely."
    fi
}

# Run main function
main "$@"
