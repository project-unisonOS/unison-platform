# Minimal platform image placeholder for GHCR publishing.
# Provides compose files and README for runtime orchestration use.
FROM python:3.12-slim@sha256:fdab368dc2e04fab3180d04508b41732756cc442586f708021560ee1341f3d29

WORKDIR /opt/unison-platform

COPY README.md docker-compose.prod.yml ./
COPY compose ./compose

LABEL org.opencontainers.image.source="https://github.com/project-unisonOS/unison-platform" \
      org.opencontainers.image.description="UnisonOS platform orchestration bundle"

CMD ["cat", "/opt/unison-platform/README.md"]
