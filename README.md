# Data Platform Containers

This repository curates container images that power a self-hosted, production-ready data plane grounded in open standards. Each image bundles the operational glue, security hardening, and interoperability settings required to run Apache-centric analytics workloads in any Kubernetes or Docker environment. The repo also serves as a portfolio piece: the workflows, tagging strategy, and documentation are written to explain the “why” as much as the “what.”

## Why It Exists
- Deliver opinionated, supportable images for Airflow, Spark, and Hive Metastore without closed SaaS dependencies.
- Keep the platform portable across clouds by leaning on Apache open standards (Iceberg, Spark SQL, Airflow DAGs) and self-hosted components.
- Share a single build-and-release toolchain so upgrades, compliance scans, and provenance metadata stay consistent across containers.
- Document the concepts (tagging policy, GHCR usage, change detection) to show how a small platform team can run a repeatable supply chain.

## Container Catalog
| Container | Purpose | Highlights |
| --- | --- | --- |
| `airflow` | Workflow orchestration tier | Based on `apache/airflow`, with pinned constraints, optional extras, and Git-friendly DAG volume mounts. |
| `spark` | Batch and streaming compute engine | Ships Spark 4.0, Iceberg runtime, AWS connectors, and a tiny entrypoint for `spark-submit` automation. |
| `hive-metastore` | Central Iceberg/Hive catalog service | Hardened multi-stage build, PostgreSQL schema bootstrapper, and health checks for readiness probes. |
| `devpi-server` | Private PyPI cache and index | Ships devpi-server/client, non-root runtime, and healthcheck; persist `/var/lib/devpi`. |
| `gx-core` | Great Expectations CLI runtime | Packaged GX Core in a venv with non-root user and persistent `/var/lib/gx`. |

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

# Publish to GHCR (requires GHCR credentials)
make publish PACKAGE=spark
```

Images are tagged according to `containers/<name>/container.yaml#publish`. CI automatically stamps provenance metadata, adds `sha-<git>` tags, and performs Trivy scans before pushes.

## Tagging & Registry (GHCR)
- Registry: `ghcr.io/seathegood/data-platform-containers/<slug>`
- Tags: `latest` on every push, semantic version tags (`x`, `x.y`, `x.y.z`) when `version.current` is set, `sha-<12char>` from CI for provenance, and optional `stable` during releases.
- Local builds also tag `<slug>:local` for compose-based workflows.
- Digests are the immutable source of truth; mutable tags are conveniences that always point to a known digest recorded by CI.

## Sample Deployments
The snippets below assume you built images locally with `make build PACKAGE=<name>`, producing tags such as `<slug>:local`. Swap in GHCR coordinates when pulling from CI (for example, `ghcr.io/seathegood/data-platform-containers/airflow-runtime:latest`).

### Airflow (SequentialExecutor)
```bash
export AIRFLOW_IMAGE=ghcr.io/seathegood/data-platform-containers/airflow-runtime:latest
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

For deployments behind an ALB with OIDC, enable Airflow’s FAB remote-user auth manager and the bundled `webserver_config.py`; see `containers/airflow/README.md` for the header/proxy pattern. Username/password auth remains the default in the examples above.

For additional local flows:
- Spark MinIO compose smoke: `docker compose -f docker-compose.spark.local.yml up --exit-code-from spark-smoke`
- Airflow ALB/OIDC local stack: `docker compose -f docker-compose.airflow.local.yml up` (uses `airflow-runtime:local` and an Nginx header proxy)

### Spark Job Submission
```bash
export SPARK_IMAGE=ghcr.io/seathegood/data-platform-containers/spark-runtime:latest

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
export HIVE_IMAGE=ghcr.io/seathegood/data-platform-containers/hive-metastore:latest
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
    image: ghcr.io/seathegood/data-platform-containers/hive-metastore:latest
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
    image: ghcr.io/seathegood/data-platform-containers/airflow-runtime:latest
    depends_on:
      - postgres-airflow
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres-airflow/airflow
    command: webserver
    ports:
      - "8080:8080"

  airflow-scheduler:
    image: ghcr.io/seathegood/data-platform-containers/airflow-runtime:latest
    depends_on:
      - airflow-webserver
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres-airflow/airflow
    command: scheduler

  spark-job:
    image: ghcr.io/seathegood/data-platform-containers/spark-runtime:latest
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

### Concepts Demonstrated (Portfolio Lens)
- Supply-chain hygiene: digest-pinned bases, repeatable tagging (`latest`, semver, `sha-*`, optional `stable`), and Trivy scans in CI.
- Change detection: selective builds based on git diff plus opt-in `build all` via workflow dispatch.
- Registry practices: GHCR login with GitHub token, `:local` tags for developer ergonomics, and retagging helpers for namespace moves.
- Runtime ergonomics: sensible defaults for Airflow/Spark images and docker-compose snippets that mirror production without cloud dependencies.

## Additional Documentation
- [Container Development Methodologies](docs/wiki/container-development-methodologies.md)
- [Extending the Data Platform](docs/wiki/extending-the-project.md)
- [Operations Runbooks](docs/runbooks/README.md)
- [Maintenance Checklist](docs/maintenance.md)
- [AGENTS](AGENTS.md)

### Registry housekeeping (GHCR)
Use `scripts/ghcr_cleanup_tags.sh` to prune stray tags in GHCR (e.g., test or orphaned `sha-*` tags). It requires `gh` CLI authentication with `GITHUB_TOKEN` that has `packages:write` scope and accepts `--image` and `--keep` options for safety. The script is opt-in and does not run in CI by default.

Contributions are welcome! Open a pull request with proposed improvements and include doc updates or tests alongside code changes.
