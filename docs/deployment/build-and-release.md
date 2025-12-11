# Platform Images, Installers, and Releases

This doc summarizes the build outputs, how to use them, and how they relate to GHCR/tagging once releases are cut.

## Build Outputs (images/out/)
- `unisonos-wsl-<version>.tar.gz` — WSL bundle (compose, env template, models manifest).
- `unisonos-vm-<version>/` — VM bundle with Packer stub, models manifest, metadata (targets QCOW2/VMDK).
- `unisonos-iso-<version>/` — Autoinstall seed (user-data/meta-data), models manifest, metadata for ISO baking.
- Version defaults to `git describe --tags --always` unless `VERSION` env is set; `MODEL_FLAVOR` selects model profile (`images/models.yaml`).

## Make Targets
- `make image-wsl` — builds WSL tarball.
- `make image-vm` — writes VM bundle directory.
- `make image-iso` — writes autoinstall seed bundle.
- `make qa-smoke` — runs platform health + inference smoke tests (used in CI).

## Installers (`installer/`)
- `install-docker.sh` — assumes Docker/Compose present; seeds `/etc/unison/platform.env`, installs `unison-platform.service`, pulls images, starts stack.
- `install-native.sh` — installs Docker/Compose if missing, then same flow as docker installer.
- `install-wsl.sh` — WSL-friendly path; installs Docker if needed, seeds env, pulls images, starts stack (systemd optional in WSL).
- Shared helpers in `installer/common.sh`.

## GHCR/Tagging (planned)
- Images are published as `ghcr.io/project-unisonos/<service>:<tag>`:
  - Nightly: `:edge-main-YYYYMMDD` (from `main`).
  - Beta: `:vX.Y.0-beta.N` (from `release/x.y`).
  - Stable: `:vX.Y.Z` and `:latest` for platform.
- Platform artifacts (WSL/VM/ISO + installers) will be attached to GitHub Releases in `unison-platform` for tagged versions.
- Model manifest (`images/models.yaml`) drives model preload selection; include rendered `models.json` with published artifacts.

## Usage Notes
- Before publishing artifacts, ensure secrets in `/etc/unison/platform.env` (or shipped `.env` template) are set.
- For ISO: bake `images/out/unisonos-iso-<version>/autoinstall/*` into an Ubuntu Server ISO using `xorriso`/`mkisofs`; late-commands install platform and enable `unison-platform.service`.
- For VM images: replace Packer stub with real qemu/vmware builders; emit QCOW2/VMDK named `unisonos-vm-<version>.<ext>`.
- For WSL: distribute `unisonos-wsl-<version>.tar.gz`; extract, set env, run `docker compose -f bundle/docker-compose.prod.yml up -d`.
