---
title: Platform Image Release Strategy
---

# Platform Image Release Strategy

UnisonOS platform images are delivered as **GitHub Release assets** in the `project-unisonOS/unison-platform` repository.

## Goals

- Make it obvious what to download.
- Keep versioned releases immutable and auditable.
- Provide “latest per target” entry points for developers.

## Tagging model

### Immutable, versioned tags (recommended)

Use one tag per target. Examples:

- `vX.Y.Z-wsl2`
- `vX.Y.Z-linux-vm`
- `vX.Y.Z-bare-metal`

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

## Release expectations

Each platform image release should:

- Target **exactly one** install path (WSL2 OR VM OR bare metal).
- Publish assets with canonical, self-describing names:
  - `unisonos-wsl2-dev.tar.gz`
  - `unisonos-linux-vm-dev.qcow2`
  - `unisonos-bare-metal.iso`
- Link to a single canonical install page:
  - `https://project-unisonos.github.io/unison-platform/install#wsl2`
  - `https://project-unisonos.github.io/unison-platform/install#linux-vm`
  - `https://project-unisonos.github.io/unison-platform/install#bare-metal`

