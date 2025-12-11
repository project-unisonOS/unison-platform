#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"
MODELS="${ROOT_DIR}/images/models.yaml"
VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"
FLAVOR="${MODEL_FLAVOR:-default}"
UBUNTU_VERSION="${UBUNTU_VERSION:-24.04}"
BASE_URL="https://cloud-images.ubuntu.com/releases/${UBUNTU_VERSION}/release"
BASE_IMAGE="ubuntu-${UBUNTU_VERSION}-server-cloudimg-amd64.img"

ARTIFACT_DIR="${OUT_ROOT}/unisonos-vm-${VERSION}"

mkdir -p "${ARTIFACT_DIR}"
TMP_IMAGE="${ARTIFACT_DIR}/${BASE_IMAGE}"
QCOW_OUT="${ARTIFACT_DIR}/unisonos-vm-${VERSION}.qcow2"
VMDK_OUT="${ARTIFACT_DIR}/unisonos-vm-${VERSION}.vmdk"

render_models_manifest() {
  local target="${ARTIFACT_DIR}/models.json"
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

write_packer_stub() {
  cat > "${ARTIFACT_DIR}/packer.pkr.hcl" <<'PKR'
# Packer stub for UnisonOS VM images (QCOW2/VMDK)
# Replace with real builders (e.g., qemu, vmware-iso) if Packer is available.
variable "version" { type = string }
variable "model_flavor" { type = string }

fetch_cloud_image() {
  if [ ! -f "${TMP_IMAGE}" ]; then
    echo "Downloading Ubuntu cloud image ${BASE_IMAGE}..."
    curl -fsSL "${BASE_URL}/${BASE_IMAGE}" -o "${TMP_IMAGE}"
  fi
}

emit_qcow2() {
  if ! command -v qemu-img >/dev/null 2>&1; then
    echo "qemu-img not found; install qemu-utils to generate qcow2/vmdk images." >&2
    return
  fi
  echo "Converting cloud image to qcow2..."
  cp "${TMP_IMAGE}" "${QCOW_OUT}"
}

emit_vmdk() {
  if ! command -v qemu-img >/dev/null 2>&1; then
    return
  fi
  echo "Converting qcow2 to vmdk..."
  qemu-img convert -O vmdk "${TMP_IMAGE}" "${VMDK_OUT}"
}

source "null" "placeholder" {}

build {
  name = "unisonos-vm"
  sources = ["source.null.placeholder"]
  provisioner "shell-local" {
    inline = [
      "echo Packer build placeholder for UnisonOS ${var.version} (${var.model_flavor})"
    ]
  }
}
PKR
}

write_metadata() {
  cat > "${ARTIFACT_DIR}/metadata.json" <<META
{
  "artifact": "unisonos-vm",
  "version": "${VERSION}",
  "model_flavor": "${FLAVOR}",
  "ubuntu_version": "${UBUNTU_VERSION}",
  "base_image": "${BASE_URL}/${BASE_IMAGE}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "composer": "unison-platform/images/vm/build-vm.sh"
}
META
  cat > "${ARTIFACT_DIR}/README.md" <<'DOC'
UnisonOS VM build bundle
========================

This directory holds stubs for building UnisonOS VM images:
- packer.pkr.hcl placeholder
- models.json rendered from images/models.yaml
- metadata.json describing the intended artifact

Next steps: replace the Packer stub with real qemu/vmware builders that:
- Start from Ubuntu 24.04 cloud image by default (22.04 optional via UBUNTU_VERSION)
- Provision Docker + unison-platform compose bundle
- Preload models per models.json (optional)
- Emit qcow2/vmdk artifacts named unisonos-vm-<version>.<ext>
DOC
}

render_models_manifest
write_packer_stub
write_metadata
fetch_cloud_image
emit_qcow2
emit_vmdk

echo "VM bundle written to ${ARTIFACT_DIR}"
