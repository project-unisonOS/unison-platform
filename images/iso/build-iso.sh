#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"
MODELS="${ROOT_DIR}/images/models.yaml"
VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"
FLAVOR="${MODEL_FLAVOR:-default}"
UBUNTU_VERSION="${UBUNTU_VERSION:-24.04}"

ARTIFACT_DIR="${OUT_ROOT}/unisonos-iso-${VERSION}"
SEED_ISO="${OUT_ROOT}/unisonos-autoinstall-seed-${VERSION}.iso"

mkdir -p "${ARTIFACT_DIR}/autoinstall"

render_models_manifest() {
  local target="${ARTIFACT_DIR}/autoinstall/models.json"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found; skipping models manifest rendering."
    return
  fi
  python3 - <<'PY' "${MODELS}" "${FLAVOR}" "${target}"
import json, sys
try:
    import yaml  # type: ignore
except ImportError:
    print("PyYAML not installed; writing passthrough manifest.")
    with open(sys.argv[3], "w") as fh:
        json.dump({"error": "PyYAML not installed"}, fh)
    sys.exit(0)

models_path, flavor, target = sys.argv[1], sys.argv[2], sys.argv[3]
with open(models_path) as fh:
    data = yaml.safe_load(fh) or {}

base = data.get("default", {})
selected = base.copy()
if flavor != "default":
    selected.update(data.get("flavors", {}).get(flavor, {}))

manifest = {
  "flavor": flavor,
  "provider": selected.get("provider"),
  "text_model": selected.get("text_model"),
  "multimodal_model": selected.get("multimodal_model"),
  "preload": bool(selected.get("preload", False)),
  "models": selected.get("models", [])
}

with open(target, "w") as fh:
    json.dump(manifest, fh, indent=2)
PY
}

write_autoinstall_stub() {
  cat > "${ARTIFACT_DIR}/autoinstall/user-data" <<'USERDATA'
#cloud-config
autoinstall:
  version: 1
  identity:
    hostname: unisonos
    username: unison
    password: "$6$unison$QKpsK2F5iVUE9VumXZhBxxDqjvYCyaY0lUD4iifz9Qpc2K05KkRQ9zCBVYb5FZygbh/Tg4SKFmZ1yFd1HTsIQ0"  # replace for production
  ssh:
    install-server: true
    allow-pw: true  # set false when ssh_authorized_keys is provided
  ssh_authorized_keys:
    - "ssh-rsa REPLACE_WITH_REAL_KEY"
  packages:
    - docker.io
    - docker-compose
    - git
  late-commands:
    - curtin in-target --target=/target -- bash -c "cd /opt && git clone https://github.com/project-unisonOS/unison-platform.git"
    - curtin in-target --target=/target -- bash -c "cd /opt/unison-platform && make up ENV=prod"
USERDATA

  cat > "${ARTIFACT_DIR}/autoinstall/meta-data" <<'METADATA'
instance-id: unisonos
local-hostname: unisonos
METADATA
}

write_metadata() {
  cat > "${ARTIFACT_DIR}/metadata.json" <<META
{
  "artifact": "unisonos-iso",
  "version": "${VERSION}",
  "model_flavor": "${FLAVOR}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "composer": "unison-platform/images/iso/build-iso.sh"
}
META

  cat > "${ARTIFACT_DIR}/README.md" <<'DOC'
UnisonOS Autoinstall Seed
=========================

This directory contains seeds for building a UnisonOS autoinstall ISO:
- autoinstall/user-data (cloud-init style) with late-commands to pull unison-platform
- autoinstall/meta-data
- models.json rendered from images/models.yaml
- metadata.json describing the artifact

Next steps: use tools like `xorriso`/`mkisofs` to bake these seeds into an Ubuntu Server ISO and emit
`unisonos-installer-<version>.iso`.
DOC
}

make_seed_iso() {
  local tool=""
  if command -v xorriso >/dev/null 2>&1; then
    tool="xorriso -as mkisofs"
  elif command -v genisoimage >/dev/null 2>&1; then
    tool="genisoimage"
  elif command -v mkisofs >/dev/null 2>&1; then
    tool="mkisofs"
  else
    echo "No ISO creation tool found (xorriso/genisoimage/mkisofs). Skipping seed ISO build."
    echo "Autoinstall seed files are available under ${ARTIFACT_DIR}/autoinstall"
    return
  fi

  echo "Building autoinstall seed ISO with ${tool}..."
  (cd "${ARTIFACT_DIR}/autoinstall" && \
    ${tool} -volid cidata -joliet -rock -o "${SEED_ISO}" user-data meta-data models.json)
  echo "Seed ISO written to ${SEED_ISO}"
}

render_models_manifest
write_autoinstall_stub
write_metadata
make_seed_iso

echo "ISO seed bundle written to ${ARTIFACT_DIR}"
