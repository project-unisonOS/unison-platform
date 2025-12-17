#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-${1:-}}"
if [ -z "${VERSION}" ]; then
  echo "Usage: VERSION=v0.5.0-alpha.1 $0 (or pass VERSION as first arg)" >&2
  exit 1
fi

DIST="${ROOT_DIR}/dist/${VERSION}"
OUT="${ROOT_DIR}/images/out"

rm -rf "${DIST}"
mkdir -p "${DIST}"

echo "[release-alpha] building artifacts VERSION=${VERSION}"
(cd "${ROOT_DIR}" && VERSION="${VERSION}" make baremetal-iso linux-vm image-wsl)

echo "[release-alpha] staging canonical asset names"

WSL_SRC="${OUT}/unisonos-wsl2-dev-${VERSION}.tar.gz"
WSL_DST="${DIST}/unisonos-wsl2-${VERSION}.tar.gz"
test -f "${WSL_SRC}"
cp "${WSL_SRC}" "${WSL_DST}"

QCOW_SRC="${OUT}/unisonos-linux-vm-${VERSION}.qcow2"
QCOW_DST="${DIST}/unisonos-linux-vm-${VERSION}.qcow2"
test -f "${QCOW_SRC}"
cp "${QCOW_SRC}" "${QCOW_DST}"

if [ -f "${OUT}/unisonos-linux-vm-${VERSION}.vmdk" ]; then
  cp "${OUT}/unisonos-linux-vm-${VERSION}.vmdk" "${DIST}/unisonos-linux-vm-${VERSION}.vmdk"
fi

ISO_SRC="${OUT}/unisonos-baremetal-installer-${VERSION}.iso"
ISO_DST="${DIST}/unisonos-baremetal-${VERSION}.iso"
test -f "${ISO_SRC}"
cp "${ISO_SRC}" "${ISO_DST}"

echo "[release-alpha] basic artifact safeguards"
iso_bytes="$(stat -c%s "${ISO_DST}")"
if [ "${iso_bytes}" -lt 1000000000 ]; then
  echo "[release-alpha] ERROR: ISO too small (${iso_bytes} bytes) - expected full installer ISO" >&2
  exit 1
fi
if [[ "$(basename "${ISO_DST}")" == *"seed"* ]] || [[ "$(basename "${ISO_DST}")" == *"autoinstall-seed"* ]]; then
  echo "[release-alpha] ERROR: ISO name indicates seed-only ISO: $(basename "${ISO_DST}")" >&2
  exit 1
fi
if command -v xorriso >/dev/null 2>&1; then
  if ! xorriso -indev "${ISO_DST}" -ls /casper 2>/dev/null | grep -q "squashfs"; then
    echo "[release-alpha] ERROR: ISO missing a casper squashfs; likely not a full installer ISO" >&2
    exit 1
  fi
fi

echo "[release-alpha] splitting bare-metal ISO for GitHub Releases (2GB asset limit)"
ISO_MAX_BYTES=2147483648
if [ "${iso_bytes}" -gt "${ISO_MAX_BYTES}" ]; then
  ISO_PREFIX="${DIST}/unisonos-baremetal-${VERSION}.iso.part"
  split -b 1900m -d -a 2 "${ISO_DST}" "${ISO_PREFIX}"
  rm -f "${ISO_DST}"
  cat > "${DIST}/unisonos-baremetal-${VERSION}.iso.REASSEMBLE.txt" <<EOF
Reassemble:
  cat unisonos-baremetal-${VERSION}.iso.part* > unisonos-baremetal-${VERSION}.iso

Verify:
  sha256sum -c SHA256SUMS-${VERSION}.txt
EOF
  part0="${ISO_PREFIX}00"
  part1="${ISO_PREFIX}01"
  test -f "${part0}"
  test -f "${part1}"
  for part in "${ISO_PREFIX}"*; do
    pbytes="$(stat -c%s "${part}")"
    if [ "${pbytes}" -gt "${ISO_MAX_BYTES}" ]; then
      echo "[release-alpha] ERROR: ISO part too large for GitHub Releases: $(basename "${part}") (${pbytes} bytes)" >&2
      exit 1
    fi
  done
else
  echo "[release-alpha] ISO is within GitHub Releases limit; keeping as single file"
fi

qcow_disk_bytes="$(stat -c%s "${QCOW_DST}")"
qcow_virtual_bytes="$(qemu-img info "${QCOW_DST}" | awk -F'[()]' '/virtual size/ {gsub(/[^0-9]/, "", $2); print $2; exit}')"
if [ -z "${qcow_virtual_bytes}" ]; then
  echo "[release-alpha] ERROR: unable to read qcow2 virtual size" >&2
  exit 1
fi
if [ "${qcow_virtual_bytes}" -lt 20000000000 ]; then
  echo "[release-alpha] ERROR: qcow2 virtual size too small (${qcow_virtual_bytes} bytes) - expected full VM disk" >&2
  exit 1
fi
if [ "${qcow_disk_bytes}" -lt 200000000 ]; then
  echo "[release-alpha] ERROR: qcow2 disk size too small (${qcow_disk_bytes} bytes) - likely incomplete build" >&2
  exit 1
fi

MANIFEST_DST="${DIST}/unisonos-manifest-${VERSION}.json"
python3 "${ROOT_DIR}/scripts/generate_release_manifest.py" \
  --version "${VERSION}" \
  --out "${MANIFEST_DST}" \
  --compose-file "${ROOT_DIR}/compose/compose.yaml" \
  --model-pack-profile "alpha/default" \
  --model-pack-manifest "${ROOT_DIR}/model-packs/alpha/default.json" \
  --assets-dir "${DIST}"

echo "[release-alpha] generating sha256 sums"
SHA_DST="${DIST}/SHA256SUMS-${VERSION}.txt"
(cd "${DIST}" && { ls -1 | LC_ALL=C sort | while read -r f; do [ "${f}" = "$(basename "${SHA_DST}")" ] && continue; sha256sum "${f}"; done; } > "$(basename "${SHA_DST}")")

if [ "${CI:-}" = "true" ] || [ "${RELEASE_CLEANUP:-}" = "1" ]; then
  echo "[release-alpha] CI cleanup: removing large intermediate files"
  rm -rf "${ROOT_DIR}/images/cache" || true
  rm -f "${OUT}/unisonos-baremetal-installer-${VERSION}.iso" || true
  rm -f "${OUT}/unisonos-linux-vm-${VERSION}.qcow2" || true
  rm -f "${OUT}/unisonos-linux-vm-${VERSION}.vmdk" || true
  rm -f "${OUT}/unisonos-wsl2-dev-${VERSION}.tar.gz" || true
  rm -f "${OUT}/unisonos-wsl-rootfs-${VERSION}.tar.gz" || true
  rm -rf "${OUT}/unisonos-wsl-${VERSION}" || true
fi

echo "[release-alpha] done: ${DIST}"
