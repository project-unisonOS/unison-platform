# Platform builds and preview releases

The canonical downloadable appliance artifact is the signed x86_64 bundle
published by `.github/workflows/release.yml`. The initial release
channel is explicitly an unsupported software preview. Physical appliance
compatibility, install, update, rollback, and recovery validation remain
pending.

## Preview release contents

For version `vX.Y.Z-preview.N`, the workflow publishes:

- `unisonos-vX.Y.Z-preview.N-x86_64.tar`: signed install and update bundle
- `unisonos-vX.Y.Z-preview.N-manifest.json`: immutable runtime bill of materials
- `unisonos-vX.Y.Z-preview.N-images.env`: digest-pinned image inventory
- `unisonos-vX.Y.Z-preview.N-sources.json`: image-to-source correspondence
- `unisonos-vX.Y.Z-preview.N.spdx.json`: aggregate SPDX runtime inventory
- `unisonos-vX.Y.Z-preview.N-provenance.json`: bundle provenance statement
- `unisonos-vX.Y.Z-preview.N-support.json`: machine-readable support status
- `unisonos-preview-bundle-ed25519.pem`: preview verification key
- `SHA256SUMS` and `SHA256SUMS.ed25519`: asset integrity evidence
- Sigstore bundles for the JSON evidence and checksum inventory

The release notes are the download authority. Do not infer current assets from
older alpha releases.

## Build and publication controls

The workflow accepts only preview-formatted versions. It rebuilds every project
image from the exact source commits in
`releases/preview-source-correspondence.v1.json`, replaces mutable common-wheel
inputs with an immutable digest, and publishes only linux/amd64 images.

Each image receives BuildKit SBOM and provenance attestations, a keyless Cosign
signature, and a critical-severity vulnerability scan. The assembly job rejects
missing image evidence, records effective Dockerfile hashes, produces the signed
bundle, and verifies the complete release set before publication.

After publication, a separate job downloads the public GitHub Release assets,
verifies checksums and signatures, validates the bundle and provenance, runs an
installation transaction in a temporary prefix, and confirms incomplete or
tampered mirrors are rejected.

The previous tag-triggered alpha workflow was removed. Its WSL, VM, and ISO
assets are historical evaluator artifacts and are not part of the current
appliance download contract.

## Manual release

Dispatch `Unsupported preview release` from the `main` branch with a version
such as `v0.6.0-preview.1`. The repository secret
`PREVIEW_BUNDLE_SIGNING_KEY_PEM` must contain the private key matching
`releases/trust/preview-bundle-ed25519.pem`.

Preview signing trust is intentionally separate from a future production
release key. A supported release must also satisfy the tracked hardware
validation gates before the support record can change from
`unsupported-preview`.
