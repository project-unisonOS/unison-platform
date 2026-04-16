# UnisonOS Alpha Release — {{VERSION}}

Built: {{BUILT_AT}}

## What’s new

- Milestone 1 native install route remains the primary supported path for UnisonOS on Ubuntu 24.04 x86_64.
- Alpha evaluator artifacts may also be included for WSL2, Linux VM, and bare-metal installer testing.
- Bare-metal installer is full Ubuntu Server live-server media with embedded autoinstall payload (not a seed-only ISO).
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

GitHub Release assets:

{{ASSETS_BULLETS}}

Bare-metal note:
- GitHub Releases limit individual assets to 2GB, so the bare-metal ISO is shipped as `unisonos-baremetal-{{VERSION}}.iso.part00`, `...part01`, etc.
- Reassemble before flashing:
  - `cat unisonos-baremetal-{{VERSION}}.iso.part* > unisonos-baremetal-{{VERSION}}.iso`

Canonical native install guide:
- https://github.com/project-unisonOS/unison-platform/blob/main/docs/deployment/ubuntu-native.md

Alpha evaluation guide:
- https://project-unisonos.github.io/developers/evaluate-alpha/

## Model packs

- Default profile: `alpha/default` (Qwen for interaction + planner)
- If models are missing, follow the prompt or see:
  - https://project-unisonos.github.io/developers/model-packs/

## Known issues

- Alpha quality; expect rough edges in first-run experience and hardware compatibility.
- VM images may take longer to boot on hosts without virtualization acceleration.

## Verification

- Verify `SHA256SUMS-{{VERSION}}.txt` against downloaded assets.

## Report bugs

- Packaging/install/release issues: https://github.com/project-unisonOS/unison-platform/issues
- Devstack issues: https://github.com/project-unisonOS/unison-devstack/issues
- Renderer issues: https://github.com/project-unisonOS/unison-experience-renderer/issues
