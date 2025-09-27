# syntax=docker/dockerfile:1.6

ARG BASE_IMAGE=eclipse-temurin:17-jre-jammy
FROM ${BASE_IMAGE}

ARG PACKAGE_VERSION
ARG UPSTREAM_URI
ARG DEB_SHA256

ENV DEBIAN_FRONTEND=noninteractive

RUN --mount=type=cache,target=/var/cache/apt <<'EOS'
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends gnupg curl ca-certificates procps tini gosu iproute2
rm -rf /var/lib/apt/lists/*
EOS

RUN --mount=type=cache,target=/tmp/downloads <<'EOS'
set -euo pipefail
mkdir -p /tmp/downloads
curl -fsSL "${UPSTREAM_URI}" -o /tmp/downloads/unifi.deb
if [ -n "${DEB_SHA256}" ]; then
  echo "${DEB_SHA256}  /tmp/downloads/unifi.deb" | sha256sum -c -
fi
EOS

RUN dpkg -i /tmp/downloads/unifi.deb || apt-get -f install -y && rm -rf /var/lib/apt/lists/*

COPY files/ /opt/unifi-overlay/
RUN <<'EOS'
set -euo pipefail
if [ -d /opt/unifi-overlay ]; then
  cp -R /opt/unifi-overlay/. /usr/lib/unifi/
fi
mkdir -p /var/lib/unifi
chown -R 1000:1000 /var/lib/unifi
EOS

VOLUME ["/var/lib/unifi"]
EXPOSE 8443/tcp 8080/tcp 3478/udp

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD wget -qO- http://127.0.0.1:8080/status | grep -q \"ok\"

COPY files/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER 1000:1000
WORKDIR /usr/lib/unifi
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["start"]
