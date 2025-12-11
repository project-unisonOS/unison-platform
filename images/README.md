# Platform Images (WSL / VM / ISO)

This directory will host the build pipeline for UnisonOS images:
- **WSL**: scripted install or rootfs tarball for Windows WSL.
- **VM**: QCOW2/VMDK images for common hypervisors.
- **Bare metal ISO**: Ubuntu autoinstall-based ISO that installs UnisonOS and boots into the platform stack.

Planned components:
- Shared provisioners (Ansible/shell) to install Docker, `unison-platform`, Ollama/local models, and systemd units.
- Make targets: `make image-wsl`, `make image-vm`, `make image-iso`.
- Outputs published alongside `unison-platform` releases.
- Model manifest stub: `models.yaml` to control default/preloaded models per flavor.

Status: scaffolding — implementation will land in Phase 2.
