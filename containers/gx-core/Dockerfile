# syntax=docker/dockerfile:1.5
# Build arguments provided via containers/gx-core/container.yaml
ARG BASE_IMAGE
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS runtime

ARG GX_VERSION
ARG GX_UID
ARG GX_GID

ENV PATH="/opt/gx/bin:${PATH}" \
    GX_HOME="/var/lib/gx" \
    PYTHONUNBUFFERED="1"

# allow security updates for base packages
# hadolint ignore=DL3008
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends tini git curl; \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/gx; \
    /opt/gx/bin/pip install --no-cache-dir --upgrade pip; \
    /opt/gx/bin/pip install --no-cache-dir "great_expectations==${GX_VERSION}"

RUN set -eux; \
    addgroup --system --gid "${GX_GID}" gx; \
    adduser --system --uid "${GX_UID}" --ingroup gx --home /var/lib/gx gx; \
    mkdir -p /var/lib/gx; \
    chown -R gx:gx /var/lib/gx /opt/gx

COPY files/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

VOLUME ["/var/lib/gx"]

USER gx
WORKDIR /var/lib/gx

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["--help"]
