# Platform Images, Installers, and Releases

This doc summarizes the build outputs, how to use them, and how they relate to GHCR/tagging once releases are cut.

## Build Outputs (images/out/)
- `unisonos-wsl-<version>.tar.gz` — WSL bundle (compose, env template, models manifest).
- `unisonos-linux-vm-<version>.qcow2` — Bootable Ubuntu VM disk image (built from Ubuntu cloud image; provisions UnisonOS on first boot).
- `unisonos-baremetal-installer-<version>.iso` — Full Ubuntu Server installer ISO remastered with embedded autoinstall payload (not seed-only).
- Version defaults to `git describe --tags --always` unless `VERSION` env is set; `MODEL_FLAVOR` selects model profile (`images/models.yaml`).
- Default base OS: Ubuntu 24.04 (override with `UBUNTU_VERSION`/`UBUNTU_TAG` where applicable).

## Make Targets
- `make image-wsl` — builds WSL tarball.
- `make linux-vm` — writes VM QCOW2 (and optional VMDK).
- `make baremetal-iso` — writes the remastered installer ISO with embedded autoinstall payload.
- `make qa-smoke` — runs platform health + inference smoke tests (used in CI).
- `release.yml` workflow — on `v*` tags, installs tooling, builds images/seed ISO, uploads artifacts, and attaches them to GitHub Releases.

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
- Service repos can call the shared workflow `project-unisonOS/unison-platform/.github/workflows/reusable-build.yml@main` to inherit the same tag semantics and GHCR labels.

## Usage Notes
- Before publishing artifacts, ensure secrets in `/etc/unison/platform.env` (or shipped `.env` template) are set.
- For ISO: bake `images/out/unisonos-iso-<version>/autoinstall/*` into an Ubuntu Server ISO using `xorriso`/`mkisofs`; late-commands install platform and enable `unison-platform.service`.
- For VM images: the CI build path uses Ubuntu cloud images + libguestfs customization (no KVM required); the image provisions the platform on first boot via a systemd unit.
- For WSL: distribute `unisonos-wsl-<version>.tar.gz`; extract, set env, run `docker compose -f bundle/docker-compose.prod.yml up -d`.
