# Bare Metal ISO (Ubuntu Autoinstall)

Goal: create a bootable ISO that installs Ubuntu + Unison Platform via autoinstall.

Planned steps:
- Generate `autoinstall.yaml` with partitioning, user, SSH keys/password, and late-commands to run platform install.
- Bake ISO from Ubuntu Server base image with autoinstall seed.
- Install Docker or native services, configure platform env, and enable systemd units so Unison starts on boot.

Build entrypoint: `make image-iso` (calls `images/iso/build-iso.sh`), writes autoinstall seed bundle under `images/out/unisonos-iso-<version>/`.
