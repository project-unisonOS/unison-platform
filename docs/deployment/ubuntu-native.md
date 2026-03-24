# Ubuntu Native Installation

This is the canonical Milestone 1 install path for UnisonOS.

Supported target:

- Ubuntu 24.04 LTS
- x86_64 hardware
- local microphone and speakers
- enough CPU and memory to run the selected local model profile

This guide intentionally does not describe evaluator images, default passwords, or developer-only bootstrap flows.

## What The Native Installer Does

`installer/install-native.sh`:

- installs Docker if missing
- copies the platform bundle into `/opt/unison-platform`
- seeds `/etc/unison/platform.env` from `.env.template` if the file does not already exist
- installs and enables `unison-platform.service`
- pulls container images
- stops before first start unless the environment is explicitly production-safe and auto-start is requested

That last point is deliberate. The installer will not boot the stack with template or development defaults.

## Install

From the `unison-platform` repository:

```bash
sudo make install-native
```

Or run the installer directly:

```bash
cd installer
sudo ./install-native.sh
```

## Required Configuration Before First Start

Open the generated environment file:

```bash
sudo editor /etc/unison/platform.env
```

At minimum, replace these template defaults:

- `UNISON_ENV=development`
- `POSTGRES_PASSWORD=unison_password`
- `JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production`

For the Milestone 1 native path, set:

- `UNISON_ENV=production`
- a unique strong `POSTGRES_PASSWORD`
- a unique strong `JWT_SECRET_KEY`
- a unique `UNISON_AUTH_BOOTSTRAP_TOKEN` if the `unison-auth` service is enabled in your install profile

Review the rest of the file as well, especially model-provider and audio-related settings for the target machine.

## First Start

Start the platform only after the environment file has been updated:

```bash
sudo systemctl start unison-platform.service
sudo systemctl status unison-platform.service
```

If you need to restart after changes:

```bash
sudo unisonctl restart
```

## First Admin Bootstrap

If your install profile includes `unison-auth`, create the first admin explicitly after first start:

```bash
curl http://localhost:8083/bootstrap/status

curl -X POST http://localhost:8083/bootstrap/admin \
  -H "Content-Type: application/json" \
  -H "X-Unison-Bootstrap-Token: <value from /etc/unison/platform.env>" \
  -d '{
    "username": "owner",
    "password": "ReplaceThisWithAStrongPassword!42",
    "email": "owner@example.com"
  }'
```

This is a one-time bootstrap path. Once an active admin exists, bootstrap closes and ongoing user creation must happen through authenticated admin flows.

## Local Source Bring-Up

For active development on Ubuntu 24.04, use the local-source path instead of relying on published `latest` images for `unison-auth`, `unison-orchestrator`, and `unison-experience-renderer`.

From the workspace copy of `unison-platform`:

```bash
make up-local
```

That workflow:

- builds `ghcr.io/project-unisonos/unison-common-wheel:latest` from local `unison-common`
- builds local source images for `unison-auth`, `unison-orchestrator`, `unison-experience-renderer`, `unison-agent-vdi`, and `unison-updates`
- starts the stack with `compose/compose.local-source.yaml`

The `updates` service remains behind the optional `updates` compose profile. Include it with:

```bash
PROFILE=updates make up-local
```

When enabled through the local-source path, `unison-updates` reads the generated local release manifest at:

- `unison-platform/releases/local-dev-manifest.json`

## Verify The Install

Check the service:

```bash
sudo unisonctl status
```

Check container state:

```bash
sudo docker ps
```

Check the renderer surface:

- `http://localhost:8092`

If the stack does not come up cleanly, inspect logs:

```bash
sudo unisonctl logs
sudo unisonctl logs orchestrator
```

For local-source development validation, run:

```bash
make validate-golden
```

That script checks:

- inference readiness and selected model
- auth bootstrap status and first-admin presence
- orchestrator startup convergence
- renderer onboarding convergence

For restart/recovery validation on the live stack, run:

```bash
make validate-recovery
```

That script:

- restarts the orchestrator through the current compose stack
- waits for core endpoints to reconverge
- reruns the golden-path validation after recovery
- reruns briefing and VDI acceptance after recovery when `MILESTONE1_ACCEPTANCE_USERNAME` and `MILESTONE1_ACCEPTANCE_PASSWORD` are set

For staged updates artifact validation on the live stack, run:

```bash
make validate-update-artifact ARTIFACT=/var/lib/unison/updates/artifacts/<job>-apply-override.json
```

That script:

- reads the staged override artifact emitted by `unison-updates`
- compares the artifact service targets against `releases/local-dev-manifest.json`
- fails if the artifact and manifest disagree on the target set

For next-boot staging from an emitted apply artifact, run:

```bash
sudo unisonctl stage-update /var/lib/unison/updates/artifacts/<job>-apply-override.json
sudo unisonctl show-staged-update
```

That path:

- converts the emitted updates artifact into `${PREFIX}/staged/compose.next-boot.override.yaml`
- records metadata in `${PREFIX}/staged/compose.next-boot.metadata.json`
- causes subsequent `unisonctl start`, `restart`, and the systemd unit to include the staged override on boot

After a successful boot into the staged target, finalize it with:

```bash
sudo unisonctl finalize-staged-update
```

That path:

- archives the staged override and metadata under `${PREFIX}/staged/archive/`
- clears the active staged files unless retention is requested
- records the staged job as applied in `unison-updates`
- updates `last_known_good` to the newly booted target

For an end-to-end staged-update lifecycle check on the live stack, run:

```bash
make validate-staged-update-lifecycle
```

That validator:

- creates a fresh updates apply job
- stages its emitted artifact into a temporary prefix
- finalizes the staged boot
- verifies archive creation, cleared staged files, applied job state, and updated `last_known_good`

## Operations And Recovery

The native installer now installs a Milestone 1 `unisonctl` that operates on the compose-backed `unison-platform.service` stack.

Common commands:

```bash
sudo unisonctl status
sudo unisonctl health
sudo unisonctl logs
sudo unisonctl follow
sudo unisonctl doctor
sudo unisonctl recover
```

Recovery posture:

- `unisonctl doctor` checks Docker reachability, systemd unit presence, compose validity, and unsafe environment defaults.
- `unisonctl recover` performs a guarded restart of the platform stack and then prints post-recovery health.
- `unisonctl` refuses start, restart, or recover when `/etc/unison/platform.env` still contains template defaults.

Install acceptance:

```bash
cd /opt/unison-platform
RUN_NATIVE_INSTALL_ACCEPTANCE=1 python -m pytest qa/test_native_install_acceptance.py -v
```

Or via the repo Make target:

```bash
make qa-native-install
```

## Notes

- WSL2, VM, and bare-metal images remain useful evaluation channels, but they are not the supported production install path.
- Older `scripts/native/*` material is legacy alpha-era packaging work, not the canonical Milestone 1 install contract.
- The native installer can be forced to auto-start by setting `UNISON_AUTO_START=1`, but the recommended production path is still to review `/etc/unison/platform.env` before first boot.
