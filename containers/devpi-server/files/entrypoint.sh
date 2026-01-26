#!/usr/bin/env bash
set -euo pipefail

SERVERDIR=${DEVPI_SERVERDIR:-/var/lib/devpi}
HOST=${DEVPI_HOST:-0.0.0.0}
PORT=${DEVPI_PORT:-3141}
FLAGS=("--serverdir" "${SERVERDIR}" "--host" "${HOST}" "--port" "${PORT}")

if [[ -n "${DEVPI_SERVER_FLAGS:-}" ]]; then
  # shellcheck disable=SC2206
  FLAGS+=(${DEVPI_SERVER_FLAGS})
fi

mkdir -p "${SERVERDIR}"

if [[ $# -gt 0 ]]; then
  exec /opt/devpi/bin/devpi-server "$@"
fi

exec /opt/devpi/bin/devpi-server "${FLAGS[@]}"
