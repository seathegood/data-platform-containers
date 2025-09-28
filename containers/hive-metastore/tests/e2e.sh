#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
PACKAGE="hive-metastore"
NETWORK="${PACKAGE}-e2e"
POSTGRES_CONTAINER="${NETWORK}-postgres"
METASTORE_CONTAINER="${NETWORK}-app"
POSTGRES_IMAGE="postgres:15-alpine"
METASTORE_IMAGE="docker.io/seathegood/hive-metastore:latest"

cleanup() {
  status=$1
  if [ "$status" -ne 0 ]; then
    echo "\n==> Hive Metastore logs"
    docker logs "$METASTORE_CONTAINER" 2>/dev/null || true
    echo "\n==> Postgres logs"
    docker logs "$POSTGRES_CONTAINER" 2>/dev/null || true
  fi
  docker rm -f "$METASTORE_CONTAINER" >/dev/null 2>&1 || true
  docker rm -f "$POSTGRES_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
}
trap 'status=$?; cleanup "$status"; exit "$status"' EXIT

cd "$ROOT_DIR"

PACKAGE_CLI="$ROOT_DIR/scripts/package.py"
"$PACKAGE_CLI" build "$PACKAGE"
"$PACKAGE_CLI" test "$PACKAGE"

docker network create "$NETWORK" >/dev/null 2>&1 || true

docker run -d --rm \
  --name "$POSTGRES_CONTAINER" \
  --network "$NETWORK" \
  -e POSTGRES_USER=metastore \
  -e POSTGRES_PASSWORD=metastore \
  -e POSTGRES_DB=metastore \
  "$POSTGRES_IMAGE" >/dev/null

echo "Waiting for PostgreSQL to become ready..."
for attempt in $(seq 1 30); do
  if docker exec "$POSTGRES_CONTAINER" pg_isready -U metastore >/dev/null 2>&1; then
    POSTGRES_READY=1
    break
  fi
  sleep 2
done
if [ -z "${POSTGRES_READY:-}" ]; then
  echo "PostgreSQL failed to start"
  exit 1
fi

docker run -d --rm \
  --name "$METASTORE_CONTAINER" \
  --network "$NETWORK" \
  -e METASTORE_DB_HOST="$POSTGRES_CONTAINER" \
  -e METASTORE_DB=metastore \
  -e METASTORE_DB_USER=metastore \
  -e METASTORE_DB_PASSWORD=metastore \
  -e METASTORE_DB_PORT=5432 \
  -e METASTORE_PORT=9083 \
  -e HIVE_METASTORE_HOST=127.0.0.1 \
  "$METASTORE_IMAGE" >/dev/null

echo "Waiting for Hive Metastore health check..."
for attempt in $(seq 1 30); do
  status=$(docker inspect --format '{{if .State}}{{.State.Health.Status}}{{end}}' "$METASTORE_CONTAINER" 2>/dev/null || echo "starting")
  if [ "$status" = "healthy" ]; then
    METASTORE_HEALTHY=1
    break
  fi
  if [ "$status" = "unhealthy" ]; then
    echo "Hive Metastore reported unhealthy"
    exit 1
  fi
  sleep 10
done
if [ -z "${METASTORE_HEALTHY:-}" ]; then
  echo "Hive Metastore never reached healthy state"
  exit 1
fi

docker exec "$METASTORE_CONTAINER" /usr/local/bin/healthcheck.sh >/dev/null

SCHEMA_VERSION=$(docker exec "$POSTGRES_CONTAINER" \
  psql -U metastore -d metastore -Atc 'SELECT "SCHEMA_VERSION" FROM "VERSION" WHERE "VER_ID" = 1;' 2>/dev/null || echo "")
if [ -z "$SCHEMA_VERSION" ]; then
  echo "Failed to read schema version from PostgreSQL"
  exit 1
fi

echo "Hive schema version: $SCHEMA_VERSION"

echo "E2E pipeline completed successfully"
