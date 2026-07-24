# Installers

## Supported native release bootstrap

The Phase 9 candidate path uses `installer/bootstrap.py`. It verifies the
canonical bundle index with the separately trusted Ed25519 public key, rejects
undeclared or changed content, reconciles the release manifest with Compose,
images, host requirements, licenses, and the model profile, then prints an
exact system-change plan. Verification does not require elevated privileges.

Installation requires the SHA-256 of that exact plan:

```bash
./installer/bootstrap.py \
  --bundle unisonos-VERSION-x86_64.tar \
  --trusted-public-key unisonos-release.pem \
  --prefix /opt/unison \
  --data-dir /var/lib/unison \
  verify

sudo ./installer/bootstrap.py \
  --bundle unisonos-VERSION-x86_64.tar \
  --trusted-public-key unisonos-release.pem \
  --prefix /opt/unison \
  --data-dir /var/lib/unison \
  install \
  --accept-plan-sha256 PLAN_SHA256
```

Successful installation writes `/opt/unison/install-receipt.json`, which binds
the installed tree to the signed bundle index, release manifest, source commit,
and immutable image inventory. Uninstall removes the receipt and software while
preserving personal data unless factory reset receives its separate exact
destruction confirmation.

## Verified update transaction

`installer/update_transaction.py` accepts only a
`unison.updates.verified-target.v1` authorization whose channel, target
version, release version, hardware profile, artifact length, and artifact
SHA-256 match the independently verified signed release bundle.

Before activation it verifies available capacity, copies and verifies the
personal-data checkpoint, materializes the complete target into a versioned
staging path, and journals the transaction. Activation atomically changes the
current release pointer. A bounded health callback must pass before the new
receipt and version are promoted.

Failed health, migration, or post-activation interruption restores the
last-known-good release, receipt, and checkpointed data automatically. A
promoted update retains its checkpoint for explicit owner rollback. An
interruption before activation leaves the old release active and permits the
same verified target to resume.

Installer scripts live here for different host targets:
- **install-native.sh**: legacy repository-oriented native Ubuntu evaluation path.
- **install-docker.sh**: host already has Docker; pulls and configures platform Compose.
- **install-wsl.sh**: WSL-specific bootstrap script (Windows + Ubuntu WSL).

Goals:
- Provide a single canonical native install path.
- Share common env/config handling across installers.
- Emit `unison-platform.service` for managed startup after first-run configuration is complete.

Scripts:
- `install-docker.sh` — assumes Docker/Compose present; copies the compose bundle, seeds `/etc/unison/platform.env`, installs/enables `unison-platform.service`, and pulls images.
- `install-native.sh` — installs Docker/Compose if missing, then performs the same bundle/env/systemd setup as the Docker installer.
- `install-wsl.sh` — WSL-friendly path for evaluation environments; installs Docker if needed, copies bundle/env, and prepares the stack.
- `common.sh` — shared helpers for prereq checks, env seeding, systemd unit creation, image pulls, safety validation, and optional startup.

Runtime bundle defaults:
- native installs now default to `compose/compose.native.yaml`
- developer/runtime iteration still uses `compose/compose.yaml` and `compose/compose.local-source.yaml`
- optional `updates` remains behind its compose profile

Safety behavior:

- Installers no longer start the stack if `/etc/unison/platform.env` still contains template or development defaults.
- Native installs seed `/etc/unison/platform.env` from `.env.native.template` by default so the supported Milestone 1 route starts from a narrower runtime contract than the broader developer `.env.template`.
- Auto-start is opt-in via `UNISON_AUTO_START=1`.
- `UNISON_SKIP_START=1` always suppresses first start.
- Installers now install `/usr/local/bin/unisonctl` as the supported Milestone 1 operations CLI for the compose-backed native stack.
