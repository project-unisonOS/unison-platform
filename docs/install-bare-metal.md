---
title: Install UnisonOS (Bare Metal)
---

# Install UnisonOS (Bare Metal Evaluation)

Bare-metal ISO images are still an evaluation channel. They are not the supported Milestone 1 installation path.

Download the bare-metal installer ISO from the GitHub Release:

- https://github.com/project-unisonOS/unison-platform/releases/tag/v0.5.0-alpha.1

Expected assets (for `v0.5.0-alpha.N`):

- `unisonos-baremetal-v0.5.0-alpha.N.iso.part00` (and subsequent `part*`)
- `unisonos-baremetal-v0.5.0-alpha.N.iso.REASSEMBLE.txt`
- `SHA256SUMS-v0.5.0-alpha.N.txt`

## Bare-metal ISO is split (GitHub 2GB limit)

GitHub Releases limit individual assets to 2GB, so the bare-metal ISO is shipped as multiple parts (`.iso.part00`, `.iso.part01`, …). Reassemble before flashing:

- `cat unisonos-baremetal-v0.5.0-alpha.N.iso.part* > unisonos-baremetal-v0.5.0-alpha.N.iso`

## Install

1. Reassemble the ISO:
   - `cat unisonos-baremetal-v0.5.0-alpha.N.iso.part* > unisonos-baremetal-v0.5.0-alpha.N.iso`
2. Flash the ISO to a USB drive (Rufus/balenaEtcher or `dd`).
3. Boot the target machine from USB.
4. Follow the installer prompts, then reboot.

## Access

- Renderer UI: `http://<device-ip>:8092`

Review `/etc/unison/platform.env` after install, remove any template defaults, and set production-safe secrets before the first platform start.
