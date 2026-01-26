# syntax=docker/dockerfile:1.5
# Build arguments provided via containers/devpi-server/container.yaml
ARG BASE_IMAGE
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS runtime

ARG DEVPI_SERVER_VERSION
ARG DEVPI_CLIENT_VERSION
ARG DEVPI_UID
ARG DEVPI_GID

ENV PATH="/opt/devpi/bin:${PATH}" \
    DEVPI_SERVERDIR="/var/lib/devpi" \
    DEVPI_HOST="0.0.0.0" \
    DEVPI_PORT="3141" \
    PYTHONUNBUFFERED="1"

# allow security updates for tini/curl
# hadolint ignore=DL3008
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends tini curl; \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/devpi; \
    /opt/devpi/bin/pip install --no-cache-dir --upgrade pip; \
    /opt/devpi/bin/pip install --no-cache-dir "devpi-server==${DEVPI_SERVER_VERSION}" "devpi-client==${DEVPI_CLIENT_VERSION}"

RUN set -eux; \
    addgroup --system --gid "${DEVPI_GID}" devpi; \
    adduser --system --uid "${DEVPI_UID}" --ingroup devpi --home /var/lib/devpi devpi; \
    mkdir -p /var/lib/devpi; \
    chown -R devpi:devpi /var/lib/devpi /opt/devpi

COPY files/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY files/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

VOLUME ["/var/lib/devpi"]
EXPOSE 3141

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD /usr/local/bin/healthcheck.sh

USER devpi
WORKDIR /var/lib/devpi

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD []
