#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"
MODELS="${ROOT_DIR}/images/models.yaml"
VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"
FLAVOR="${MODEL_FLAVOR:-default}"

ARTIFACT_DIR="${OUT_ROOT}/unisonos-vm-${VERSION}"

mkdir -p "${ARTIFACT_DIR}"

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
# TODO: replace with real builders (e.g., qemu, vmware-iso)
variable "version" { type = string }
variable "model_flavor" { type = string }

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
- Start from Ubuntu cloud image (22.04/24.04)
- Provision Docker + unison-platform compose bundle
- Preload models per models.json (optional)
- Emit qcow2/vmdk artifacts named unisonos-vm-<version>.<ext>
DOC
}

render_models_manifest
write_packer_stub
write_metadata

echo "VM bundle written to ${ARTIFACT_DIR}"
