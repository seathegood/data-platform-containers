# Apache Hive Metastore Container

Lightweight wrapper around the Apache Hive standalone metastore distribution. Designed to run with an external PostgreSQL database.

## Port
- 9083/tcp — Thrift metastore service

## Required Environment
- `METASTORE_DB_HOST`
- `METASTORE_DB_PASS`

Optional variables are documented in `container.yaml`.

## Usage
```
docker run -d \
  --name hive-metastore \
  -p 9083:9083 \
  -e METASTORE_DB_HOST=db \
  -e METASTORE_DB_PASS=change-me \
  ghcr.io/your-org/hive-metastore:3.1.3
```

`tests/metadata.py` validates the metadata schema and required environment variables.
