#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"
CACHE_DIR="${ROOT_DIR}/images/cache"

VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"
# Default to current Ubuntu 24.04.x live-server ISO; override via UBUNTU_ISO_URL for pinning.
UBUNTU_ISO_URL="${UBUNTU_ISO_URL:-https://releases.ubuntu.com/24.04/ubuntu-24.04.3-live-server-amd64.iso}"
UBUNTU_ISO_SHA256="${UBUNTU_ISO_SHA256:-}"

ISO_NAME="$(basename "${UBUNTU_ISO_URL}")"
UBUNTU_ISO="${CACHE_DIR}/${ISO_NAME}"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

PATCHROOT="${WORKDIR}/patch"
mkdir -p "${PATCHROOT}" "${CACHE_DIR}" "${OUT_ROOT}"

OUT_ISO="${OUT_ROOT}/unisonos-baremetal-installer-${VERSION}.iso"

echo "[baremetal] version=${VERSION}"
echo "[baremetal] ubuntu_iso_url=${UBUNTU_ISO_URL}"
echo "[baremetal] ubuntu_iso_cache=${UBUNTU_ISO}"

if [ ! -f "${UBUNTU_ISO}" ]; then
  echo "[baremetal] downloading ubuntu installer iso..."
  curl -fsSL "${UBUNTU_ISO_URL}" -o "${UBUNTU_ISO}"
fi

if [ -n "${UBUNTU_ISO_SHA256}" ]; then
  echo "${UBUNTU_ISO_SHA256}  ${UBUNTU_ISO}" | sha256sum -c -
fi

echo "[baremetal] extracting boot configs for patch..."
mkdir -p "${PATCHROOT}/boot/grub" "${PATCHROOT}/nocloud/payload"
xorriso -osirrox on -indev "${UBUNTU_ISO}" -extract /boot/grub/grub.cfg "${PATCHROOT}/boot/grub/grub.cfg" >/dev/null
xorriso -osirrox on -indev "${UBUNTU_ISO}" -extract /boot/grub/loopback.cfg "${PATCHROOT}/boot/grub/loopback.cfg" >/dev/null
chmod -R u+rwX "${PATCHROOT}"

echo "[baremetal] adding nocloud payload..."
cp -R "${ROOT_DIR}/images/baremetal/nocloud/"* "${PATCHROOT}/nocloud/"

# Bundle the platform repo content needed by the installer (kept minimal and reproducible).
PAYLOAD_TAR="${PATCHROOT}/nocloud/payload/unison-platform-bundle.tar.gz"
tar -czf "${PAYLOAD_TAR}" -C "${ROOT_DIR}" \
  .env.template \
  compose \
  config \
  installer \
  model-packs \
  scripts \
  Makefile \
  images/models.yaml

echo "[baremetal] patching grub configs for autoinstall..."
patch_grub() {
  local path="$1"
  [ -f "${path}" ] || return 0
  # Append autoinstall datasource args to kernel command line (idempotent).
  if rg -n "ds=nocloud" "${path}" >/dev/null 2>&1; then
    return 0
  fi
  # Ubuntu live-server uses "linux" or "linuxefi" lines; patch both.
  sed -i \
    -e 's@\\(linux[^\\n]*\\)---@\\1 autoinstall ds=nocloud\\;s=/cdrom/nocloud/ ---@' \
    -e 's@\\(linuxefi[^\\n]*\\)---@\\1 autoinstall ds=nocloud\\;s=/cdrom/nocloud/ ---@' \
    "${path}" || true
}

patch_grub "${PATCHROOT}/boot/grub/grub.cfg"
patch_grub "${PATCHROOT}/boot/grub/loopback.cfg"

echo "[baremetal] repacking bootable iso..."
rm -f "${OUT_ISO}"
xorriso \
  -indev "${UBUNTU_ISO}" \
  -outdev "${OUT_ISO}" \
  -boot_image any replay \
  -map "${PATCHROOT}/nocloud" /nocloud \
  -map "${PATCHROOT}/boot/grub/grub.cfg" /boot/grub/grub.cfg \
  -map "${PATCHROOT}/boot/grub/loopback.cfg" /boot/grub/loopback.cfg \
  -volid "UNISONOS_${VERSION}" \
  -report_about warning

echo "[baremetal] wrote ${OUT_ISO}"
