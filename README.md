# Data Platform Containers

This repository curates the container images that power a self-hosted, production-ready data plane grounded in open standards. Each image bundles the operational glue, security hardening, and interoperability settings required to run Apache-centric analytics workloads in any Kubernetes or Docker environment.

## Why It Exists
- Deliver opinionated, supportable images for Airflow, Spark, and Hive Metastore without relying on closed SaaS offerings.
- Keep the platform portable across clouds by leaning on Apache open standards (Iceberg, Hive catalog, Spark SQL, Airflow DAGs).
- Share a single build-and-release toolchain so upgrades, compliance scans, and provenance metadata stay consistent across containers.

## Container Catalog
| Container | Purpose | Highlights |
| --- | --- | --- |
| `airflow` | Workflow orchestration tier | Based on `apache/airflow`, with pinned constraints, optional extras, and Git-friendly DAG volume mounts. |
| `spark` | Batch and streaming compute engine | Ships Spark 3.5, Iceberg runtime, AWS connectors, and a tiny entrypoint for `spark-submit` automation. |
| `hive-metastore` | Central Iceberg/Hive catalog service | Hardened multi-stage build, PostgreSQL schema bootstrapper, and health checks for readiness probes. |

Community contributions live under `containers/_template` and follow the same release and testing conventions. See the wiki entry [Container Development Methodologies](docs/wiki/container-development-methodologies.md) for deeper implementation patterns.

## Repository Layout
- `containers/` – source-of-truth for each image: metadata, Dockerfile, test hooks, and overlay files.
- `templates/` – shared Dockerfile fragments and helper scripts reused during builds.
- `scripts/` – automation for build/test/publish flows (e.g., `scripts/package.py`).
- `docs/` – operational runbooks, maintenance notes, and wiki-style guides.
- `.github/workflows/` – CI pipelines that lint, build, scan, and optionally publish artifacts.
- `Makefile` – convenience entrypoint for common developer tasks (`make build`, `make test`, etc.).

## Prerequisites
- Docker 20.10+ with BuildKit enabled (`DOCKER_BUILDKIT=1`).
- Python 3.10+ with `pip install -r requirements-dev.txt` (or `pyyaml` at minimum).
- GNU Make, Bash, and standard Unix tooling.

## Build and Test Locally
```bash
# Build a single image (outputs to docker image cache)
make build PACKAGE=spark

# Run the container's smoke tests and linters
make test PACKAGE=spark

# Build everything (useful before a release)
make build-all
```

Images are tagged according to `containers/<name>/container.yaml#publish`. CI automatically stamps provenance metadata and performs Trivy scans before pushes.

## Sample Deployments
The snippets below assume you built images locally with `make build PACKAGE=<name>`, producing tags such as `data-platform/<name>:local`. Swap in your registry coordinates when pulling from CI.

### Airflow (SequentialExecutor)
```bash
export AIRFLOW_IMAGE=data-platform/airflow:local
docker volume create airflow_home

# Initialize the metadata database (SQLite for demo purposes)
docker run --rm \
  -v airflow_home:/opt/airflow \
  "$AIRFLOW_IMAGE" \
  airflow db init

# Launch the webserver
docker run -d --name airflow-webserver \
  -p 8080:8080 \
  -v airflow_home:/opt/airflow \
  -e AIRFLOW__CORE__EXECUTOR=SequentialExecutor \
  -e AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:////opt/airflow/airflow.db \
  "$AIRFLOW_IMAGE" \
  webserver

# (Optional) start the scheduler in a companion container
docker run -d --name airflow-scheduler \
  -v airflow_home:/opt/airflow \
  "$AIRFLOW_IMAGE" \
  scheduler
```

### Spark Job Submission
```bash
export SPARK_IMAGE=data-platform/spark:local

# Run the bundled Pi example over a local[*] master
docker run --rm \
  "$SPARK_IMAGE" \
  --master local[2] \
  local:///opt/spark/examples/src/main/python/pi.py 100

# Submit one of your jobs mounted from the host
docker run --rm \
  -v "$(pwd)/jobs":/opt/jobs \
  "$SPARK_IMAGE" \
  --master local[4] \
  /opt/jobs/etl.py --catalog thrift://hive-metastore:9083
```

### Hive Metastore with PostgreSQL Backend
```bash
export HIVE_IMAGE=data-platform/hive-metastore:local
docker network create data-plane-demo >/dev/null 2>&1 || true

# Ephemeral PostgreSQL backing database
docker run -d --name hive-db --network data-plane-demo \
  -e POSTGRES_DB=metastore \
  -e POSTGRES_USER=hive \
  -e POSTGRES_PASSWORD=hivepassword \
  postgres:15-alpine

# Launch the Metastore
docker run -d --name hive-metastore --network data-plane-demo \
  -p 9083:9083 \
  -e METASTORE_DB_HOST=hive-db \
  -e METASTORE_DB_PORT=5432 \
  -e METASTORE_DB=metastore \
  -e METASTORE_DB_USER=hive \
  -e METASTORE_DB_PASSWORD=hivepassword \
  -e METASTORE_PORT=9083 \
  "$HIVE_IMAGE"
```

### Full Data Plane (Docker Compose)
```bash
cat <<'EOF' > docker-compose.yml
services:
  postgres-metastore:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: metastore
      POSTGRES_USER: hive
      POSTGRES_PASSWORD: hivepassword
    volumes:
      - postgres_data:/var/lib/postgresql/data

  postgres-airflow:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: airflow
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
    volumes:
      - postgres_airflow_data:/var/lib/postgresql/data

  hive-metastore:
    image: data-platform/hive-metastore:local
    depends_on:
      - postgres-metastore
    environment:
      METASTORE_DB_HOST: postgres-metastore
      METASTORE_DB_PORT: "5432"
      METASTORE_DB: metastore
      METASTORE_DB_USER: hive
      METASTORE_DB_PASSWORD: hivepassword
      METASTORE_PORT: "9083"
    ports:
      - "9083:9083"

  airflow-webserver:
    image: data-platform/airflow:local
    depends_on:
      - postgres-airflow
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres-airflow/airflow
    command: webserver
    ports:
      - "8080:8080"

  airflow-scheduler:
    image: data-platform/airflow:local
    depends_on:
      - airflow-webserver
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres-airflow/airflow
    command: scheduler

  spark-job:
    image: data-platform/spark:local
    profiles: ["jobs"]
    depends_on:
      - hive-metastore
    command: >-
      --master local[2]
      --conf spark.sql.catalog.hive=thrift://hive-metastore:9083
      local:///opt/spark/examples/src/main/python/pi.py 50

volumes:
  postgres_data:
  postgres_airflow_data:
EOF

# Seed the Airflow metadata database before bringing up the stack
docker compose run --rm airflow-webserver airflow db init

# Launch the platform
docker compose up -d
```

The compose example is intentionally minimal—wire in TLS, production storage, and distributed Spark clusters according to your deployment standards. Use `docker compose run --rm --profile jobs spark-job` to submit ad-hoc jobs or override the command for a custom workload. Refer to the wiki page [Extending the Data Platform](docs/wiki/extending-the-project.md) for best practices when promoting this demo into a production topology.

## Additional Documentation
- [Container Development Methodologies](docs/wiki/container-development-methodologies.md)
- [Extending the Data Platform](docs/wiki/extending-the-project.md)
- [Operations Runbooks](docs/runbooks/README.md)
- [Maintenance Checklist](docs/maintenance.md)

Contributions are welcome! Open a pull request with proposed improvements and include doc updates or tests alongside code changes.
