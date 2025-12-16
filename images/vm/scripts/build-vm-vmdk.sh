#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_ROOT="${ROOT_DIR}/images/out"
VERSION="${VERSION:-$(cd "${ROOT_DIR}" && git describe --tags --always 2>/dev/null || echo dev)}"

QCOW="${OUT_ROOT}/unisonos-linux-vm-${VERSION}.qcow2"
VMDK="${OUT_ROOT}/unisonos-linux-vm-${VERSION}.vmdk"

command -v qemu-img >/dev/null 2>&1 || { echo "missing qemu-img (qemu-utils)" >&2; exit 1; }
test -f "${QCOW}"

rm -f "${VMDK}"
qemu-img convert -O vmdk "${QCOW}" "${VMDK}"
echo "[vm] wrote ${VMDK}"

