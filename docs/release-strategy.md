---
title: Platform Image Release Strategy
---

# Platform Image Release Strategy

UnisonOS platform artifacts are delivered as **GitHub Release assets** in the `project-unisonOS/unison-platform` repository.

Important Milestone 1 framing:
- the supported installation route is Ubuntu 24.04 native on x86_64
- WSL2, Linux VM, and bare-metal image artifacts are evaluator channels unless explicitly promoted
- release assets and release notes should foreground the native route first

## Goals

- Make it obvious what to download.
- Make the supported native install path unmistakable.
- Keep versioned releases immutable and auditable.
- Provide “latest per target” entry points for developers and evaluators.

## Tagging model

### Immutable, versioned tags (current)

For `v0.5.0-alpha.N`, use one immutable release tag.

That release should always support the canonical native install path first. Evaluator artifacts may also be attached when available.

Example current alpha shape:

- `v0.5.0-alpha.N` → native install docs/assets first, optionally followed by WSL2 + Linux VM + bare metal + manifest + checksums

These tags are **immutable** and should never be moved.

### Rolling “latest per target” tags

Maintain one moving tag per target:

- `latest-wsl`
- `latest-linux-vm`
- `latest-bare-metal`

These tags are **mutable** and should be force-updated to point at the newest corresponding versioned tag.

Example (manual update):

```bash
git fetch --tags origin
git tag -fa latest-wsl vX.Y.Z-wsl2 -m "Latest WSL2 developer image"
git push -f origin latest-wsl
```

## Release expectations (alpha)

Each platform release should:

- foreground the canonical Ubuntu native install path
- publish evaluator artifacts only as secondary channels when available
- publish assets with canonical, self-describing names:
  - `unisonos-wsl2-v0.5.0-alpha.N.tar.gz` (or `.zip`)
  - `unisonos-linux-vm-v0.5.0-alpha.N.qcow2` (and/or `.vmdk`)
  - `unisonos-baremetal-v0.5.0-alpha.N.iso.part00` (and subsequent `part*`, plus `...REASSEMBLE.txt`)
  - `unisonos-manifest-v0.5.0-alpha.N.json`
  - `SHA256SUMS-v0.5.0-alpha.N.txt`
- Link to the canonical install pages for the supported native route first
- Link to evaluator install pages second when those artifacts are present
