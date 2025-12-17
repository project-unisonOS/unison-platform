---
title: Install UnisonOS (Developer Images)
---

# Install UnisonOS (Release Artifacts)

UnisonOS platform artifacts are distributed as **GitHub Release assets** from:
`https://github.com/project-unisonOS/unison-platform/releases`.

For `v0.5.0-alpha.N`, a **single tag** publishes **all** evaluator artifacts (WSL2 + Linux VM + bare metal) plus a manifest and checksums.

Jump to:

- <a id="wsl2"></a>[Windows / WSL2](#windows--wsl2)
- <a id="linux-vm"></a>[Linux VM](#linux-vm)
- <a id="bare-metal"></a>[Bare Metal](#bare-metal)

## Windows + WSL2

**For:** Developers on Windows 11/10 who want a fast local dev environment via WSL2.  
**Download:** From the GitHub Release tag (example `v0.5.0-alpha.N`):
- `unisonos-wsl2-v0.5.0-alpha.N.tar.gz`
- `SHA256SUMS-v0.5.0-alpha.N.txt`

**Prereqs**

- Windows 11 (recommended) or Windows 10 19044+
- Admin access to enable WSL2
- Enough disk space for a Linux distro + Docker images
- Docker Desktop (recommended) or Docker installed inside WSL

**Install (copy/paste)**

```powershell
# 1) Enable WSL2 (one-time)
wsl --install

# 2) Import the UnisonOS WSL distro
wsl --import UnisonOS `
  C:\\wsl\\unisonos `
  .\\unisonos-wsl2-v0.5.0-alpha.N.tar.gz `
  --version 2

# 3) Launch
wsl -d UnisonOS
```

## Linux VM

**For:** Developers on Linux/macOS/Windows who want an isolated VM-based dev environment.  
**Download:** From the GitHub Release tag (example `v0.5.0-alpha.N`):
- `unisonos-linux-vm-v0.5.0-alpha.N.qcow2` (and/or `.vmdk`)
- `SHA256SUMS-v0.5.0-alpha.N.txt`

**Prereqs**

- QEMU (Linux/macOS) or VMware/VirtualBox/Hyper-V (as supported)
- Enough disk space for the image + snapshots

**QEMU quick start (example)**

```bash
qemu-system-x86_64 \
  -m 8192 -smp 4 \
  -drive file=unisonos-linux-vm-v0.5.0-alpha.N.qcow2,format=qcow2 \
  -nic user,model=virtio-net-pci \
  -display none -serial mon:stdio
```

## Bare Metal

**For:** Developers/operators installing UnisonOS onto dedicated hardware.  
**Download:** From the GitHub Release tag (example `v0.5.0-alpha.N`):
- `unisonos-baremetal-v0.5.0-alpha.N.iso`
- `SHA256SUMS-v0.5.0-alpha.N.txt`

**Prereqs**

- A target machine you can boot from USB
- A USB drive (8GB+ recommended)
- A flashing tool (Rufus / balenaEtcher) or `dd` on Linux

**Install (high-level)**

1. Flash `unisonos-baremetal-v0.5.0-alpha.N.iso` to a USB drive.
2. Boot the target machine from USB.
3. Follow the on-screen installer prompts.
4. After install, reboot into the installed system.

**What you get**

- A bootable installer ISO designed for bare-metal deployment.

**What you do NOT get**

- A WSL2 distro import tarball.
- A VM disk image.
