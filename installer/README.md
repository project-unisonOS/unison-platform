# Installers

Installer scripts live here for different host targets:
- **install-native.sh**: native Ubuntu install (no Docker).
- **install-docker.sh**: host already has Docker; pulls and configures platform Compose.
- **install-wsl.sh**: WSL-specific bootstrap script (Windows + Ubuntu WSL).

Goals:
- Provide the `curl | bash` entrypoint referenced in docs.
- Share common env/config handling across installers.
- Emit systemd units (e.g., `unison-platform.service`) to start the stack on boot.

Status: scaffolding — scripts are stubs pending implementation in Phase 2.
