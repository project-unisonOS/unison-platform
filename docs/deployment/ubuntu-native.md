# Unison Ubuntu Installation Guide

Complete guide for installing and running Unison on Ubuntu 22.04 or 24.04.

---

## 📋 Prerequisites

### System Requirements

- **OS**: Ubuntu 22.04 LTS or 24.04 LTS
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk**: 10GB free space
- **CPU**: 2+ cores recommended
- **Audio**: Microphone and speakers/headphones

### Network Requirements

- Internet connection for initial installation
- Ports 8088, 8090, 7072 available (or configurable)

---

## 🚀 Quick Install

### One-Command Installation

```bash
curl -sSL https://install.unison.ai | sudo bash
```

Or download and run manually:

```bash
wget https://install.unison.ai/ubuntu_install.sh
chmod +x ubuntu_install.sh
sudo ./ubuntu_install.sh
```

### From Source

```bash
git clone https://github.com/project-unisonos/unison.git
cd unison
sudo ./scripts/ubuntu_install.sh
```

---

## 📦 What Gets Installed

The installation script will:

1. **System Dependencies**
   - Python 3.12
   - Docker and Docker Compose
   - Redis
   - PulseAudio and ALSA
   - FFmpeg

2. **Unison Components**
   - Orchestrator service
   - Authentication service
   - Consent service
   - Supporting infrastructure

3. **Configuration**
   - Systemd service units
   - Environment configuration
   - RSA keys for auth/consent
   - Audio permissions

4. **Tools**
   - `unisonctl` - Service management CLI
   - Audio testing scripts

---

## 🎯 Post-Installation

### 1. Start Services

```bash
sudo unisonctl start
```

### 2. Check Status

```bash
sudo unisonctl status
```

Expected output:
```
═══════════════════════════════════════════════════════════
                  Unison Service Status
═══════════════════════════════════════════════════════════

● unison-orchestrator: active
● unison-auth: active
● unison-consent: active

═══════════════════════════════════════════════════════════
```

### 3. Test Audio

```bash
sudo unisonctl test audio
```

This will:
- Test speaker output (you should hear a tone)
- Test microphone input (record and playback)
- Verify audio permissions

### 4. Health Check

```bash
sudo unisonctl health
```

All services should report as healthy.

---

## 🎤 Testing the System

### Echo Skill Test

Once services are running, test the echo skill:

1. Say: **"echo hello world"**
2. You should hear: **"hello world"**

### Manual API Test

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8088/token \
  -H "Content-Type: application/json" \
  -d '{"username":"test-user","password":"test-password"}' \
  | jq -r '.access_token')

# Test orchestrator
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8090/health
```

---

## 🛠️ Using unisonctl

### Service Management

```bash
# Start all services
sudo unisonctl start

# Stop all services
sudo unisonctl stop

# Restart all services
sudo unisonctl restart

# Show status
sudo unisonctl status

# Enable auto-start on boot
sudo unisonctl enable

# Disable auto-start
sudo unisonctl disable
```

### Logs

```bash
# View logs (last 50 lines)
sudo unisonctl logs

# View specific service logs
sudo unisonctl logs unison-auth

# Follow logs in real-time
sudo unisonctl follow unison-orchestrator
```

### Testing

```bash
# Test audio
sudo unisonctl test audio

# Health check
sudo unisonctl health
```

### Information

```bash
# Show version
sudo unisonctl version

# Show help
sudo unisonctl help
```

---

## 📂 Directory Structure

```
/opt/unison/              # Installation directory
├── unison-orchestrator/  # Orchestrator service
├── unison-auth/          # Auth service
├── unison-consent/       # Consent service
├── scripts/              # Utility scripts
└── .env                  # Environment configuration

/var/lib/unison/          # Data directory
├── keys/                 # RSA keys
├── storage/              # Event storage
└── postgres/             # Database data

/var/log/unison/          # Log directory
```

---

## ⚙️ Configuration

### Environment Variables

Edit `/opt/unison/.env` to configure:

```bash
# Service ports
UNISON_ORCHESTRATOR_PORT=8090
UNISON_AUTH_PORT=8088
UNISON_CONSENT_PORT=7072

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security (CHANGE IN PRODUCTION!)
UNISON_JWT_SECRET=<generated>
UNISON_CONSENT_SECRET=<generated>

# Tracing
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

After changing configuration:

```bash
sudo unisonctl restart
```

### Audio Configuration

If audio isn't working:

1. **Check devices**:
   ```bash
   aplay -l    # List playback devices
   arecord -l  # List capture devices
   ```

2. **Check volume**:
   ```bash
   alsamixer
   ```

3. **Check permissions**:
   ```bash
   groups      # Should include 'audio'
   ```

4. **Restart PulseAudio**:
   ```bash
   pulseaudio -k
   pulseaudio --start
   ```

---

## 🔧 Troubleshooting

### Services Won't Start

1. **Check logs**:
   ```bash
   sudo unisonctl logs unison-orchestrator
   ```

2. **Check dependencies**:
   ```bash
   systemctl status redis
   ```

3. **Check ports**:
   ```bash
   sudo netstat -tulpn | grep -E '8088|8090|7072'
   ```

### Audio Issues

1. **Run audio test**:
   ```bash
   sudo unisonctl test audio
   ```

2. **Check PulseAudio**:
   ```bash
   pulseaudio --check
   pactl info
   ```

3. **Check permissions**:
   ```bash
   sudo usermod -aG audio unison
   sudo systemctl restart unison-orchestrator
   ```

### Permission Errors

```bash
# Fix ownership
sudo chown -R unison:unison /opt/unison
sudo chown -R unison:unison /var/lib/unison
sudo chown -R unison:unison /var/log/unison

# Fix permissions
sudo chmod 600 /var/lib/unison/keys/*_private.pem
```

### Network Issues

```bash
# Check if services are listening
sudo netstat -tulpn | grep python

# Test connectivity
curl http://localhost:8090/health
curl http://localhost:8088/health
curl http://localhost:7072/health
```

---

## 🔐 Security

### Production Deployment

Before deploying to production:

1. **Change secrets**:
   ```bash
   sudo nano /opt/unison/.env
   # Update UNISON_JWT_SECRET and UNISON_CONSENT_SECRET
   sudo unisonctl restart
   ```

2. **Enable firewall**:
   ```bash
   sudo ufw allow 8090/tcp  # Orchestrator
   sudo ufw allow 8088/tcp  # Auth
   sudo ufw allow 7072/tcp  # Consent
   sudo ufw enable
   ```

3. **Use HTTPS**:
   - Set up reverse proxy (nginx/Apache)
   - Configure SSL certificates
   - Update service URLs

4. **Rotate keys**:
   ```bash
   # Generate new RSA keys
   cd /var/lib/unison/keys
   sudo -u unison python3.12 /opt/unison/scripts/generate_keys.py
   sudo unisonctl restart
   ```

---

## 📊 Monitoring

### Service Status

```bash
# Check all services
sudo unisonctl status

# Check individual service
systemctl status unison-orchestrator
```

### Logs

```bash
# View logs
sudo journalctl -u unison-orchestrator -n 100

# Follow logs
sudo journalctl -u unison-orchestrator -f

# Filter by time
sudo journalctl -u unison-orchestrator --since "1 hour ago"
```

### Resource Usage

```bash
# CPU and memory
top -p $(pgrep -d',' -f unison)

# Disk usage
du -sh /var/lib/unison/*
```

---

## 🔄 Updates

### Update Unison

```bash
cd /opt/unison
sudo -u unison git pull
sudo unisonctl restart
```

### Update Dependencies

```bash
sudo apt-get update
sudo apt-get upgrade
sudo unisonctl restart
```

---

## 🗑️ Uninstallation

To completely remove Unison:

```bash
# Stop services
sudo unisonctl stop

# Disable services
sudo unisonctl disable

# Remove systemd units
sudo rm /etc/systemd/system/unison-*.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/unison
sudo rm -rf /var/lib/unison
sudo rm -rf /var/log/unison

# Remove user
sudo userdel -r unison

# Remove unisonctl
sudo rm /usr/local/bin/unisonctl
```

---

## 📚 Additional Resources

- **Documentation**: https://docs.unison.ai
- **GitHub**: https://github.com/project-unisonos/unison
- **Support**: https://support.unison.ai
- **Community**: https://community.unison.ai

---

## 🆘 Getting Help

If you encounter issues:

1. Check this documentation
2. Run diagnostics:
   ```bash
   sudo unisonctl health
   sudo unisonctl test audio
   ```
3. Check logs:
   ```bash
   sudo unisonctl logs
   ```
4. Search GitHub issues
5. Ask in community forums
6. Contact support

---

## ✅ Verification Checklist

After installation, verify:

- [ ] All services running (`sudo unisonctl status`)
- [ ] Health checks passing (`sudo unisonctl health`)
- [ ] Audio working (`sudo unisonctl test audio`)
- [ ] Echo skill responds
- [ ] Logs are clean (no errors)
- [ ] Services auto-start on boot (if enabled)

---

**Installation complete! Welcome to Unison!** 🎉
