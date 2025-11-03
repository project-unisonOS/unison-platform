# Unison Platform

> **Enterprise-grade intent orchestration platform with one-command deployment and unified developer experience**

## 🎯 Overview

The Unison Platform transforms a distributed microservices architecture into a cohesive, manageable system while maintaining development autonomy. It provides **hard interfaces**, **one-click orchestration**, and **consistent CI/CD** across all services.

### 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Unison Platform                          │
├─────────────────────────────────────────────────────────────┤
│  Core Domain        │  I/O Domain    │  Skills+Inference  │
│  ┌─────────────┐    │ ┌────────────┐ │ ┌────────────────┐ │
│  │ Orchestrator│    │ │ Speech     │ │ │ Inference      │ │
│  │ Context     │    │ │ Vision     │ │ │ Skills         │ │
│  │ Policy      │    │ │ Core       │ │ │                │ │
│  │ Auth        │    │ │            │ │ │                │ │
│  └─────────────┘    │ └────────────┘ │ └────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│              Intent Orchestration Layer                     │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐       │
│  │Intent Graph │ │Context Graph│ │Experience Rendr│       │
│  │             │ │             │ │                │       │
│  │             │ │             │ │                │       │
│  └─────────────┘ └─────────────┘ └────────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                Infrastructure Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐       │
│  │ Storage     │ │ Agent VDI   │ │ Redis/Postgres │       │
│  │             │ │             │ │                │       │
│  │             │ │             │ │                │       │
│  └─────────────┘ └─────────────┘ └────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (or Docker Engine with Compose)
- **Make** (for command shortcuts)
- **Git** (for version control)

### One-Command Setup

```bash
# Clone the platform repository
git clone https://github.com/project-unisonos/unison-platform.git
cd unison-platform

# Configure environment
cp .env.template .env
# Edit .env with your configuration

# Start the entire stack
make up

# Verify everything is working
make health
```

That's it! 🎉 The entire Unison platform is now running with all services interconnected.

## 📋 Service Endpoints

Once started, all services are available at:

| Service | Endpoint | Description |
|---------|----------|-------------|
| **Orchestrator** | http://localhost:8090 | Main intent orchestration |
| **Intent Graph** | http://localhost:8080 | Intent processing & decomposition |
| **Context Graph** | http://localhost:8091 | Context fusion & management |
| **Experience Renderer** | http://localhost:8092 | Adaptive interface generation |
| **Agent VDI** | http://localhost:8093 | Virtual display interface |
| **Auth Service** | http://localhost:8083 | Authentication & authorization |
| **Context Service** | http://localhost:8081 | Context management |
| **Policy Service** | http://localhost:8083 | Policy enforcement |
| **I/O Speech** | http://localhost:8084 | Speech processing |
| **I/O Vision** | http://localhost:8086 | Vision processing |
| **I/O Core** | http://localhost:8085 | I/O coordination |
| **Inference** | http://localhost:8087 | ML inference gateway |
| **Storage** | http://localhost:8082 | Data persistence |

## 🛠️ Developer Experience

### Essential Commands

```bash
# Start development environment
make dev

# View logs from all services
make logs

# Check service health
make health

# Run integration tests
make test-int

# Stop everything
make down

# Clean up resources
make clean
```

### Advanced Commands

```bash
# Start with observability stack
make observability

# Pin exact image versions for reproducible deployments
make pin

# Validate service contracts
make validate

# Run security scans
make security-scan

# Generate documentation
make docs
```

### Service Management

```bash
# Restart specific service
make restart-service SERVICE=orchestrator

# View logs for specific service
make logs-service SERVICE=intent-graph

# Get shell in service container
make shell SERVICE=context-graph

# Execute command in service
make exec SERVICE=auth CMD="env | grep SERVICE"
```

## 🏗️ Platform Architecture

### Domain Organization

The platform is organized into four clear domains to reduce cognitive load:

#### **Core Domain** (`core/`)
- **Orchestrator**: Central coordination and workflow management
- **Context**: User context and session management  
- **Policy**: Business rules and compliance enforcement
- **Auth**: Authentication, authorization, and identity management

#### **I/O Domain** (`io/`)
- **Speech**: Voice processing and synthesis
- **Vision**: Image and video analysis
- **Core**: I/O coordination and protocol management

#### **Skills+Inference Domain** (`skills/`)
- **Inference**: ML model inference gateway
- **Skills**: Domain-specific skill implementations

#### **Infrastructure Domain** (`infra/`)
- **Storage**: Data persistence and retrieval
- **Agent VDI**: Virtual display for legacy software
- **Gateway**: API gateway and load balancing
- **Observability**: Monitoring, tracing, and metrics

### Service Communication

All services communicate through standardized interfaces:

- **HTTP/REST**: Synchronous request/response
- **NATS/JetStream**: Asynchronous event streaming
- **EventEnvelope**: Universal event schema
- **mTLS + JWT**: Secure service-to-service communication

## 🔧 Configuration

### Environment Variables

The platform uses **Twelve-Factor App** principles:

```bash
# Core configuration
UNISON_ENV=development
LOG_LEVEL=info

# Database
POSTGRES_HOST=postgres
POSTGRES_DB=unison
POSTGRES_USER=unison
POSTGRES_PASSWORD=unison_password

# Cache & Messaging
REDIS_HOST=redis
NATS_HOST=nats

# Service-specific
ORCHESTRATOR_PORT=8090
INTENT_GRAPH_PORT=8080
CONTEXT_GRAPH_PORT=8091
```

### Service Contracts

All services implement the **ServiceContract** interface:

```python
class ServiceContract(ABC):
    @abstractmethod
    async def health(self) -> HealthResponse:
        """Return service health status"""
        pass
    
    @abstractmethod
    async def handle_event(self, envelope: EventEnvelope) -> EventEnvelope:
        """Handle incoming events"""
        pass
    
    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """Return service metadata"""
        pass
```

## 🧪 Testing

### Test Structure

```
tests/
├── unit/              # Unit tests for platform components
├── integration/       # Cross-service integration tests
├── contracts/         # Provider/consumer contract tests
└── e2e/              # End-to-end scenario tests
```

### Running Tests

```bash
# Run all tests
make full-test

# Unit tests only
make test-unit

# Integration tests
make test-int

# Contract compliance
make validate
```

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Service interaction testing
3. **Contract Tests**: API contract compliance
4. **End-to-End Tests**: Complete user workflows

## 📊 Observability

### Built-in Monitoring

The platform includes comprehensive observability:

```bash
# Start with monitoring stack
make observability

# Access dashboards
# Jaeger: http://localhost:16686
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

### Telemetry Stack

- **Traces**: Jaeger distributed tracing
- **Metrics**: Prometheus + Grafana dashboards
- **Logs**: Structured JSON logging with correlation IDs
- **Health Checks**: Comprehensive service health monitoring

### OpenTelemetry Integration

All services include OpenTelemetry instrumentation:

```python
from unison_spec.telemetry import setup_telemetry

tracer, meter, logger = setup_telemetry(
    service_name="unison-intent-graph",
    service_version="1.0.0"
)
```

## 🔒 Security

### Security Baseline

- **Container Security**: Non-root users, read-only filesystems, seccomp profiles
- **Supply Chain**: SBOM generation, provenance attestations, SLSA compliance
- **Runtime**: mTLS, JWT authentication, secret management
- **Network**: Service mesh, zero-trust networking

### Security Scanning

```bash
# Run security vulnerability scan
make security-scan

# Check for exposed secrets
make audit-secrets

# Verify compliance
make compliance-check
```

## 🚀 Deployment

### Development

```bash
# Local development
make dev

# With observability
make observability
```

### Production

```bash
# Production deployment
make deploy-prod

# Using pinned versions
docker compose -f compose/compose.pinned.yaml up -d
```

### Release Process

1. **Service Updates**: Individual services update and push images
2. **Version Pinning**: `make pin` locks exact image digests
3. **Integration Testing**: Full stack validation
4. **Release Bundle**: Generated compose files and artifacts
5. **Deployment**: Reproducible deployment with pinned versions

## 📚 Documentation

### Architecture Documentation

- **[API Reference](docs/api/)**: Complete API documentation
- **[Service Specs](docs/specs/)**: Service specifications and contracts
- **[Deployment Guide](docs/deployment/)**: Production deployment guide
- **[Development Guide](docs/development/)**: Development setup and workflows

### Code Documentation

All services include comprehensive documentation:

- **OpenAPI Specs**: Auto-generated API documentation
- **Inline Documentation**: Code-level documentation and examples
- **Architecture Decision Records**: Design decisions and rationale

## 🤝 Contributing

### Development Workflow

1. **Fork** the platform repository
2. **Create** feature branch
3. **Set up** development environment: `make dev`
4. **Make changes** with tests
5. **Validate** contracts: `make validate`
6. **Submit** pull request

### Service Development

When adding new services:

1. **Create** service repository following the template
2. **Implement** ServiceContract interface
3. **Add** reusable CI workflow
4. **Update** platform compose configuration
5. **Add** integration tests
6. **Update** documentation

### Code Standards

- **Python**: Black formatting, mypy typing, flake8 linting
- **Docker**: Multi-stage builds, security baselines
- **API**: OpenAPI 3.0 specifications
- **Documentation**: Comprehensive inline docs

## 🆘 Troubleshooting

### Common Issues

#### Services Not Starting

```bash
# Check service status
make status

# View logs
make logs

# Check health
make health
```

#### Port Conflicts

```bash
# Check what's using ports
netstat -tulpn | grep :808

# Clean up Docker resources
make clean
```

#### Performance Issues

```bash
# Check system resources
make metrics

# Monitor Docker stats
docker stats
```

### Getting Help

- **[Issues](https://github.com/project-unisonos/unison-platform/issues)**: Bug reports and feature requests
- **[Discussions](https://github.com/project-unisonos/unison-platform/discussions)**: Community discussions
- **[Documentation](docs/)**: Comprehensive documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Unison Community**: Contributors and maintainers
- **Open Source Projects**: Dependencies and tools
- **Cloud Native Computing Foundation**: Cloud-native patterns and practices

---

**Built with ❤️ by the Unison community**

For more information, visit [project-unisonos.org](https://project-unisonos.org)
