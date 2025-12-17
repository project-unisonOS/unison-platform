---
title: Install UnisonOS (WSL2)
---

# Install UnisonOS (WSL2)

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

## Access

- Renderer UI: `http://localhost:8092`
