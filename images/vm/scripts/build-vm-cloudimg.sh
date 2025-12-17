#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"
CACHE_DIR="${ROOT_DIR}/images/cache"

VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"
VM_DISK_GB="${VM_DISK_GB:-32}"

UBUNTU_CLOUDIMG_URL="${UBUNTU_CLOUDIMG_URL:-https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img}"
UBUNTU_CLOUDIMG_SHA256="${UBUNTU_CLOUDIMG_SHA256:-}"

IMG_NAME="$(basename "${UBUNTU_CLOUDIMG_URL}")"
SRC_IMG="${CACHE_DIR}/${IMG_NAME}"
QCOW_OUT="${OUT_ROOT}/unisonos-linux-vm-${VERSION}.qcow2"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

mkdir -p "${OUT_ROOT}" "${CACHE_DIR}"

SUDO=""
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  SUDO="sudo"
fi

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing $1" >&2; exit 127; }
}

need_cmd curl
need_cmd qemu-img
need_cmd qemu-nbd
need_cmd lsblk
need_cmd mount
need_cmd umount

echo "[vm/cloudimg] version=${VERSION}"
echo "[vm/cloudimg] ubuntu_cloudimg_url=${UBUNTU_CLOUDIMG_URL}"
echo "[vm/cloudimg] ubuntu_cloudimg_cache=${SRC_IMG}"

if [ ! -f "${SRC_IMG}" ]; then
  echo "[vm/cloudimg] downloading ubuntu cloud image..."
  curl -fsSL "${UBUNTU_CLOUDIMG_URL}" -o "${SRC_IMG}"
fi
if [ -n "${UBUNTU_CLOUDIMG_SHA256}" ]; then
  echo "${UBUNTU_CLOUDIMG_SHA256}  ${SRC_IMG}" | sha256sum -c -
fi

rm -f "${QCOW_OUT}"
qemu-img convert -O qcow2 "${SRC_IMG}" "${QCOW_OUT}"
qemu-img resize "${QCOW_OUT}" "${VM_DISK_GB}G" >/dev/null

echo "[vm/cloudimg] mounting image via nbd to stage bundle..."
NBD_DEV="${NBD_DEV:-/dev/nbd0}"
MNT="${WORKDIR}/mnt"
mkdir -p "${MNT}"

cleanup_nbd() {
  set +e
  ${SUDO} umount "${MNT}" >/dev/null 2>&1 || true
  ${SUDO} qemu-nbd --disconnect "${NBD_DEV}" >/dev/null 2>&1 || true
}
trap cleanup_nbd EXIT

${SUDO} modprobe nbd max_part=8 || true
${SUDO} qemu-nbd --connect "${NBD_DEV}" "${QCOW_OUT}"
${SUDO} partprobe "${NBD_DEV}" >/dev/null 2>&1 || true
sleep 1

root_part="$(${SUDO} lsblk -nrpo NAME,FSTYPE "${NBD_DEV}" | awk '$2=="ext4"{print $1}' | head -n 1)"
if [ -z "${root_part}" ]; then
  echo "[vm/cloudimg] ERROR: unable to locate ext4 root partition on ${NBD_DEV}" >&2
  ${SUDO} lsblk "${NBD_DEV}" >&2 || true
  exit 1
fi

${SUDO} mount "${root_part}" "${MNT}"

${SUDO} mkdir -p "${MNT}/opt/unison-platform"
${SUDO} cp "${ROOT_DIR}/docker-compose.prod.yml" "${MNT}/opt/unison-platform/docker-compose.yml"
${SUDO} cp "${ROOT_DIR}/.env.template" "${MNT}/opt/unison-platform/.env.template"
${SUDO} cp -R "${ROOT_DIR}/config" "${MNT}/opt/unison-platform/config"
${SUDO} cp -R "${ROOT_DIR}/compose" "${MNT}/opt/unison-platform/compose"
${SUDO} cp -R "${ROOT_DIR}/installer" "${MNT}/opt/unison-platform/installer"
${SUDO} cp -R "${ROOT_DIR}/model-packs" "${MNT}/opt/unison-platform/model-packs"
${SUDO} mkdir -p "${MNT}/opt/unison-platform/scripts"
${SUDO} cp "${ROOT_DIR}/scripts/health-check.sh" "${MNT}/opt/unison-platform/scripts/" || true

FIRSTBOOT_SERVICE="${ROOT_DIR}/images/vm/assets/unisonos-firstboot.service"
FIRSTBOOT_SH="${ROOT_DIR}/images/vm/assets/unisonos-firstboot.sh"
${SUDO} install -m 0644 "${FIRSTBOOT_SERVICE}" "${MNT}/etc/systemd/system/unisonos-firstboot.service"
${SUDO} install -m 0755 "${FIRSTBOOT_SH}" "${MNT}/usr/local/sbin/unisonos-firstboot.sh"
${SUDO} mkdir -p "${MNT}/etc/systemd/system/multi-user.target.wants"
${SUDO} ln -sf /etc/systemd/system/unisonos-firstboot.service "${MNT}/etc/systemd/system/multi-user.target.wants/unisonos-firstboot.service"

${SUDO} umount "${MNT}"
${SUDO} qemu-nbd --disconnect "${NBD_DEV}"
trap 'rm -rf "${WORKDIR}"' EXIT

echo "[vm/cloudimg] wrote ${QCOW_OUT}"
