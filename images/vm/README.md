# Linux VM Image (QCOW2 / VMDK)

This directory builds evaluator-ready **bootable VM disk images** that contain:

- Ubuntu LTS (currently 24.04 cloud image as base)
- Docker + Compose plugin installed
- Unison platform bundle installed under `/opt/unison-platform`
- `unison-platform.service` enabled to auto-start the stack on boot

## Outputs

- `unison-platform/images/out/unisonos-linux-vm-${VERSION}.qcow2`
- (Optional) `unison-platform/images/out/unisonos-linux-vm-${VERSION}.vmdk`

## Requirements

- `qemu-img` (package: `qemu-utils`)
- `virt-customize` (package: `libguestfs-tools`)
- `curl`

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y qemu-utils libguestfs-tools curl
```

## Build

```bash
cd unison-platform
VERSION=v0.5.0-alpha.1 make linux-vm
```

This uses `images/vm/scripts/build-vm-qcow2.sh` and downloads the Ubuntu cloud image into `images/cache/`.

## Login / access

- Default user: `unison`
- Default password: `unison` (alpha evaluator default; change immediately for real installs)
- Renderer UI (after first boot + services start): `http://<vm-ip>:8092`

Networking defaults to DHCP.

