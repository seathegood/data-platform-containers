#!/bin/sh
# shellcheck shell=sh

set -eu

command -v nc >/dev/null || { echo "nc is required"; exit 1; }
command -v psql >/dev/null || { echo "psql is required"; exit 1; }

SERVICE_HOST="${HIVE_METASTORE_HOST:-localhost}"
SERVICE_PORT="${HIVE_METASTORE_PORT:-9083}"
DB_HOST="${METASTORE_DB_HOST:-localhost}"
DB_PORT="${METASTORE_DB_PORT:-5432}"
SCHEMA_VERSION="${SCHEMA_VERSION:-4.1.0}"

if [ ! -f /tmp/metastore-ready ]; then
  [ -t 1 ] && echo "Metastore starting"
  exit 1
fi

if ! nc -z "$SERVICE_HOST" "$SERVICE_PORT"; then
  echo "Metastore TCP port $SERVICE_PORT not open on $SERVICE_HOST"
  exit 1
fi

: "${METASTORE_DB_USER:?METASTORE_DB_USER is required}"
: "${METASTORE_DB_PASSWORD:?METASTORE_DB_PASSWORD is required}"
: "${METASTORE_DB:?METASTORE_DB is required}"

EXPECTED_VERSION="${SCHEMA_VERSION}"

VERSION_ROW=$(PGPASSWORD="$METASTORE_DB_PASSWORD" \
  psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$METASTORE_DB_USER" \
    -d "$METASTORE_DB" \
    -Atc "SELECT \"SCHEMA_VERSION\" FROM \"VERSION\" WHERE \"VER_ID\" = 1;" \
    2>/dev/null || echo "")

if [ "$VERSION_ROW" != "$EXPECTED_VERSION" ]; then
  echo "Hive schema version is '$VERSION_ROW', expected '$EXPECTED_VERSION'"
  exit 1
fi
