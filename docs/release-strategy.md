---
title: Platform Image Release Strategy
---

# Platform Image Release Strategy

UnisonOS platform artifacts are delivered as **GitHub Release assets** in the `project-unisonOS/unison-platform` repository.

## Goals

- Make it obvious what to download.
- Keep versioned releases immutable and auditable.
- Provide “latest per target” entry points for developers.

## Tagging model

### Immutable, versioned tags (current)

For `v0.5.0-alpha.N`, use **one tag** that publishes **all** evaluator artifacts. Example:

- `v0.5.0-alpha.N` → WSL2 + Linux VM + bare metal + manifest + checksums

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

Each platform image release should:

- Publish a single evaluator bundle release per tag.
- Publish assets with canonical, self-describing names:
  - `unisonos-wsl2-v0.5.0-alpha.N.tar.gz` (or `.zip`)
  - `unisonos-linux-vm-v0.5.0-alpha.N.qcow2` (and/or `.vmdk`)
  - `unisonos-baremetal-v0.5.0-alpha.N.iso.part00` (and subsequent `part*`, plus `...REASSEMBLE.txt`)
  - `unisonos-manifest-v0.5.0-alpha.N.json`
  - `SHA256SUMS-v0.5.0-alpha.N.txt`
- Link to a single canonical install page:
  - `https://project-unisonos.github.io/developers/evaluate-alpha/`
