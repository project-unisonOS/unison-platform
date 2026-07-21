---
title: Install UnisonOS (WSL2)
---

# Install UnisonOS (WSL2 Evaluation)

WSL2 is an evaluation channel for Milestone 1, not the supported production install target.

Download the WSL2 artifact from the GitHub Release:

- https://github.com/project-unisonOS/unison-platform/releases/tag/v0.5.0-alpha.1

Expected assets (for `v0.5.0-alpha.N`):

- `unisonos-wsl2-v0.5.0-alpha.N.tar.gz` (or `.zip`)
- `SHA256SUMS-v0.5.0-alpha.N.txt`

## Install

```powershell
wsl --install

wsl --import UnisonOS `
  C:\\wsl\\unisonos `
  .\\unisonos-wsl2-v0.5.0-alpha.N.tar.gz `
  --version 2

wsl -d UnisonOS
```

After import, review `/etc/unison/platform.env`, replace any template or development defaults, and then start the stack manually.

## Access

- Renderer UI: `http://localhost:8092`
