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
