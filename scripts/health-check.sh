#!/bin/bash
# Unison Platform - Health Check Script
# Checks the health of all services in the platform

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service configuration
declare -A SERVICES=(
    ["auth"]="http://localhost:8083/health"
    ["context"]="http://localhost:8081/health"
    ["policy"]="http://localhost:8083/health"
    ["orchestrator"]="http://localhost:8090/health"
    ["intent-graph"]="http://localhost:8080/health"
    ["context-graph"]="http://localhost:8091/health"
    ["experience-renderer"]="http://localhost:8092/health"
    ["agent-vdi"]="http://localhost:8093/health"
    ["io-speech"]="http://localhost:8084/health"
    ["io-vision"]="http://localhost:8086/health"
    ["io-core"]="http://localhost:8085/health"
    ["inference"]="http://localhost:8087/health"
    ["storage"]="http://localhost:8082/health"
)

# Infrastructure services
declare -A INFRA=(
    ["redis"]="localhost:6379"
    ["postgres"]="localhost:5432"
    ["nats"]="localhost:4222"
)

echo -e "${BLUE}🏥 Unison Platform - Health Check${NC}"
echo -e "${BLUE}================================${NC}"

# Function to check HTTP service health
check_http_service() {
    local service_name=$1
    local health_url=$2
    local timeout=${3:-10}
    
    echo -e "${YELLOW}🔍 Checking ${service_name}...${NC}"
    
    # Use curl to check health endpoint
    local response
    local status_code
    
    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -w "\n%{http_code}" --max-time "$timeout" "$health_url" 2>/dev/null || echo "")
        status_code=$(echo "$response" | tail -n1)
        response_body=$(echo "$response" | head -n -1)
    else
        echo -e "${RED}❌ curl not available, skipping HTTP checks${NC}"
        return 1
    fi
    
    if [[ "$status_code" == "200" ]]; then
        # Try to parse JSON response
        if command -v jq >/dev/null 2>&1; then
            local status=$(echo "$response_body" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
            local version=$(echo "$response_body" | jq -r '.version // "unknown"' 2>/dev/null || echo "unknown")
            echo -e "${GREEN}✅ ${service_name}: Healthy (status: ${status}, version: ${version})${NC}"
        else
            echo -e "${GREEN}✅ ${service_name}: Healthy (HTTP 200)${NC}"
        fi
        return 0
    else
        echo -e "${RED}❌ ${service_name}: Unhealthy (HTTP ${status_code})${NC}"
        return 1
    fi
}

# Function to check TCP connectivity
check_tcp_service() {
    local service_name=$1
    local host_port=$2
    local timeout=${3:-5}
    
    echo -e "${YELLOW}🔍 Checking ${service_name}...${NC}"
    
    # Extract host and port
    local host=$(echo "$host_port" | cut -d':' -f1)
    local port=$(echo "$host_port" | cut -d':' -f2)
    
    # Use nc (netcat) or timeout with bash TCP socket
    if command -v nc >/dev/null 2>&1; then
        if nc -z -w"$timeout" "$host" "$port" 2>/dev/null; then
            echo -e "${GREEN}✅ ${service_name}: Connected${NC}"
            return 0
        else
            echo -e "${RED}❌ ${service_name}: Connection failed${NC}"
            return 1
        fi
    elif command -v timeout >/dev/null 2>&1; then
        if timeout "$timeout" bash -c "</dev/tcp/${host}/${port}" 2>/dev/null; then
            echo -e "${GREEN}✅ ${service_name}: Connected${NC}"
            return 0
        else
            echo -e "${RED}❌ ${service_name}: Connection failed${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  ${service_name}: Cannot check (nc/timeout not available)${NC}"
        return 2
    fi
}

# Function to check Docker containers
check_docker_containers() {
    echo -e "\n${BLUE}🐳 Docker Container Status${NC}"
    echo -e "${BLUE}========================${NC}"
    
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker not available${NC}"
        return 1
    fi
    
    # Get all Unison containers
    local containers
    containers=$(docker ps --filter "name=unison-devstack" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "")
    
    if [[ -z "$containers" ]]; then
        echo -e "${YELLOW}⚠️  No Unison containers found${NC}"
        return 1
    fi
    
    echo "$containers"
    
    # Check for unhealthy containers
    local unhealthy_count
    unhealthy_count=$(docker ps --filter "name=unison-devstack" --filter "status=unhealthy" --format "{{.Names}}" | wc -l || echo "0")
    
    if [[ "$unhealthy_count" -gt 0 ]]; then
        echo -e "\n${RED}❌ Found ${unhealthy_count} unhealthy containers${NC}"
        return 1
    fi
}

# Function to check system resources
check_system_resources() {
    echo -e "\n${BLUE}💻 System Resources${NC}"
    echo -e "${BLUE}==================${NC}"
    
    # Check disk space
    if command -v df >/dev/null 2>&1; then
        local disk_usage
        disk_usage=$(df -h / 2>/dev/null | tail -n1 | awk '{print $5}' || echo "N/A")
        echo -e "${BLUE}Disk Usage:${NC} ${disk_usage}"
        
        # Warn if disk usage is high
        local disk_percent
        disk_percent=$(echo "$disk_usage" | sed 's/%//' || echo "0")
        if [[ "$disk_percent" -gt 80 ]]; then
            echo -e "${YELLOW}⚠️  High disk usage detected${NC}"
        fi
    fi
    
    # Check memory
    if command -v free >/dev/null 2>&1; then
        local memory_usage
        memory_usage=$(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2}' 2>/dev/null || echo "N/A")
        echo -e "${BLUE}Memory Usage:${NC} ${memory_usage}"
    fi
    
    # Check Docker resources
    if command -v docker >/dev/null 2>&1; then
        local docker_stats
        docker_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -10 || echo "")
        if [[ -n "$docker_stats" ]]; then
            echo -e "\n${BLUE}Docker Resource Usage:${NC}"
            echo "$docker_stats"
        fi
    fi
}

# Function to generate health report
generate_health_report() {
    local healthy_services=0
    local unhealthy_services=0
    local total_services=${#SERVICES[@]}
    local healthy_infra=0
    local unhealthy_infra=0
    local total_infra=${#INFRA[@]}
    
    echo -e "\n${BLUE}📊 Health Report${NC}"
    echo -e "${BLUE}================${NC}"
    
    # Count service health
    for service in "${!SERVICES[@]}"; do
        if check_http_service "$service" "${SERVICES[$service]}" >/dev/null 2>&1; then
            ((healthy_services++))
        else
            ((unhealthy_services++))
        fi
    done
    
    # Count infrastructure health
    for infra in "${!INFRA[@]}"; do
        if check_tcp_service "$infra" "${INFRA[$infra]}" >/dev/null 2>&1; then
            ((healthy_infra++))
        else
            ((unhealthy_infra++))
        fi
    done
    
    echo -e "${BLUE}Services:${NC} ${healthy_services}/${total_services} healthy"
    echo -e "${BLUE}Infrastructure:${NC} ${healthy_infra}/${total_infra} healthy"
    
    local total_healthy=$((healthy_services + healthy_infra))
    local total_total=$((total_services + total_infra))
    local health_percentage=$((total_healthy * 100 / total_total))
    
    echo -e "${BLUE}Overall Health:${NC} ${health_percentage}%"
    
    if [[ "$health_percentage" -eq 100 ]]; then
        echo -e "${GREEN}🎉 All systems are healthy!${NC}"
        return 0
    elif [[ "$health_percentage" -ge 80 ]]; then
        echo -e "${YELLOW}⚠️  Most systems are healthy, but some issues detected${NC}"
        return 1
    else
        echo -e "${RED}❌ Significant health issues detected${NC}"
        return 2
    fi
}

# Function to show service details
show_service_details() {
    local service_name=$1
    local health_url=$2
    
    echo -e "\n${BLUE}🔍 Service Details: ${service_name}${NC}"
    echo -e "${BLUE}=============================${NC}"
    
    if command -v curl >/dev/null 2>&1; then
        local response
        response=$(curl -s "$health_url" 2>/dev/null || echo "")
        
        if [[ -n "$response" ]]; then
            if command -v jq >/dev/null 2>&1; then
                echo "$response" | jq '.' 2>/dev/null || echo "$response"
            else
                echo "$response"
            fi
        else
            echo -e "${RED}❌ No response from service${NC}"
        fi
    else
        echo -e "${RED}❌ curl not available for detailed checks${NC}"
    fi
}

# Main execution
main() {
    local detailed=${1:-false}
    local report_only=${2:-false}
    
    # Check infrastructure first
    echo -e "\n${BLUE}🏗️  Infrastructure Health${NC}"
    echo -e "${BLUE}========================${NC}"
    
    local infra_healthy=0
    local infra_total=${#INFRA[@]}
    
    for infra in "${!INFRA[@]}"; do
        if check_tcp_service "$infra" "${INFRA[$infra]}"; then
            ((infra_healthy++))
        fi
    done
    
    # Check application services
    echo -e "\n${BLUE}🚀 Application Services${NC}"
    echo -e "${BLUE}========================${NC}"
    
    local services_healthy=0
    local services_total=${#SERVICES[@]}
    
    for service in "${!SERVICES[@]}"; do
        if check_http_service "$service" "${SERVICES[$service]}"; then
            ((services_healthy++))
            
            # Show details if requested
            if [[ "$detailed" == "true" ]]; then
                show_service_details "$service" "${SERVICES[$service]}"
            fi
        fi
    done
    
    # Check Docker containers
    check_docker_containers
    
    # Check system resources
    check_system_resources
    
    # Generate report
    if [[ "$report_only" != "true" ]]; then
        generate_health_report
    fi
}

# Handle command line arguments
case "${1:-}" in
    "detailed"|"--detailed"|"-d")
        main true false
        ;;
    "report"|"--report"|"-r")
        main false true
        ;;
    "service"|"--service"|"-s")
        if [[ -z "${2:-}" ]]; then
            echo -e "${RED}❌ Please specify a service name${NC}"
            echo "Available services: ${!SERVICES[*]}"
            exit 1
        fi
        
        if [[ -n "${SERVICES[$2]:-}" ]]; then
            show_service_details "$2" "${SERVICES[$2]}"
        else
            echo -e "${RED}❌ Unknown service: $2${NC}"
            echo "Available services: ${!SERVICES[*]}"
            exit 1
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  (none)         Run basic health check"
        echo "  detailed       Show detailed service information"
        echo "  report         Generate health report only"
        echo "  service <name> Show details for specific service"
        echo "  help           Show this help message"
        echo ""
        echo "Available services: ${!SERVICES[*]}"
        echo "Available infrastructure: ${!INFRA[*]}"
        ;;
    *)
        main false false
        ;;
esac
