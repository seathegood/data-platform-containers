#!/usr/bin/env bash
set -euo pipefail

COMMAND=${1:-start}
shift || true

if [[ "${COMMAND}" == "start" ]]; then
  exec /usr/bin/java -Xmx"${JVM_HEAP_SIZE:-1024M}" -jar /usr/lib/unifi/lib/ace.jar "$@"
fi

exec "$COMMAND" "$@"
