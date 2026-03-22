---
title: Install UnisonOS (Linux VM)
---

# Install UnisonOS (Linux VM Evaluation)

Linux VM images are for evaluation and integration testing. Ubuntu 24.04 native remains the supported Milestone 1 install path.

Download the VM image from the GitHub Release:

- https://github.com/project-unisonOS/unison-platform/releases/tag/v0.5.0-alpha.1

Expected assets (for `v0.5.0-alpha.N`):

- `unisonos-linux-vm-v0.5.0-alpha.N.qcow2` (and/or `.vmdk`)
- `SHA256SUMS-v0.5.0-alpha.N.txt`

## Run (QEMU example)

```bash
qemu-system-x86_64 \
  -m 8192 -smp 4 \
  -drive file=unisonos-linux-vm-v0.5.0-alpha.N.qcow2,format=qcow2 \
  -nic user,model=virtio-net-pci,hostfwd=tcp::8092-:8092 \
  -display none -serial mon:stdio
```

## Access

- Renderer UI: `http://localhost:8092` (if you forwarded ports) or `http://<vm-ip>:8092`

Do not treat any bundled credentials, sample users, or preconfigured environment values in evaluator images as production-safe. Review `/etc/unison/platform.env` and rotate secrets before first start.
