# Apache Hive Metastore Container

Packaged Apache Hive standalone metastore with baked-in PostgreSQL schema bootstrapping.

## Port
- 9083/tcp — Thrift metastore service

## Required Environment
- `METASTORE_DB_HOST`
- `METASTORE_DB`
- `METASTORE_DB_USER`
- `METASTORE_DB_PASSWORD`

Recommended defaults for `METASTORE_DB_PORT` (5432) and `METASTORE_PORT` (9083) are provided in `container.yaml` and can be overridden as needed.

## Usage
```bash
docker run -d \
  --name hive-metastore \
  -p 9083:9083 \
  -e METASTORE_DB_HOST=db \
  -e METASTORE_DB=metastore \
  -e METASTORE_DB_USER=metastore \
  -e METASTORE_DB_PASSWORD=change-me \
  seathegood/hive-metastore:4.1.0
```

`tests/metadata.py` validates the metadata schema and environment requirements defined in `container.yaml`.

## Schema bootstrapping and upgrades
- If `hive-site.xml` is not mounted, the entrypoint generates one using the Postgres env vars.
- If the `VERSION` table is missing, the entrypoint applies `hive-schema-<SCHEMA_VERSION>.postgres.sql`.
- If the schema version differs from `SCHEMA_VERSION`, it applies the matching upgrade script when present; otherwise, startup fails to avoid drift.

## Healthcheck
The bundled healthcheck waits for `/tmp/metastore-ready`, probes the thrift port, and verifies the schema version via `psql`. Ensure `METASTORE_DB_USER/PASSWORD/DB/HOST/PORT` are set so the healthcheck can run.

## Quick test with Postgres
```bash
cat <<'EOF' > docker-compose.hms.yml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: metastore
      POSTGRES_USER: metastore
      POSTGRES_PASSWORD: change-me
  hive-metastore:
    image: ghcr.io/seathegood/data-platform-containers/hive-metastore:4.1.0
    depends_on:
      - postgres
    environment:
      METASTORE_DB_HOST: postgres
      METASTORE_DB: metastore
      METASTORE_DB_USER: metastore
      METASTORE_DB_PASSWORD: change-me
    ports:
      - "9083:9083"
EOF

docker compose -f docker-compose.hms.yml up
```
