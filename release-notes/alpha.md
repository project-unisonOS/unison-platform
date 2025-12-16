# UnisonOS Alpha Release — {{VERSION}}

Built: {{BUILT_AT}}

## What’s new

- Alpha bundle release for UnisonOS evaluators (WSL2 + Linux VM + bare-metal installer).
- Bare-metal installer is full Ubuntu Server live-server media with embedded autoinstall payload (not a seed-only ISO).
- Includes `unisonos-manifest-{{VERSION}}.json` and `SHA256SUMS-{{VERSION}}.txt` for verification.

## MVP checklist (alpha)

- WSL2 install: expected (alpha; verify on your host)
- Linux VM install: expected (alpha; verify on your hypervisor)
- Bare-metal install: expected (alpha; verify on target hardware/VM)
- Boots/starts to “ready” automatically: expected once Docker + services start
- Inference works end-to-end (default interaction model is Qwen): expected after models are installed
- Renderer reachable and usable: expected after services are up
- One-command smoke test: see evaluator guide
- Recovery message if model missing: expected (install models per docs)

## Downloads

GitHub Release assets:

{{ASSETS_BULLETS}}

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
