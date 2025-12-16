# Bare-metal Installer ISO (Ubuntu Autoinstall)

This directory builds a **full, bootable Ubuntu Server installer ISO** with embedded UnisonOS autoinstall configuration (NoCloud).

The output is evaluator-ready: boot from USB, unattended install, reboot into an installed system with `unison-platform.service` enabled to auto-start the stack.

## Outputs

- `unison-platform/images/out/unisonos-baremetal-installer-${VERSION}.iso`

## Requirements

- `xorriso`
- `curl`
- `python3`

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y xorriso curl
```

## Build

```bash
cd unison-platform
VERSION=v0.5.0-alpha.1 make baremetal-iso
```

Optional overrides:

- `UBUNTU_ISO_URL` (default: Ubuntu 24.04 LTS live server amd64)
- `UBUNTU_ISO_SHA256` (optional integrity check)

## What the autoinstall does

- Installs Ubuntu Server (Ubuntu LTS; default 24.04)
- Creates a local evaluator user: `unison` (password set in `nocloud/user-data`)
- Installs Docker + Compose plugin via apt
- Copies the Unison platform bundle from the installer media into `/opt/unison-platform`
- Seeds `/etc/unison/platform.env` from `.env.template`
- Installs and enables `unison-platform.service` so the stack starts on boot

Model defaults and model-pack behavior are driven by:

- `unison-platform/images/models.yaml` + `MODEL_FLAVOR`
- `unison-platform/model-packs/alpha/*`

