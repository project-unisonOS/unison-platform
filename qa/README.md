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

Status:
- `qa/test_smoke.py` covers the compose/devstack smoke path.
- `qa/test_native_install_acceptance.py` covers the supported Ubuntu native install path when run against a real installed stack.

## Running Locally

```bash
TARGET_HOST=http://localhost PORT_ORCHESTRATOR=8090 python -m pytest qa -v
```

Defaults match dev/prod compose mappings; override ports via env vars.

Native install acceptance:

```bash
RUN_NATIVE_INSTALL_ACCEPTANCE=1 python -m pytest qa/test_native_install_acceptance.py -v
```

Useful overrides:
- `UNISONCTL_BIN`
- `ORCHESTRATOR_BASE_URL`
- `RENDERER_BASE_URL`
- `AUTH_BASE_URL`
- `CONTEXT_BASE_URL`
- `AGENT_VDI_BASE_URL`
- `STORAGE_BASE_URL`
- `MILESTONE1_ACCEPTANCE_USERNAME`
- `MILESTONE1_ACCEPTANCE_PASSWORD`
- `MILESTONE1_ACCEPTANCE_PERSON_ID`
