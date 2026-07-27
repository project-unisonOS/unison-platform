# Minimal platform image placeholder for GHCR publishing.
# Provides compose files and README for runtime orchestration use.
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

WORKDIR /opt/unison-platform

COPY README.md docker-compose.prod.yml ./
COPY compose ./compose

LABEL org.opencontainers.image.source="https://github.com/project-unisonOS/unison-platform" \
      org.opencontainers.image.description="UnisonOS platform orchestration bundle"

CMD ["cat", "/opt/unison-platform/README.md"]
