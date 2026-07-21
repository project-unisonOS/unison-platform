# WSL Target (Windows + Ubuntu)

Goal: deliver a WSL-friendly artifact (rootfs tarball or scripted install) that runs the Unison platform via Docker Compose.

Planned steps:
- Validate WSL + Ubuntu version.
- Install Docker inside WSL (or use Docker Desktop integration).
- Pull platform images from GHCR and configure volumes.
- Seed `.env` for WSL defaults and start the stack (`unisonctl start` equivalent).
- Optional: publish a `unison-os-wsl.tar.gz` rootfs.

Build entrypoint: `make image-wsl` (calls `images/wsl/build-wsl.sh`), outputs to `images/out/unisonos-wsl-<version>.tar.gz`.

Defaults: Ubuntu 24.04 base for the rootfs tarball (override with `UBUNTU_TAG=22.04` if needed).
