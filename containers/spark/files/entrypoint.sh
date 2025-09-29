#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "spark-submit" ]]; then
  shift
fi

exec "$SPARK_HOME/bin/spark-submit" "$@"
