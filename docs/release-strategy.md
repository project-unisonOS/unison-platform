---
title: Platform release strategy
---

# Platform release strategy

UnisonOS platform downloads are delivered as immutable GitHub Release assets
in `project-unisonOS/unison-platform`.

## Current channel

The current channel uses tags shaped like `vX.Y.Z-preview.N`. Every release is
marked as a prerelease and an unsupported, pre-production software preview.
It is suitable for evaluating the software delivery and installer contracts,
but not for production data or claims of hardware compatibility.

The primary download is the signed x86_64 appliance bundle. Its manifest pins
every runtime image by digest. Checksums, signatures, SBOM, provenance,
source correspondence, and a machine-readable support record are published
beside it.

Release tags and assets are immutable. If a candidate is defective, publish a
new preview number. Do not move a tag or replace an asset.

## Promotion to a supported channel

A future supported release requires all software gates plus the deferred
physical-hardware matrix. At minimum that includes clean installation, restart,
power-loss recovery, update activation, rollback, backup and restore, peripheral
behavior, thermal behavior, and documented hardware compatibility.

Until those checks pass, documentation and release metadata must continue to
say `unsupported-preview`. Historical `v0.5.0-alpha.1` WSL, VM, and ISO files
remain evaluator artifacts only and are not current appliance downloads.

## Download authority

The release page and its `RELEASE_NOTES.md` asset define the files for that
version. Website pages should link to the current release page or to an exact
asset in that release. Rolling target tags and guessed filenames are not part
of the current contract.
