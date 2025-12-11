#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"
MODELS="${ROOT_DIR}/images/models.yaml"
VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"
FLAVOR="${MODEL_FLAVOR:-default}"

ARTIFACT_DIR="${OUT_ROOT}/unisonos-wsl-${VERSION}"
TARBALL="${OUT_ROOT}/unisonos-wsl-${VERSION}.tar.gz"

mkdir -p "${ARTIFACT_DIR}"

copy_platform_bundle() {
  mkdir -p "${ARTIFACT_DIR}/bundle"
  cp "${ROOT_DIR}/docker-compose.prod.yml" "${ARTIFACT_DIR}/bundle/"
  cp "${ROOT_DIR}/.env.template" "${ARTIFACT_DIR}/bundle/.env.example"
  cp -R "${ROOT_DIR}/config" "${ARTIFACT_DIR}/bundle/config"
  cp -R "${ROOT_DIR}/compose" "${ARTIFACT_DIR}/bundle/compose"
}

render_models_manifest() {
  local target="${ARTIFACT_DIR}/bundle/models.json"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found; skipping models manifest rendering."
    return
  fi
  python3 - <<'PY' "${MODELS}" "${FLAVOR}" "${target}"
import json, os, sys
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

write_metadata() {
  cat > "${ARTIFACT_DIR}/metadata.json" <<META
{
  "artifact": "unisonos-wsl",
  "version": "${VERSION}",
  "model_flavor": "${FLAVOR}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "composer": "unison-platform/images/wsl/build-wsl.sh"
}
META
  cat > "${ARTIFACT_DIR}/README.md" <<'DOC'
UnisonOS WSL bundle
===================

This archive contains a WSL-friendly Unison Platform bundle:
- docker-compose.prod.yml + compose overrides
- .env.example template
- models.json rendered from images/models.yaml

Usage (WSL):
1) Install Docker inside WSL or enable Docker Desktop integration.
2) Extract this tarball in your WSL home.
3) cp bundle/.env.example bundle/.env and set secrets.
4) docker compose -f bundle/docker-compose.prod.yml up -d
5) Confirm services via health endpoints.
DOC
}

package_artifact() {
  rm -f "${TARBALL}"
  (cd "${OUT_ROOT}" && tar -czf "${TARBALL##${OUT_ROOT}/}" "$(basename "${ARTIFACT_DIR}")")
  echo "WSL bundle created at ${TARBALL}"
}

copy_platform_bundle
render_models_manifest
write_metadata
package_artifact
