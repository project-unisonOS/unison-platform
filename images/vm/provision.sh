#!/usr/bin/env bash
set -euo pipefail

# Packer provisioning script for UnisonOS VM images.
# Assumes running as a sudo-capable user inside the VM.

VERSION="${UNISON_VERSION:-edge}"
MODEL_FLAVOR="${UNISON_MODEL_FLAVOR:-default}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  ca-certificates curl gnupg lsb-release \
  docker.io docker-compose-plugin git

systemctl enable docker
systemctl start docker

if [ ! -d /opt/unison-platform ]; then
  git clone https://github.com/project-unisonOS/unison-platform.git /opt/unison-platform
fi

cd /opt/unison-platform
git fetch --tags || true

if git rev-parse "refs/tags/${VERSION}" >/dev/null 2>&1; then
  git checkout "${VERSION}"
else
  git checkout main
fi

cp images/out/unisonos-vm-${VERSION}/models.json /opt/unison-platform/images/out/models.json || true

ENV=prod docker compose -f docker-compose.prod.yml pull
ENV=prod docker compose -f docker-compose.prod.yml up -d

echo "Provisioning complete for UnisonOS ${VERSION} (flavor=${MODEL_FLAVOR})"
