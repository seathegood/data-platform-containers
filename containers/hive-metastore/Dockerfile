# syntax=docker/dockerfile:1.6

ARG BASE_IMAGE=eclipse-temurin:11-jre-jammy
FROM ${BASE_IMAGE}

ARG PACKAGE_VERSION
ARG TARBALL_URI
ARG TARBALL_SHA512

ENV HIVE_HOME="/opt/hive-metastore"

RUN --mount=type=cache,target=/var/cache/apt <<'EOS'
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends wget gosu procps python3 python3-venv ca-certificates netcat-openbsd tini
rm -rf /var/lib/apt/lists/*
EOS

RUN --mount=type=cache,target=/tmp/downloads <<'EOS'
set -euo pipefail
mkdir -p /tmp/downloads
wget -q "${TARBALL_URI}" -O /tmp/downloads/hive-metastore.tar.gz
if [ -n "${TARBALL_SHA512}" ]; then
  echo "${TARBALL_SHA512}  /tmp/downloads/hive-metastore.tar.gz" | sha512sum -c -
fi
EOS

RUN <<'EOS'
set -euo pipefail
mkdir -p /opt
cd /opt
rm -rf hive-standalone-metastore-*
tar -xzf /tmp/downloads/hive-metastore.tar.gz
mv hive-standalone-metastore-${PACKAGE_VERSION}-bin hive-metastore-${PACKAGE_VERSION}
ln -sfn hive-metastore-${PACKAGE_VERSION} hive-metastore
EOS

COPY files/ /opt/hive-metastore-overlay/
RUN <<'EOS'
set -euo pipefail
if [ -d /opt/hive-metastore-overlay ]; then
  cp -R /opt/hive-metastore-overlay/. ${HIVE_HOME}/
fi
chmod +x ${HIVE_HOME}/bin/metastore-entrypoint.sh
EOS

EXPOSE 9083/tcp
WORKDIR ${HIVE_HOME}

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
  CMD nc -z 127.0.0.1 9083 || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/hive-metastore/bin/metastore-entrypoint.sh"]
CMD ["run"]
