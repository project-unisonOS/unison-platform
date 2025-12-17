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

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing $1" >&2; exit 127; }
}

need_cmd curl
need_cmd qemu-img
need_cmd virt-customize
need_cmd virt-copy-in

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

echo "[vm/cloudimg] installing base packages (docker, compose)..."
virt-customize -a "${QCOW_OUT}" \
  --install "ca-certificates,curl,docker.io,docker-compose-v2,cloud-init,openssh-server" \
  --run-command "systemctl disable ssh || true"

echo "[vm/cloudimg] staging platform bundle..."
STAGE="${WORKDIR}/bundle"
mkdir -p "${STAGE}/opt/unison-platform"
cp "${ROOT_DIR}/docker-compose.prod.yml" "${STAGE}/opt/unison-platform/docker-compose.yml"
cp "${ROOT_DIR}/.env.template" "${STAGE}/opt/unison-platform/.env.template"
cp -R "${ROOT_DIR}/config" "${STAGE}/opt/unison-platform/config"
cp -R "${ROOT_DIR}/compose" "${STAGE}/opt/unison-platform/compose"
cp -R "${ROOT_DIR}/installer" "${STAGE}/opt/unison-platform/installer"
cp -R "${ROOT_DIR}/model-packs" "${STAGE}/opt/unison-platform/model-packs"
mkdir -p "${STAGE}/opt/unison-platform/scripts"
cp "${ROOT_DIR}/scripts/health-check.sh" "${STAGE}/opt/unison-platform/scripts/" || true

virt-copy-in -a "${QCOW_OUT}" "${STAGE}/opt" /

echo "[vm/cloudimg] installing first-boot service..."
FIRSTBOOT_SERVICE="${ROOT_DIR}/images/vm/assets/unisonos-firstboot.service"
FIRSTBOOT_SH="${ROOT_DIR}/images/vm/assets/unisonos-firstboot.sh"
virt-customize -a "${QCOW_OUT}" \
  --upload "${FIRSTBOOT_SERVICE}:/etc/systemd/system/unisonos-firstboot.service" \
  --upload "${FIRSTBOOT_SH}:/usr/local/sbin/unisonos-firstboot.sh" \
  --run-command "chmod +x /usr/local/sbin/unisonos-firstboot.sh" \
  --run-command "mkdir -p /etc/systemd/system/multi-user.target.wants" \
  --run-command "ln -sf /etc/systemd/system/unisonos-firstboot.service /etc/systemd/system/multi-user.target.wants/unisonos-firstboot.service"

echo "[vm/cloudimg] wrote ${QCOW_OUT}"

