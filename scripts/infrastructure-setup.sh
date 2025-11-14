#!/bin/bash
# Infrastructure setup script for Unison Platform
# Provisions cloud resources and configures the environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLOUD_PROVIDER=${CLOUD_PROVIDER:-"digitalocean"}
REGION=${REGION:-"nyc3"}
DROPLET_SIZE=${DROPLET_SIZE:-"s-4vcpu-8gb"}
DB_SIZE=${DB_SIZE:-"db-s-2vcpu-4gb"}
DOMAIN=${DOMAIN:-"unisonos.org"}

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
    
    # Check for cloud provider CLI
    case $CLOUD_PROVIDER in
        "digitalocean")
            if ! command -v doctl >/dev/null 2>&1; then
                error "doctl (DigitalOcean CLI) not found. Install from https://github.com/digitalocean/doctl"
            fi
            ;;
        "aws")
            if ! command -v aws >/dev/null 2>&1; then
                error "AWS CLI not found. Install from https://aws.amazon.com/cli/"
            fi
            ;;
        "gcp")
            if ! command -v gcloud >/dev/null 2>&1; then
                error "Google Cloud CLI not found. Install from https://cloud.google.com/sdk"
            fi
            ;;
        *)
            error "Unsupported cloud provider: $CLOUD_PROVIDER"
            ;;
    esac
    
    # Check for required tools
    for tool in docker curl jq openssl; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            error "$tool not found. Please install it first."
        fi
    done
    
    # Check authentication
    case $CLOUD_PROVIDER in
        "digitalocean")
            if ! doctl account get >/dev/null 2>&1; then
                error "DigitalOcean authentication failed. Run 'doctl auth init'"
            fi
            ;;
        "aws")
            if ! aws sts get-caller-identity >/dev/null 2>&1; then
                error "AWS authentication failed. Configure credentials with 'aws configure'"
            fi
            ;;
        esac
    
    log "Prerequisites check completed"
}

# Create SSH key for cloud instances
create_ssh_key() {
    log "Creating SSH key for cloud instances..."
    
    SSH_KEY_NAME="unison-platform-$(date +%s)"
    SSH_KEY_FILE="$HOME/.ssh/$SSH_KEY_NAME"
    
    # Generate SSH key
    ssh-keygen -t ed25519 -f "$SSH_KEY_FILE" -N "" -C "unison-platform@$(hostname)"
    
    # Add to SSH agent
    ssh-add "$SSH_KEY_FILE" 2>/dev/null || true
    
    # Upload to cloud provider
    case $CLOUD_PROVIDER in
        "digitalocean")
            doctl compute ssh-key create "$SSH_KEY_NAME" --public-key "$(cat "$SSH_KEY_FILE.pub")"
            ;;
        "aws")
            aws ec2 import-key-pair --key-name "$SSH_KEY_NAME" --public-key-material "$(cat "$SSH_KEY_FILE.pub")"
            ;;
    esac
    
    echo "$SSH_KEY_NAME" > .ssh_key_name
    echo "$SSH_KEY_FILE" > .ssh_key_file
    
    log "SSH key created: $SSH_KEY_NAME"
}

# Provision database
provision_database() {
    log "Provisioning managed database..."
    
    case $CLOUD_PROVIDER in
        "digitalocean")
            # Create PostgreSQL cluster
            DB_CLUSTER_ID=$(doctl databases create unison-db \
                --engine pg \
                --version 16 \
                --size "$DB_SIZE" \
                --region "$REGION" \
                --num-nodes 1 \
                --format json | jq -r '.[0].id')
            
            # Wait for database to be ready
            log "Waiting for database to be ready..."
            while true; do
                DB_STATUS=$(doctl databases get "$DB_CLUSTER_ID" --format json | jq -r '.[0].status')
                if [[ "$DB_STATUS" == "online" ]]; then
                    break
                fi
                sleep 30
            done
            
            # Get connection details
            DB_CONNECTION_STRING=$(doctl databases get "$DB_CLUSTER_ID" --format json | jq -r '.[0].connection.uri')
            DB_HOST=$(echo "$DB_CONNECTION_STRING" | sed 's/.*@\([^:]*\):.*/\1/')
            DB_PORT=$(echo "$DB_CONNECTION_STRING" | sed 's/.*:\([0-9]*\)\/.*/\1/')
            DB_USER=$(echo "$DB_CONNECTION_STRING" | sed 's/.*:\/\/\([^:]*\):.*/\1/')
            DB_PASSWORD=$(doctl databases get "$DB_CLUSTER_ID" --format json | jq -r '.[0].connection.password')
            DB_NAME=unison_identity
            ;;
        "aws")
            # Create RDS PostgreSQL instance
            DB_INSTANCE_ID=$(aws rds create-db-instance \
                --db-instance-identifier unison-db \
                --db-instance-class db.t3.micro \
                --engine postgres \
                --engine-version 16.1 \
                --master-username unison \
                --master-user-password "$(openssl rand -base64 32)" \
                --allocated-storage 20 \
                --storage-type gp2 \
                --vpc-security-group-ids sg-xxxxxxxx \
                --db-subnet-group-name default \
                --backup-retention-period 7 \
                --multi-az \
                --storage-encrypted \
                --query 'DBInstance.DBInstanceIdentifier' \
                --output text)
            
            # Wait for database to be ready
            aws rds wait db-instance-available --db-instance-identifier "$DB_INSTANCE_ID"
            
            # Get connection details
            DB_HOST=$(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE_ID" --query 'DBInstances[0].Endpoint.Address' --output text)
            DB_PORT=5432
            DB_USER=unison
            DB_PASSWORD=$(aws rds describe-db-instances --db-instance-identifier "$DB_INSTANCE_ID" --query 'DBInstances[0].MasterUsername' --output text)  # This needs to be stored securely
            DB_NAME=unison_identity
            ;;
    esac
    
    # Save database credentials
    cat > .db_credentials << EOF
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME
EOF
    
    chmod 600 .db_credentials
    
    log "Database provisioned: $DB_HOST:$DB_PORT"
}

# Provision compute instances
provision_instances() {
    log "Provisioning compute instances..."
    
    SSH_KEY_NAME=$(cat .ssh_key_name)
    
    # Create user data script for instances
    cat > user-data.sh << 'EOF'
#!/bin/bash
# User data script for Unison Platform instances

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create unison user
useradd -m -s /bin/bash unison
usermod -aG docker unison

# Create application directory
mkdir -p /opt/unison
chown unison:unison /opt/unison

# Configure firewall
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Install monitoring tools
apt-get install -y htop iotop nethogs

# Setup log rotation
cat > /etc/logrotate.d/unison << 'EOL'
/opt/unison/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 unison unison
}
EOL
EOF
    
    # Provision instances
    case $CLOUD_PROVIDER in
        "digitalocean")
            # Create first instance (primary)
            DROPLET_1_ID=$(doctl compute droplet create unison-identity-1 \
                --size "$DROPLET_SIZE" \
                --region "$REGION" \
                --image ubuntu-22-04-x64 \
                --ssh-keys "$SSH_KEY_NAME" \
                --user-data-file user-data.sh \
                --enable-private-networking \
                --format json | jq -r '.[0].id')
            
            # Create second instance (secondary)
            DROPLET_2_ID=$(doctl compute droplet create unison-identity-2 \
                --size "$DROPLET_SIZE" \
                --region "$REGION" \
                --image ubuntu-22-04-x64 \
                --ssh-keys "$SSH_KEY_NAME" \
                --user-data-file user-data.sh \
                --enable-private-networking \
                --format json | jq -r '.[0].id')
            
            # Wait for instances to be ready
            log "Waiting for instances to be ready..."
            for droplet_id in "$DROPLET_1_ID" "$DROPLET_2_ID"; do
                while true; do
                    DROPLET_STATUS=$(doctl compute droplet get "$droplet_id" --format json | jq -r '.[0].status')
                    if [[ "$DROPLET_STATUS" == "active" ]]; then
                        break
                    fi
                    sleep 30
                done
            done
            
            # Get instance IPs
            DROPLET_1_IP=$(doctl compute droplet get "$DROPLET_1_ID" --format json | jq -r '.[0].networks.v4[0].ip_address')
            DROPLET_2_IP=$(doctl compute droplet get "$DROPLET_2_ID" --format json | jq -r '.[0].networks.v4[0].ip_address')
            ;;
        "aws")
            # Create EC2 instances
            # Similar implementation for AWS
            ;;
    esac
    
    # Save instance information
    cat > .instance_info << EOF
PRIMARY_IP=$DROPLET_1_IP
SECONDARY_IP=$DROPLET_2_IP
PRIMARY_ID=$DROPLET_1_ID
SECONDARY_ID=$DROPLET_2_ID
EOF
    
    chmod 600 .instance_info
    
    log "Instances provisioned: $DROPLET_1_IP, $DROPLET_2_IP"
}

# Setup DNS and load balancer
setup_networking() {
    log "Setting up DNS and load balancer..."
    
    PRIMARY_IP=$(cat .instance_info | grep PRIMARY_IP | cut -d= -f2)
    
    case $CLOUD_PROVIDER in
        "digitalocean")
            # Create load balancer
            LB_ID=$(doctl compute load-balancer create unison-lb \
                --region "$REGION" \
                --forwarding-rules "entry_protocol:http,entry_port:80,target_protocol:http,target_port:80,certificate_id:,tls_passthrough:false" \
                --forwarding-rules "entry_protocol:https,entry_port:443,target_protocol:https,target_port:443,certificate_id:,tls_passthrough:false" \
                --health-check "protocol:http,port:80,path:/health,check_interval_seconds:30,response_timeout_seconds:10,healthy_threshold:5,unhealthy_threshold:3" \
                --droplet-ids "$(cat .instance_info | grep PRIMARY_ID | cut -d= -f2)" \
                --format json | jq -r '.[0].id')
            
            # Wait for load balancer to be active
            while true; do
                LB_STATUS=$(doctl compute load-balancer get "$LB_ID" --format json | jq -r '.[0].status')
                if [[ "$LB_STATUS" == "active" ]]; then
                    break
                fi
                sleep 30
            done
            
            # Get load balancer IP
            LB_IP=$(doctl compute load-balancer get "$LB_ID" --format json | jq -r '.[0].ip')
            
            # Create DNS records
            doctl compute domain records create "$DOMAIN" \
                --record-type A \
                --record-name "@" \
                --record-data "$LB_IP"
            
            doctl compute domain records create "$DOMAIN" \
                --record-type A \
                --record-name "www" \
                --record-data "$LB_IP"
            
            doctl compute domain records create "$DOMAIN" \
                --record-type A \
                --record-name "api" \
                --record-data "$LB_IP"
            
            doctl compute domain records create "$DOMAIN" \
                --record-type A \
                --record-name "app" \
                --record-data "$LB_IP"
            ;;
    esac
    
    log "DNS and load balancer configured: $DOMAIN -> $LB_IP"
}

# Generate SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    PRIMARY_IP=$(cat .instance_info | grep PRIMARY_IP | cut -d= -f2)
    SSH_KEY_FILE=$(cat .ssh_key_file)
    
    # Create certificates directory
    mkdir -p certs
    
    # Generate self-signed certificate for initial setup
    # In production, use Let's Encrypt or your CA
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout certs/unisonos.org.key \
        -out certs/unisonos.org.crt \
        -subj "/C=US/ST=California/L=San Francisco/O=Unison/OU=Platform/CN=$DOMAIN"
    
    # Copy certificates to primary instance
    scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no \
        certs/unisonos.org.crt certs/unisonos.org.key \
        root@"$PRIMARY_IP":/etc/nginx/certs/
    
    log "SSL certificates generated and installed"
}

# Deploy application
deploy_application() {
    log "Deploying Unison Platform application..."
    
    PRIMARY_IP=$(cat .instance_info | grep PRIMARY_IP | cut -d= -f2)
    SSH_KEY_FILE=$(cat .ssh_key_file)
    
    # Copy application files to primary instance
    scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no \
        -r . root@"$PRIMARY_IP":/opt/unison/
    
    # SSH into primary instance and deploy
    ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no root@"$PRIMARY_IP" << 'EOF'
cd /opt/unison

# Setup environment file
cp .env.prod.template .env.prod

# Generate secrets
mkdir -p secrets
openssl rand -base64 32 > secrets/db_password.txt
openssl rand -base64 32 > secrets/redis_password.txt
openssl rand -base64 64 > secrets/jwt_signing_key.txt
openssl rand -base64 16 > secrets/admin_password.txt
chmod 600 secrets/*

# Update environment file with database credentials
source .db_credentials
sed -i "s/DB_HOST=.*/DB_HOST=$DB_HOST/" .env.prod
sed -i "s/DB_PORT=.*/DB_PORT=$DB_PORT/" .env.prod
sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" .env.prod

# Run security setup
chmod +x scripts/security-setup.sh
./scripts/security-setup.sh

# Deploy services
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
sleep 60

# Run health checks
./scripts/health-check.sh
EOF
    
    log "Application deployed successfully"
}

# Run verification tests
verify_deployment() {
    log "Running deployment verification..."
    
    DOMAIN=${DOMAIN:-"unisonos.org"}
    
    # Test health endpoint
    if curl -f -s "https://$DOMAIN/health" >/dev/null; then
        log "Health check passed"
    else
        error "Health check failed"
    fi
    
    # Test identity service
    if curl -f -s "https://$DOMAIN/identity/health" >/dev/null; then
        log "Identity service health check passed"
    else
        error "Identity service health check failed"
    fi
    
    # Test consent service
    if curl -f -s "https://$DOMAIN/consent/health" >/dev/null; then
        log "Consent service health check passed"
    else
        error "Consent service health check failed"
    fi
    
    # Test connector broker
    if curl -f -s "https://$DOMAIN/connectors/health" >/dev/null; then
        log "Connector broker health check passed"
    else
        error "Connector broker health check failed"
    fi
    
    # Test MCP proxy
    if curl -f -s "https://$DOMAIN/mcp/health" >/dev/null; then
        log "MCP proxy health check passed"
    else
        error "MCP proxy health check failed"
    fi
    
    log "All verification tests passed"
}

# Cleanup temporary files
cleanup() {
    log "Cleaning up temporary files..."
    
    rm -f user-data.sh
    rm -f .db_credentials
    rm -f .instance_info
    rm -f .ssh_key_name
    rm -f .ssh_key_file
    
    log "Cleanup completed"
}

# Main execution
main() {
    log "Starting Unison Platform infrastructure setup..."
    
    check_prerequisites
    create_ssh_key
    provision_database
    provision_instances
    setup_networking
    setup_ssl
    deploy_application
    verify_deployment
    cleanup
    
    log "Infrastructure setup completed successfully!"
    log ""
    log "Your Unison Platform is now live at: https://$DOMAIN"
    log "Admin interface: https://admin.$DOMAIN"
    log "API documentation: https://$DOMAIN/docs"
    log ""
    log "Next steps:"
    log "1. Configure external service integrations (PayPal, Figma, Venmo)"
    log "2. Set up monitoring and alerting"
    log "3. Configure backup procedures"
    log "4. Test user onboarding flows"
}

# Run main function
main "$@"
