# UnisonOS Alpha Release — {{VERSION}}

Built: {{BUILT_AT}}

## What’s new

- Milestone 1 native install route remains the primary supported path for UnisonOS on Ubuntu 24.04 x86_64.
- Alpha evaluator artifacts may also be included for WSL2, Linux VM, and bare-metal installer testing.
- Bare-metal installer is full Ubuntu Server live-server media with embedded autoinstall payload (not a seed-only ISO).
- Includes native-install-first release assets such as `install-native.sh`, `unisonctl.sh`, `platform.env.native.template`, `compose.native.yaml`, and native install docs.
- Includes `unisonos-manifest-{{VERSION}}.json` and `SHA256SUMS-{{VERSION}}.txt` for verification.

## MVP checklist (alpha)

- Ubuntu native install route: primary supported Milestone 1 path
- WSL2 install: evaluator channel when included
- Linux VM install: evaluator channel when included
- Bare-metal install: evaluator channel when included
- Boots/starts to “ready” automatically: expected once Docker + services start
- Inference works end-to-end (default interaction model is Qwen): expected after models are installed
- Renderer reachable and usable: expected after services are up
- One-command smoke test: see install or evaluator guide as appropriate
- Recovery message if model missing: expected (install models per docs)

## Downloads

GitHub Release assets (native-first contract plus any evaluator artifacts):

{{ASSETS_BULLETS}}

{{BARE_METAL_NOTE}}

Canonical native install guide:
- https://project-unisonos.github.io/developers/install-unisonos/

Alpha evaluation guides:
- https://project-unisonos.github.io/developers/install-wsl2/
- https://project-unisonos.github.io/developers/install-linux-vm/
- https://project-unisonos.github.io/developers/install-bare-metal/

## Model packs

- Default profile: `alpha/default` (Qwen for interaction + planner)
- If models are missing, follow the prompt or see the current model-pack guidance in the platform and docs repos.

## Known issues

- Alpha quality; expect rough edges in first-run experience and hardware compatibility.
- VM images may take longer to boot on hosts without virtualization acceleration.

## Verification

- Verify `SHA256SUMS-{{VERSION}}.txt` against downloaded assets.

## Report bugs

- Packaging/install/release issues: https://github.com/project-unisonOS/unison-platform/issues
- Devstack issues: https://github.com/project-unisonOS/unison-devstack/issues
- Renderer issues: https://github.com/project-unisonOS/unison-experience-renderer/issues
