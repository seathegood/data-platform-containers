#!/usr/bin/env bash
set -euo pipefail

PORT=${DEVPI_PORT:-3141}
HOST=${DEVPI_HEALTHCHECK_HOST:-127.0.0.1}
URL="http://${HOST}:${PORT}/+status"

exec curl -fsS --max-time 5 "$URL" >/dev/null
