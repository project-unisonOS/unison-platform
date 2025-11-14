# Unison Deployment Guide

**Choose the right deployment method for your use case**

---

## 🎯 Deployment Decision Tree

```
┌─────────────────────────────────────────────────────────────┐
│         What are you trying to accomplish?                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  Development / Testing / Cloud?       │
        └───────────────────────────────────────┘
                    │                   │
                    │ YES               │ NO
                    ▼                   ▼
        ┌─────────────────┐   ┌─────────────────────┐
        │ Docker Compose  │   │ End User / Edge?    │
        │ Deployment      │   └─────────────────────┘
        └─────────────────┘            │
                                       │ YES
                                       ▼
                            ┌─────────────────────┐
                            │ Native Ubuntu       │
                            │ Installation        │
                            └─────────────────────┘
```

---

## 🐳 Docker Compose Deployment

### Best For

- **Development teams** building on Unison
- **Cloud deployments** (AWS, GCP, Azure)
- **CI/CD pipelines** and automated testing
- **Multi-service testing** and integration
- **Quick prototyping** and experimentation

### Pros

✅ **Isolated environments** - No system-level changes  
✅ **Easy cleanup** - `make down` removes everything  
✅ **Reproducible** - Same environment everywhere  
✅ **Observability included** - Jaeger, Prometheus, Grafana  
✅ **Version pinning** - Exact image versions locked  
✅ **Fast iteration** - Rebuild and restart quickly

### Cons

❌ **Requires Docker** - Additional dependency  
❌ **Higher resource usage** - Container overhead  
❌ **Container networking** - Extra network layer  
❌ **Audio complexity** - Harder to access host audio

### Quick Start

```bash
cd unison-platform
make up
make health
```

### Documentation

- [Docker Compose README](../../README.md)
- [Development Guide](../development/)
- [Observability Setup](../observability/)

---

## 🖥️ Native Ubuntu Installation

### Best For

- **End users** running personal assistants
- **Edge devices** (Raspberry Pi, NUC, etc.)
- **Production workstations** with Ubuntu
- **Direct hardware access** (audio, sensors)
- **Low-latency applications** requiring native performance

### Pros

✅ **Native performance** - No container overhead  
✅ **System integration** - Direct audio/hardware access  
✅ **Lower resource usage** - Runs on lighter hardware  
✅ **Boot-on-startup** - Systemd integration  
✅ **Simple management** - `unisonctl` CLI tool  
✅ **Production-ready** - Designed for long-running use

### Cons

❌ **Ubuntu-specific** - Only works on Ubuntu 22.04/24.04  
❌ **System-level changes** - Installs packages, creates users  
❌ **Harder to clean up** - Requires uninstall script  
❌ **Single environment** - Can't run multiple versions

### Quick Start

```bash
# One-command installation
curl -sSL https://install.unison.ai | sudo bash

# Or from source
cd unison-platform
sudo make install-native
sudo unisonctl start
```

### Documentation

- [Native Ubuntu Installation Guide](ubuntu-native.md)
- [unisonctl Reference](../reference/unisonctl.md)
- [Troubleshooting](../troubleshooting/)

---

## 📊 Comparison Matrix

| Feature | Docker Compose | Native Ubuntu |
|---------|----------------|---------------|
| **Setup Time** | 5 minutes | 10-15 minutes |
| **Resource Usage** | High (2-4GB RAM) | Low (1-2GB RAM) |
| **Performance** | Good | Excellent |
| **Audio Access** | Complex | Direct |
| **Cleanup** | Easy (`make down`) | Manual uninstall |
| **Multi-version** | ✅ Yes | ❌ No |
| **Production Ready** | ✅ Yes | ✅ Yes |
| **Observability** | ✅ Built-in | ⚠️ Manual setup |
| **Boot on Startup** | ⚠️ Manual | ✅ Systemd |
| **Platform Support** | Linux/Mac/Windows | Ubuntu only |

---

## 🎯 Use Case Examples

### Development Team

**Scenario**: Building a new skill for Unison  
**Recommendation**: **Docker Compose**  
**Why**: Easy to iterate, built-in observability, reproducible environment

```bash
make dev
# Make changes
make restart-service SERVICE=orchestrator
make logs-service SERVICE=orchestrator
```

---

### Personal Assistant

**Scenario**: Running Unison as a home assistant  
**Recommendation**: **Native Ubuntu**  
**Why**: Direct audio access, low resource usage, boots on startup

```bash
sudo make install-native
sudo unisonctl enable  # Start on boot
sudo unisonctl test audio
```

---

### Edge Device (Raspberry Pi)

**Scenario**: Unison on Raspberry Pi 4 (4GB RAM)  
**Recommendation**: **Native Ubuntu**  
**Why**: Limited resources, need native performance

```bash
# On Ubuntu Server 22.04 ARM64
sudo make install-native
sudo unisonctl start
```

---

### Cloud Deployment (AWS/GCP/Azure)

**Scenario**: Deploying Unison to cloud VMs  
**Recommendation**: **Docker Compose** (or Kubernetes for scale)  
**Why**: Container orchestration, easy scaling, cloud-native

```bash
# On cloud VM
make up ENV=prod
make pin  # Lock versions
```

---

### CI/CD Pipeline

**Scenario**: Automated testing in GitHub Actions  
**Recommendation**: **Docker Compose**  
**Why**: Isolated environments, easy cleanup, reproducible

```yaml
- name: Start Unison Stack
  run: make up
- name: Run Tests
  run: make test-int
- name: Cleanup
  run: make down
```

---

## 🔄 Migration Between Deployments

### Docker → Native Ubuntu

```bash
# 1. Export data from Docker
make backup

# 2. Stop Docker stack
make down

# 3. Install native
sudo make install-native

# 4. Import data (if needed)
# Manual data migration steps...

# 5. Start native services
sudo unisonctl start
```

### Native Ubuntu → Docker

```bash
# 1. Stop native services
sudo unisonctl stop
sudo unisonctl disable

# 2. Backup data
sudo cp -r /var/lib/unison /backup/

# 3. Start Docker stack
make up

# 4. Import data (if needed)
# Manual data migration steps...
```

---

## 🆘 Getting Help

### Docker Deployment Issues

- Check logs: `make logs`
- Check health: `make health`
- Clean restart: `make clean && make up`
- [Docker Troubleshooting Guide](../troubleshooting/docker.md)

### Native Ubuntu Issues

- Check status: `sudo unisonctl status`
- View logs: `sudo unisonctl logs`
- Test audio: `sudo unisonctl test audio`
- [Native Troubleshooting Guide](../troubleshooting/native.md)

---

## 📚 Additional Resources

- [Architecture Overview](../architecture/)
- [Service Specifications](../specs/)
- [API Reference](../api/)
- [Security Best Practices](../security/)
- [Performance Tuning](../performance/)

---

**Still not sure?** Open a [discussion](https://github.com/project-unisonos/unison-platform/discussions) and we'll help you choose!
