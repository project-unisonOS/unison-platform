# Installers

Installer scripts live here for different host targets:
- **install-native.sh**: native Ubuntu install for the supported Milestone 1 target.
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

Safety behavior:

- Installers no longer start the stack if `/etc/unison/platform.env` still contains template or development defaults.
- Auto-start is opt-in via `UNISON_AUTO_START=1`.
- `UNISON_SKIP_START=1` always suppresses first start.
- Installers now install `/usr/local/bin/unisonctl` as the supported Milestone 1 operations CLI for the compose-backed native stack.
