# Unison Platform - Developer Experience Makefile
# Provides one-command orchestration for the entire Unison stack

.PHONY: help up down logs test-int pin clean status observability dev prod

# Default environment
ENV ?= dev
PROFILE ?= $(ENV)

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Unison Platform - Developer Commands$(RESET)"
	@echo "$(BLUE)=========================================$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

up: ## Start the Unison stack
	@echo "$(BLUE)🚀 Starting Unison platform ($(ENV))...$(RESET)"
	@mkdir -p logs
	@docker compose --profile $(PROFILE) up -d --wait
	@echo "$(GREEN)✅ Stack is ready!$(RESET)"
	@echo "$(YELLOW)📋 Service Endpoints:$(RESET)"
	@echo "   • Orchestrator:     http://localhost:8090/health"
	@echo "   • Intent Graph:     http://localhost:8080/health"
	@echo "   • Context Graph:    http://localhost:8091/health"
	@echo "   • Experience Rendr: http://localhost:8092/health"
	@echo "   • Agent VDI:        http://localhost:8093/health"
	@echo "   • Auth Service:     http://localhost:8083/health"
	@echo "   • Context Service:  http://localhost:8081/health"
	@echo "   • Policy Service:   http://localhost:8083/health"
	@echo "   • I/O Speech:       http://localhost:8084/health"
	@echo "   • I/O Vision:       http://localhost:8086/health"
	@echo "   • I/O Core:         http://localhost:8085/health"
	@echo "   • Inference:        http://localhost:8087/health"
	@echo "   • Storage:          http://localhost:8082/health"
	@if [ "$(PROFILE)" = "observability" ]; then \
		echo "$(YELLOW)📊 Observability:$(RESET)"; \
		echo "   • Jaeger:           http://localhost:16686"; \
		echo "   • Prometheus:       http://localhost:9090"; \
		echo "   • Grafana:          http://localhost:3000 (admin/admin)"; \
	fi

down: ## Stop the Unison stack
	@echo "$(BLUE)🛑 Stopping Unison platform...$(RESET)"
	@docker compose --profile $(PROFILE) down -v --remove-orphans
	@echo "$(GREEN)✅ Stack stopped$(RESET)"

logs: ## Show logs from all services
	@echo "$(BLUE)📋 Streaming logs from all services...$(RESET)"
	@docker compose --profile $(PROFILE) logs -f --tail=200

logs-service: ## Show logs for a specific service (usage: make logs-service SERVICE=orchestrator)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)❌ Please specify a service: make logs-service SERVICE=orchestrator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)📋 Streaming logs from $(SERVICE)...$(RESET)"
	@docker compose --profile $(PROFILE) logs -f --tail=100 $(SERVICE)

status: ## Show status of all services
	@echo "$(BLUE)📊 Service Status:$(RESET)"
	@docker compose --profile $(PROFILE) ps

test-int: ## Run integration tests
	@echo "$(BLUE)🧪 Running integration tests...$(RESET)"
	@docker compose --profile $(PROFILE) up -d --wait
	@sleep 10  # Wait for services to be fully ready
	@python -m pytest tests/integration/ -v --tb=short --color=yes
	@echo "$(GREEN)✅ Integration tests completed$(RESET)"

test-unit: ## Run unit tests for platform
	@echo "$(BLUE)🧪 Running platform unit tests...$(RESET)"
	@python -m pytest tests/unit/ -v --tb=short --color=yes
	@echo "$(GREEN)✅ Unit tests completed$(RESET)"

pin: ## Pin exact image versions to artifacts.lock
	@echo "$(BLUE)📌 Pinning image versions...$(RESET)"
	@./scripts/pin-images.sh
	@echo "$(GREEN)✅ Image versions pinned to artifacts.lock$(RESET)"

validate: ## Validate service contracts and dependencies
	@echo "$(BLUE)🔍 Validating service contracts...$(RESET)"
	@./scripts/validate-contracts.sh
	@echo "$(GREEN)✅ Contracts validated$(RESET)"

clean: ## Clean up Docker resources and caches
	@echo "$(BLUE)🧹 Cleaning up Docker resources...$(RESET)"
	@docker compose --profile $(PROFILE) down -v --remove-orphans
	@docker system prune -f
	@docker volume prune -f
	@docker network prune -f
	@echo "$(GREEN)✅ Cleanup completed$(RESET)"

dev: ## Development setup (start stack + logs)
	@echo "$(BLUE)🔧 Starting development environment...$(RESET)"
	@make up ENV=dev
	@make logs

prod: ## Production setup (start stack without logs)
	@echo "$(BLUE)🏭 Starting production environment...$(RESET)"
	@make up ENV=prod

observability: ## Start stack with observability tools
	@echo "$(BLUE)📊 Starting stack with observability...$(RESET)"
	@make up ENV=observability

health: ## Check health of all services
	@echo "$(BLUE)🏥 Checking service health...$(RESET)"
	@./scripts/health-check.sh
	@echo "$(GREEN)✅ Health check completed$(RESET)"

restart: ## Restart all services
	@echo "$(BLUE)🔄 Restarting services...$(RESET)"
	@docker compose --profile $(PROFILE) restart
	@echo "$(GREEN)✅ Services restarted$(RESET)"

restart-service: ## Restart a specific service (usage: make restart-service SERVICE=orchestrator)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)❌ Please specify a service: make restart-service SERVICE=orchestrator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🔄 Restarting $(SERVICE)...$(RESET)"
	@docker compose --profile $(PROFILE) restart $(SERVICE)
	@echo "$(GREEN)✅ $(SERVICE) restarted$(RESET)"

shell: ## Get shell in a service container (usage: make shell SERVICE=orchestrator)
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(RED)❌ Please specify a service: make shell SERVICE=orchestrator$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🐚 Opening shell in $(SERVICE)...$(RESET)"
	@docker compose --profile $(PROFILE) exec $(SERVICE) /bin/bash

exec: ## Execute command in a service (usage: make exec SERVICE=orchestrator CMD="ls -la")
	@if [ -z "$(SERVICE)" ] || [ -z "$(CMD)" ]; then \
		echo "$(RED)❌ Please specify service and command: make exec SERVICE=orchestrator CMD=\"ls -la\"$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)⚡ Executing in $(SERVICE): $(CMD)$(RESET)"
	@docker compose --profile $(PROFILE) exec $(SERVICE) sh -c "$(CMD)"

build: ## Build all services
	@echo "$(BLUE)🔨 Building all services...$(RESET)"
	@docker compose --profile $(PROFILE) build --parallel
	@echo "$(GREEN)✅ Build completed$(RESET)"

pull: ## Pull latest images
	@echo "$(BLUE)📥 Pulling latest images...$(RESET)"
	@docker compose --profile $(PROFILE) pull
	@echo "$(GREEN)✅ Images pulled$(RESET)"

update: ## Update stack (pull + up)
	@echo "$(BLUE)🔄 Updating stack...$(RESET)"
	@make pull
	@make up
	@echo "$(GREEN)✅ Stack updated$(RESET)"

backup: ## Backup all data volumes
	@echo "$(BLUE)💾 Creating backup...$(RESET)"
	@mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	@docker run --rm -v unison-devstack_postgres_data:/data -v $$PWD/backups/$(shell date +%Y%m%d_%H%M%S):/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
	@docker run --rm -v unison-devstack_redis_data:/data -v $$PWD/backups/$(shell date +%Y%m%d_%H%M%S):/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
	@echo "$(GREEN)✅ Backup created in backups/$(shell date +%Y%m%d_%H%M%S)$(RESET)"

restore: ## Restore from backup (usage: make restore BACKUP_DIR=20231103_120000)
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "$(RED)❌ Please specify backup directory: make restore BACKUP_DIR=20231103_120000$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🔄 Restoring from backup $(BACKUP_DIR)...$(RESET)"
	@docker compose --profile $(PROFILE) down -v
	@docker run --rm -v unison-devstack_postgres_data:/data -v $$PWD/backups/$(BACKUP_DIR):/backup alpine tar xzf /backup/postgres_data.tar.gz -C /data
	@docker run --rm -v unison-devstack_redis_data:/data -v $$PWD/backups/$(BACKUP_DIR):/backup alpine tar xzf /backup/redis_data.tar.gz -C /data
	@make up
	@echo "$(GREEN)✅ Restore completed$(RESET)"

migrate: ## Run database migrations
	@echo "$(BLUE)🔄 Running database migrations...$(RESET)"
	@./scripts/migrate.sh
	@echo "$(GREEN)✅ Migrations completed$(RESET)"

seed: ## Seed database with test data
	@echo "$(BLUE)🌱 Seeding database with test data...$(RESET)"
	@./scripts/seed-data.sh
	@echo "$(GREEN)✅ Data seeding completed$(RESET)"

benchmark: ## Run performance benchmarks
	@echo "$(BLUE)🏃 Running performance benchmarks...$(RESET)"
	@./scripts/benchmark.sh
	@echo "$(GREEN)✅ Benchmarks completed$(RESET)"

security-scan: ## Run security vulnerability scan
	@echo "$(BLUE)🔒 Running security scan...$(RESET)"
	@./scripts/security-scan.sh
	@echo "$(GREEN)✅ Security scan completed$(RESET)"

docs: ## Generate documentation
	@echo "$(BLUE)📚 Generating documentation...$(RESET)"
	@./scripts/generate-docs.sh
	@echo "$(GREEN)✅ Documentation generated$(RESET)"

# Development shortcuts
quick-test: test-unit ## Quick unit test run
full-test: test-unit test-int ## Full test suite
ci: validate test-unit test-int security-scan ## Full CI pipeline

# Production operations
deploy-prod: ## Deploy to production
	@echo "$(BLUE)🚀 Deploying to production...$(RESET)"
	@./scripts/deploy.sh prod
	@echo "$(GREEN)✅ Production deployment completed$(RESET)"

rollback: ## Rollback to previous version
	@echo "$(BLUE)🔄 Rolling back...$(RESET)"
	@./scripts/rollback.sh
	@echo "$(GREEN)✅ Rollback completed$(RESET)"

# Monitoring shortcuts
monitor: observability ## Start with monitoring
metrics: ## Show system metrics
	@echo "$(BLUE)📊 System Metrics:$(RESET)"
	@docker stats --no-stream

top: ## Show running processes
	@docker compose --profile $(PROFILE) top
