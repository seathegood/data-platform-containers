#!/usr/bin/env bash
set -euo pipefail

if ! "$SPARK_HOME/bin/spark-submit" --version >/dev/null 2>&1; then
  echo "spark-submit failed"
  exit 1
fi

echo "spark runtime healthy"
