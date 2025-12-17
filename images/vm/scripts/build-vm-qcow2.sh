#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"

VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"
VM_DISK_GB="${VM_DISK_GB:-32}"
VM_RAM_MB="${VM_RAM_MB:-4096}"
VM_CPUS="${VM_CPUS:-2}"
VM_INSTALL_TIMEOUT_S="${VM_INSTALL_TIMEOUT_S:-3600}"

ISO_PATH="${OUT_ROOT}/unisonos-baremetal-installer-${VERSION}.iso"
QCOW_OUT="${OUT_ROOT}/unisonos-linux-vm-${VERSION}.qcow2"

mkdir -p "${OUT_ROOT}"

should_use_cloudimg() {
  # GitHub-hosted runners and many dev environments do not have KVM available.
  # Our ISO+QEMU autoinstall path requires KVM (qemu -cpu host).
  if [ "${VM_BUILD_MODE:-}" = "cloudimg" ]; then
    return 0
  fi
  if [ ! -e /dev/kvm ]; then
    return 0
  fi
  return 1
}

run_qemu_install() {
  local qcow="$1"
  local iso="$2"

  command -v qemu-system-x86_64 >/dev/null 2>&1 || { echo "missing qemu-system-x86_64" >&2; return 127; }
  command -v qemu-img >/dev/null 2>&1 || { echo "missing qemu-img" >&2; return 127; }
  command -v timeout >/dev/null 2>&1 || { echo "missing timeout" >&2; return 127; }

  rm -f "${qcow}"
  qemu-img create -f qcow2 "${qcow}" "${VM_DISK_GB}G" >/dev/null

  echo "[vm] launching autoinstall (timeout=${VM_INSTALL_TIMEOUT_S}s)..."
  timeout "${VM_INSTALL_TIMEOUT_S}" \
    qemu-system-x86_64 \
      -machine accel=kvm:tcg \
      -cpu host \
      -m "${VM_RAM_MB}" \
      -smp "${VM_CPUS}" \
      -drive "file=${qcow},format=qcow2,if=virtio" \
      -cdrom "${iso}" \
      -boot d \
      -netdev user,id=net0 \
      -device virtio-net-pci,netdev=net0 \
      -serial stdio \
      -display none
}

ensure_installer_iso() {
  if [ -f "${ISO_PATH}" ]; then
    return 0
  fi
  echo "[vm] installer ISO not found; building ${ISO_PATH}"
  (cd "${ROOT_DIR}" && VERSION="${VERSION}" make baremetal-iso)
}

run_in_docker() {
  echo "[vm] qemu-system-x86_64 not available locally; running build in Docker."
  docker run --rm --privileged \
    -v "${ROOT_DIR}:/work" \
    -w /work \
    ubuntu:24.04 \
    bash -lc "set -euo pipefail; \
      apt-get update >/dev/null; \
      DEBIAN_FRONTEND=noninteractive apt-get install -y qemu-system-x86 qemu-utils xorriso curl python3 ca-certificates >/dev/null; \
      VERSION='${VERSION}' VM_DISK_GB='${VM_DISK_GB}' VM_RAM_MB='${VM_RAM_MB}' VM_CPUS='${VM_CPUS}' VM_INSTALL_TIMEOUT_S='${VM_INSTALL_TIMEOUT_S}' \
        bash images/vm/scripts/build-vm-qcow2.sh"
}

echo "[vm] version=${VERSION}"
if should_use_cloudimg; then
  echo "[vm] using cloud-image build path (no KVM required)"
  exec bash "${ROOT_DIR}/images/vm/scripts/build-vm-cloudimg.sh"
fi

ensure_installer_iso

if command -v qemu-system-x86_64 >/dev/null 2>&1; then
  run_qemu_install "${QCOW_OUT}" "${ISO_PATH}"
else
  run_in_docker
fi

echo "[vm] wrote ${QCOW_OUT}"
