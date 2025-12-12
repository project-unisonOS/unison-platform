---
title: DX Rationale (Platform Image Releases)
---

# DX Rationale (Platform Image Releases)

This repo delivers UnisonOS platform images via **GitHub Releases**. The structure in `docs/install.md` and the release-note template is designed to optimize for a “one-minute install” and minimize developer confusion.

## Why this structure

- **Audience-first release notes**: Developers should immediately know whether a release is meant for them, without reading build logs or guessing from filenames.
- **Canonical asset names**: Stable, self-describing filenames (“wsl2-dev”, “linux-vm-dev”, “bare-metal”) make it obvious what to download and reduce copy/paste errors.
- **Single install entry point**: One page (`docs/install.md`) avoids duplicated instructions across releases and keeps updates centralized.
- **Per-target releases**: Shipping one target per release prevents accidental installs on the wrong platform (e.g., WSL vs VM).
- **Latest-per-target tags**: Rolling tags (`latest-wsl`, `latest-linux-vm`, `latest-bare-metal`) create predictable “just give me the newest” links while versioned tags remain immutable for audits and rollbacks.

