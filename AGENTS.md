# AGENTS Guide

## Purpose
- Provide safe, consistent instructions for automated agents working in this multi-image container repository.
- Prioritize reproducibility, minimal risk, and explicit approvals for publish actions.

## Repo Map
- `containers/<slug>/` contains each image definition.
- `containers/<slug>/container.yaml` is the source of truth for build args, tags, and runtime metadata.
- `containers/<slug>/Dockerfile` is the build recipe.
- `containers/<slug>/files/` holds entrypoints, health checks, and overlay files.
- `containers/<slug>/tests/` holds smoke tests.
- `scripts/package.py` is the build/test/publish CLI.
- `Makefile` wraps common tasks.
- `.github/workflows/` contains CI pipelines and release automation.

## Default Workflow
- Start read-only; confirm conventions from existing containers before editing.
- Limit changes to one image at a time unless explicitly requested.
- Update `container.yaml` and `Dockerfile` together for version or build-arg changes.
- Run `make test PACKAGE=<slug>` after edits when possible.
- Run Shellcheck on modified shell scripts when possible.
- Run Hadolint on modified Dockerfiles when possible.
- Never publish without explicit approval.

## Images (All Critical)
- `airflow`
- `spark`
- `gx-core`
- `devpi-server`
- `hive-metastore`

## Tagging and Release Policy
- Registry namespace: `ghcr.io/seathegood/data-platform-containers/<slug>`.
- `latest` moves on every push.
- `stable` moves only on explicit release.
- Publish tags include `x.y.z`, `x`, `x.y`, `latest`, `stable`, and `sha-<git>`.
- Digests are the immutable source of truth; release notes must record digests.
- Mutable tags must always point to a known digest.
- `stable` is added by the release workflow; local publishes include it only with `PACKAGE_INCLUDE_STABLE=1`.
- Image tags track upstream versions; repo releases provide a separate platform set version.
- Never tag or publish from forks/personal clones.

## Build and Test Commands
- List images: `./scripts/package.py`
- Build: `make build PACKAGE=<slug>`
- Test: `make test PACKAGE=<slug>`
- Show metadata: `make show PACKAGE=<slug>`
- Publish (maintainers only): `make publish PACKAGE=<slug>`
- Build logs (optional): `BUILD_LOG=1 make build PACKAGE=<slug>` writes to `logs/build-<slug>-<timestamp>.log` (override dir with `LOG_DIR=...`)
- Run Trivy via CI; locally, fail on CRITICAL/HIGH where possible.

## Per-Image Notes
### Airflow
- Base: `apache/airflow`.
- Use upstream constraints files; keep Python version aligned with Airflow constraints.
- Custom auth manager module lives in `containers/airflow/files/airflow_ext`; use it for ALB OIDC header flows.
- Pin base image digests; refresh during monthly maintenance.

### Spark
- Java 17 base; Spark 4.0 runtime.
- Iceberg/Hadoop/Python dependency versions are pinned in build args.
- AWS SDK v2 is modularized (`AWS_SDK_MODULES` in `containers/spark/container.yaml`); missing SDK classes should be addressed by adding modules or extending the bundle-extraction logic in the Dockerfile.
- `make build` tags `spark-runtime:local`; compose smoke tests rely on that tag and require Docker + Docker Compose.
- Pin base image digests; refresh during monthly maintenance.

### GX Core
- Python slim base; venv install for GX.
- Non-root user `gx` with fixed UID/GID.
- Pin base image digests; refresh during monthly maintenance.

### Devpi
- Python slim base; venv install for devpi-server/client.
- Non-root user `devpi` with fixed UID/GID.
- Healthcheck hits `/+status`.
- Pin base image digests; refresh during monthly maintenance.

### Hive-Metastore
- Java 21 base; Hive 4.1 runtime (Temurin Alpine). Pin the base image digest when updating.
- External PostgreSQL required; `METASTORE_DB_HOST/PORT/USER/PASSWORD/DB` are mandatory. `METASTORE_DB_URL` may override the generated JDBC URL.
- Entrypoint generates `hive-site.xml` if none is mounted, initializes schema when `VERSION` table is absent, and applies upgrade SQL when `SCHEMA_VERSION` differs (defaults to `version.current`).
- Healthcheck uses `/tmp/metastore-ready`, TCP probe on thrift port (default 9083), and schema version check via `psql`.
- Volumes: `/opt/hive/logs`, `/opt/hive/tmp`. Runs as non-root `hive`.
- Current tests are metadata-only; consider adding a Postgres-backed smoke test for schema init/upgrade.

## Security and Secrets
- Never bake secrets into images or files.
- Runtime secrets are handled by downstream projects; only parameterize via env vars.
- Prefer non-root runtime users.
- Remove package caches and build deps where feasible.
- Trivy must pass with CRITICAL/HIGH thresholds.
- Add integration smokes where missing (Hive Metastore, devpi-server, gx-core) to catch runtime/secret handling regressions.

## Dependency Rules
- Pin versions for pip and OS packages when possible.
- If unpinned, document the rationale in `container.yaml#notes`.
- Align pinned versions to upstream minimum requirements by default; only pin higher when needed and document the reason in `container.yaml#notes`.
- Default to the base image Python toolchain unless a newer pip/setuptools/wheel is explicitly required; document any overrides.
- Prefer upstream constraints files where available.

## Base Image Policy
- Base images must be pinned by digest.
- Digest updates are scheduled and PR-driven.

## Publish Rules
- Only maintainers publish images.
- Agents must request approval before push or tag changes.
- Use `.github/workflows/release.yml` to move `stable` and update release notes with digests.

## Documentation Requirements
- Update per-image README when runtime or config changes occur.
- Update `README.md` when tag or publish policy changes.

## Stop and Ask
- Any change to base images, tags, registries, or publish workflows.
- Any request to push or retag images.
- Any ambiguity about dependency pinning or release gating.
