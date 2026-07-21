---
title: DX Rationale (Platform Image Releases)
---

# DX Rationale (Platform Image Releases)

This repo delivers UnisonOS platform images via **GitHub Releases**. The structure in the install docs and the release-note template is designed to optimize for a “one-minute install” and minimize developer confusion.

## Why this structure

- **Audience-first release notes**: Developers should immediately know whether a release is meant for them, without reading build logs or guessing from filenames.
- **Canonical asset names**: Stable, self-describing filenames (“wsl2-dev”, “linux-vm-dev”, “bare-metal”) make it obvious what to download and reduce copy/paste errors.
- **Target-specific install pages**: Separate pages for WSL2, Linux VM, and bare metal keep each flow short and copy/paste-friendly:
  - `docs/install-wsl2.md`
  - `docs/install-linux-vm.md`
  - `docs/install-bare-metal.md`
- **Landing page**: `docs/install.md` links to the three target pages and highlights the current download page.
- **Per-target releases**: Shipping one target per release prevents accidental installs on the wrong platform (e.g., WSL vs VM).
- **Latest-per-target tags**: Rolling tags (`latest-wsl`, `latest-linux-vm`, `latest-bare-metal`) create predictable “just give me the newest” links while versioned tags remain immutable for audits and rollbacks.
