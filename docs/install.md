title: Install UnisonOS
---

# Install UnisonOS

For the current production-track milestone, the supported installation target is Ubuntu 24.04 native on x86_64 hardware.

Start here:

- [Ubuntu Native Installation](deployment/ubuntu-native.md)

Evaluation-only channels remain available for testing and documentation work:

- [Install (WSL2 Evaluation)](install-wsl2.md)
- [Install (Linux VM Evaluation)](install-linux-vm.md)
- [Install (Bare Metal Evaluation)](install-bare-metal.md)

Important:

- WSL2, VM, and bare-metal image artifacts are not the canonical Milestone 1 user-install path.
- Installers now seed `/etc/unison/platform.env` but do not start the platform until production-safe secrets and environment values are set.
- If you are evaluating release artifacts, treat them as non-production previews and review the install guide before first start.
