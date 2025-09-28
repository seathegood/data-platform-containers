# syntax=docker/dockerfile:1.6

ARG BASE_IMAGE=ubuntu:22.04
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

ARG PACKAGE_NAME
ARG PACKAGE_VERSION
ARG UPSTREAM_URI

LABEL org.opencontainers.image.title="${PACKAGE_NAME}" \
      org.opencontainers.image.version="${PACKAGE_VERSION}"

ENV PACKAGE_NAME="${PACKAGE_NAME}" \
    PACKAGE_VERSION="${PACKAGE_VERSION}"

# Install OS dependencies here. Split steps so caching works well.
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt bash <<'EOS'
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends curl ca-certificates
rm -rf /var/lib/apt/lists/*
EOS

# Download the upstream artifact. Replace with logic appropriate for the package.
RUN --mount=type=cache,target=/tmp/downloads bash <<'EOS'
set -euo pipefail
mkdir -p /tmp/downloads
curl -fsSL "${UPSTREAM_URI}" -o /tmp/downloads/${PACKAGE_NAME}-${PACKAGE_VERSION}
EOS

# Copy overlay files provided by the package definition.
COPY files/ /opt/app/

# Provide a healthcheck placeholder.
HEALTHCHECK CMD /opt/app/bin/healthcheck || exit 1

ENTRYPOINT ["/opt/app/bin/start.sh"]
CMD []
