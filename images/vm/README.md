# VM Targets (QCOW2 / VMDK)

Goal: build VM images for common hypervisors (QEMU/Proxmox, VMware) using Ubuntu cloud images as base.

Planned steps:
- Use Packer (or equivalent) to consume Ubuntu cloud image.
- Provision with Docker, platform Compose, Ollama/local models, and systemd units to start Unison on boot.
- Output: `unisonos-vm-qcow2-<version>.img` and `unisonos-vm-vmdk-<version>.vmdk`.

Build entrypoint: `make image-vm` (calls `images/vm/build-vm.sh`), writes bundle under `images/out/unisonos-vm-<version>/`.
