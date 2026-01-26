#!/usr/bin/env bash
set -euo pipefail

GX_HOME_DIR=${GX_HOME:-/var/lib/gx}
mkdir -p "${GX_HOME_DIR}"
export GX_HOME="${GX_HOME_DIR}"

if [[ $# -gt 0 ]]; then
  exec /opt/gx/bin/gx "$@"
fi

exec /opt/gx/bin/gx --help
