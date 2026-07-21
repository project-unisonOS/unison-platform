# Pre-Milestone-2 Checklist

Use this checklist to avoid carrying avoidable Milestone 1 ambiguity into Milestone 2 work.

This is intentionally short. The goal is to confirm the Milestone 1 baseline is real enough to build from, not to keep polishing it indefinitely.

## 1. Freeze the Milestone 1 baseline

- [ ] Confirm the supported Milestone 1 install path remains Ubuntu 24.04 native on x86_64.
- [ ] Confirm the canonical Milestone 1 runtime contract is still centered on:
  - `install-native.sh`
  - `unisonctl`
  - `.env.native.template`
  - `compose/compose.native.yaml`
- [ ] Confirm evaluator channels (WSL2, Linux VM, bare-metal ISO) remain explicitly secondary.

## 2. Run one real Milestone 1 validation pass

- [ ] Run the native install path on a real or representative Ubuntu 24.04 target.
- [ ] Verify `/etc/unison/platform.env` is seeded from the native template.
- [ ] Verify first start remains blocked until placeholder/development values are replaced.
- [ ] Verify `unisonctl status` and `unisonctl health` behave as expected.
- [ ] Verify the renderer is reachable.
- [ ] Verify at least one golden-path interaction works.
- [ ] If practical, verify restart/recovery once via `unisonctl restart` or equivalent validation script.

## 3. Capture the Milestone 1 boundary

- [ ] Write down what Milestone 1 is considered done enough to preserve.
- [ ] Write down the known gaps that are intentionally carried forward.
- [ ] Decide what Milestone 2 is allowed to change without re-opening the Milestone 1 contract.

## 4. Optional but useful release check

- [ ] Run one GitHub Actions or equivalent release dry run for the alpha release flow.
- [ ] Confirm the staged/native-first release assets appear as expected.
- [ ] Confirm evaluator artifacts remain secondary in release notes and release outputs.

## 5. Do not block Milestone 2 on polish-only work

Avoid delaying Milestone 2 for:

- broader docs information architecture cleanup
- deeper compose/runtime refactors not required by the next milestone
- evaluator-channel perfection
- release automation redesign beyond what is needed to keep Milestone 1 supportable

## Exit criterion

You are ready to begin Milestone 2 when:

- the Milestone 1 native path is validated once for real
- the Milestone 1 contract is written down clearly enough to avoid accidental drift
- the remaining gaps are known and consciously accepted
