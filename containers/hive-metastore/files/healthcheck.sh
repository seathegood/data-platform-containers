#!/bin/sh
# shellcheck shell=sh

set -eu
command -v nc > /dev/null || { echo "nc is required"; exit 1; }
command -v xxd > /dev/null || { echo "xxd is required"; exit 1; }

HOST="${HIVE_METASTORE_HOST:-localhost}"
PORT="${HIVE_METASTORE_PORT:-9083}"
SCHEMA_VERSION="${SCHEMA_VERSION:-4.1.0}"

if [ ! -f /tmp/metastore-ready ]; then
  [ -t 1 ] && echo "Metastore starting"
  exit 1
fi

if ! nc -z "$HOST" "$PORT"; then
  echo "Metastore TCP port $PORT not open on $HOST"
  exit 1
fi


EXPECTED_VERSION="${SCHEMA_VERSION}"

VERSION_ROW=$(PGPASSWORD="$METASTORE_DB_PASSWORD" psql -h "$HOST" -U "$METASTORE_DB_USER" -d "$METASTORE_DB" -Atc "SELECT version FROM VERSION;" 2>/dev/null || echo "")

if [ "$VERSION_ROW" != "$EXPECTED_VERSION" ]; then
  echo "Hive schema version is '$VERSION_ROW', expected '$EXPECTED_VERSION'"
  exit 1
fi
