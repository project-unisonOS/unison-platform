# Installers

Installer scripts live here for different host targets:
- **install-native.sh**: native Ubuntu install (no Docker).
- **install-docker.sh**: host already has Docker; pulls and configures platform Compose.
- **install-wsl.sh**: WSL-specific bootstrap script (Windows + Ubuntu WSL).

Goals:
- Provide the `curl | bash` entrypoint referenced in docs.
- Share common env/config handling across installers.
- Emit systemd units (e.g., `unison-platform.service`) to start the stack on boot.

Scripts:
- `install-docker.sh` — assumes Docker/Compose present; copies compose bundle, seeds `/etc/unison/platform.env`, installs/enables `unison-platform.service`, pulls images, and starts the stack.
- `install-native.sh` — installs Docker/Compose if missing, then performs the same steps as docker installer.
- `install-wsl.sh` — WSL-friendly path; installs Docker if needed, copies bundle/env, pulls images, and starts the stack (systemd optional in WSL).
- `common.sh` — shared helpers for prereq checks, env seeding, systemd unit creation, image pulls, and startup.
