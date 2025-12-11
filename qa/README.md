# QA & End-to-End Tests

This directory will host smoke and hardware-facing tests for the productized platform.

Planned coverage:
- Start/stop and health across core services.
- Voice/multimodal path (renderer → io-speech → orchestrator → inference → renderer).
- Storage/profile path.
- Security toggles (auth on/off, labs features).
- Install/boot validation for images/installer outputs.

Integration with CI:
- Invoked from platform workflows for nightly/beta/stable channels.
- Parameterized to run against Docker Compose, native installs, or built images.

Status: scaffolding — test harness and fixtures will land in Phase 2+.

## Running Locally

```bash
TARGET_HOST=http://localhost PORT_ORCHESTRATOR=8090 python -m pytest qa -v
```

Defaults match dev/prod compose mappings; override ports via env vars.
