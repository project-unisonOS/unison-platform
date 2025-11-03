#!/bin/bash
# Unison Platform - Image Pinning Script
# Pins exact image digests for reproducible deployments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="compose/compose.yaml"
LOCK_FILE="artifacts.lock"
REGISTRY="ghcr.io/project-unisonos"

echo -e "${BLUE}📌 Unison Platform - Image Pinning${NC}"
echo -e "${BLUE}=====================================${NC}"

# List of all Unison services
SERVICES=(
    "unison-auth"
    "unison-context"
    "unison-policy"
    "unison-orchestrator"
    "unison-intent-graph"
    "unison-context-graph"
    "unison-experience-renderer"
    "unison-agent-vdi"
    "unison-io-speech"
    "unison-io-vision"
    "unison-io-core"
    "unison-inference"
    "unison-storage"
)

# Function to get image digest
get_image_digest() {
    local image_name=$1
    local tag=${2:-"main"}
    
    echo -e "${YELLOW}🔍 Getting digest for ${image_name}:${tag}${NC}"
    
    # Use docker buildx imagetools to get the digest
    local digest
    digest=$(docker buildx imagetools inspect "${REGISTRY}/${image_name}:${tag}" --format '{{.Manifest.Digest}}' 2>/dev/null || echo "")
    
    if [[ -z "$digest" ]]; then
        echo -e "${RED}❌ Failed to get digest for ${image_name}:${tag}${NC}"
        return 1
    fi
    
    echo "$digest"
}

# Function to verify image exists
verify_image() {
    local image_name=$1
    local tag=${2:-"main"}
    
    echo -e "${YELLOW}🔍 Verifying ${image_name}:${tag} exists${NC}"
    
    if ! docker buildx imagetools inspect "${REGISTRY}/${image_name}:${tag}" >/dev/null 2>&1; then
        echo -e "${RED}❌ Image ${image_name}:${tag} not found${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Image ${image_name}:${tag} verified${NC}"
}

# Function to create backup of existing lock file
backup_lock_file() {
    if [[ -f "$LOCK_FILE" ]]; then
        local backup_file="${LOCK_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$LOCK_FILE" "$backup_file"
        echo -e "${BLUE}📋 Backed up existing lock file to ${backup_file}${NC}"
    fi
}

# Function to generate artifacts.lock
generate_lock_file() {
    echo -e "${BLUE}🔨 Generating ${LOCK_FILE}${NC}"
    
    # Create lock file header
    cat > "$LOCK_FILE" << EOF
# Unison Platform - Artifacts Lock File
# Generated on $(date)
# This file contains pinned image digests for reproducible deployments

[images]
EOF

    # Pin each service
    local failed_services=()
    
    for service in "${SERVICES[@]}"; do
        echo -e "${YELLOW}📌 Processing ${service}...${NC}"
        
        # Verify image exists first
        if verify_image "$service"; then
            # Get digest
            local digest
            digest=$(get_image_digest "$service")
            
            if [[ -n "$digest" ]]; then
                echo "${service} = \"${REGISTRY}/${service}@${digest}\"" >> "$LOCK_FILE"
                echo -e "${GREEN}✅ Pinned ${service} to ${digest:0:12}${NC}"
            else
                failed_services+=("$service")
            fi
        else
            failed_services+=("$service")
        fi
    done
    
    # Report failed services
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Failed to pin ${#failed_services[@]} services:${NC}"
        for service in "${failed_services[@]}"; do
            echo -e "${RED}   • ${service}${NC}"
        done
        return 1
    fi
    
    echo -e "${GREEN}✅ Successfully pinned all services${NC}"
}

# Function to validate lock file
validate_lock_file() {
    echo -e "${BLUE}🔍 Validating ${LOCK_FILE}${NC}"
    
    if [[ ! -f "$LOCK_FILE" ]]; then
        echo -e "${RED}❌ Lock file not found${NC}"
        return 1
    fi
    
    # Check if all services are present
    local missing_services=()
    
    for service in "${SERVICES[@]}"; do
        if ! grep -q "^${service} = " "$LOCK_FILE"; then
            missing_services+=("$service")
        fi
    done
    
    if [[ ${#missing_services[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Missing services in lock file:${NC}"
        for service in "${missing_services[@]}"; do
            echo -e "${RED}   • ${service}${NC}"
        done
        return 1
    fi
    
    # Verify all pinned images exist
    local invalid_images=()
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^([a-zA-Z0-9-]+)\s*=\s*\"([^\"]+)\" ]]; then
            local image="${BASH_REMATCH[2]}"
            if ! docker buildx imagetools inspect "$image" >/dev/null 2>&1; then
                invalid_images+=("$image")
            fi
        fi
    done < <(grep -v '^#' "$LOCK_FILE" | grep -v '^$')
    
    if [[ ${#invalid_images[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Invalid images in lock file:${NC}"
        for image in "${invalid_images[@]}"; do
            echo -e "${RED}   • ${image}${NC}"
        done
        return 1
    fi
    
    echo -e "${GREEN}✅ Lock file validation passed${NC}"
}

# Function to show lock file summary
show_summary() {
    echo -e "${BLUE}📊 Lock File Summary${NC}"
    echo -e "${BLUE}===================${NC}"
    
    local total_services=${#SERVICES[@]}
    local pinned_services=0
    
    if [[ -f "$LOCK_FILE" ]]; then
        pinned_services=$(grep -c '^unison-' "$LOCK_FILE" || echo "0")
    fi
    
    echo "Total services: $total_services"
    echo "Pinned services: $pinned_services"
    echo "Lock file: $LOCK_FILE"
    
    if [[ -f "$LOCK_FILE" ]]; then
        echo -e "\n${YELLOW}Pinned Images:${NC}"
        while IFS= read -r line; do
            if [[ "$line" =~ ^([a-zA-Z0-9-]+)\s*=\s*\"([^\"]+)\" ]]; then
                local service="${BASH_REMATCH[1]}"
                local image="${BASH_REMATCH[2]}"
                local digest=$(echo "$image" | cut -d'@' -f2)
                echo -e "  ${GREEN}✅${NC} ${service}: ${digest:0:12}"
            fi
        done < <(grep -v '^#' "$LOCK_FILE" | grep -v '^$')
    fi
}

# Function to update compose file to use pinned images
update_compose_file() {
    echo -e "${BLUE}🔄 Updating compose file to use pinned images${NC}"
    
    if [[ ! -f "$LOCK_FILE" ]]; then
        echo -e "${RED}❌ Lock file not found${NC}"
        return 1
    fi
    
    # Create compose file with pinned images
    local pinned_compose="compose/compose.pinned.yaml"
    
    cp "$COMPOSE_FILE" "$pinned_compose"
    
    # Replace image references with pinned versions
    while IFS= read -r line; do
        if [[ "$line" =~ ^([a-zA-Z0-9-]+)\s*=\s*\"([^\"]+)\" ]]; then
            local service="${BASH_REMATCH[1]}"
            local pinned_image="${BASH_REMATCH[2]}"
            
            # Extract service name from image name (remove unison- prefix)
            local service_name=$(echo "$service" | sed 's/^unison-//')
            
            # Replace image in compose file
            sed -i.bak "s|image: ${REGISTRY}/${service}:main|image: ${pinned_image}|g" "$pinned_compose"
            sed -i.bak "s|image: ${REGISTRY}/${service}:latest|image: ${pinned_image}|g" "$pinned_compose"
        fi
    done < <(grep -v '^#' "$LOCK_FILE" | grep -v '^$')
    
    rm -f "${pinned_compose}.bak"
    
    echo -e "${GREEN}✅ Created pinned compose file: ${pinned_compose}${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Starting image pinning process...${NC}"
    
    # Check dependencies
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
        exit 1
    fi
    
    if ! docker buildx version >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker buildx not available. Please install Docker buildx.${NC}"
        exit 1
    fi
    
    # Check if we're logged in to the registry
    if ! docker buildx imagetools inspect "${REGISTRY}/unison-auth:main" >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Not logged in to registry. Some images might not be accessible.${NC}"
    fi
    
    # Backup existing lock file
    backup_lock_file
    
    # Generate new lock file
    if generate_lock_file; then
        echo -e "${GREEN}✅ Lock file generated successfully${NC}"
    else
        echo -e "${RED}❌ Failed to generate lock file${NC}"
        exit 1
    fi
    
    # Validate lock file
    if validate_lock_file; then
        echo -e "${GREEN}✅ Lock file validation passed${NC}"
    else
        echo -e "${RED}❌ Lock file validation failed${NC}"
        exit 1
    fi
    
    # Update compose file
    update_compose_file
    
    # Show summary
    show_summary
    
    echo -e "\n${GREEN}🎉 Image pinning completed successfully!${NC}"
    echo -e "${BLUE}📋 Next steps:${NC}"
    echo -e "   • Use 'compose/compose.pinned.yaml' for reproducible deployments"
    echo -e "   • Commit '${LOCK_FILE}' to version control"
    echo -e "   • Update CI/CD to use pinned images"
}

# Handle command line arguments
case "${1:-}" in
    "validate")
        validate_lock_file
        show_summary
        ;;
    "summary")
        show_summary
        ;;
    "update-compose")
        update_compose_file
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (none)       Generate new lock file"
        echo "  validate      Validate existing lock file"
        echo "  summary       Show lock file summary"
        echo "  update-compose  Update compose file with pinned images"
        echo "  help          Show this help message"
        ;;
    *)
        main
        ;;
esac
