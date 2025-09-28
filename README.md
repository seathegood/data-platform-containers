# Upstream Container Template

A reusable scaffolding for packaging third-party software into container images. The template organizes metadata, Dockerfiles, automation, and documentation so new upstream-based images can be created quickly and maintained with confidence.

## Key Ideas
- Capture upstream-specific choices (versioning, patches, entrypoint) alongside shared automation.
- Ship ready-to-run build/test/publish scripts that work for every package definition.
- Treat the repo as code: version metadata, enforce tests, and document assumptions.

## Repository Layout
- `containers/` – package definitions. Each package has metadata, Dockerfile, overlays, and tests.
- `templates/` – reusable Dockerfile snippets and scripting logic consumed by packages.
- `scripts/` – shared automation for building, testing, tagging, and publishing images.
- `docs/` – guidance for extending the template, release notes, and ops runbooks.
- `.github/workflows/` – CI wiring for linting, build, scan, and publish steps.
- `Makefile` – thin wrapper exposing common developer workflows.

## Prerequisites
- Docker 20.10+ (with BuildKit enabled)
- Python 3.10+ with `pyyaml` installed (`pip install pyyaml`)
- GNU Make

## Getting Started
1. Duplicate the `_template` skeleton under `containers/` to start a new package.
2. Fill in `container.yaml` with upstream metadata (name, source URL, version strategy, base image).
3. Customize the generated `Dockerfile` or add overlays under `files/` if the template is not enough.
4. Run `make build PACKAGE=name` to build locally. Use `make test` and `make publish` to validate and push.

The `docs/new-package.md` guide walks through these steps in more detail, including tips for mapping upstream releases to tags.

## Baseline Examples
A reference package is included to demonstrate the template:
- `hive-metastore` demonstrates building JVM services, layering configuration, and smoke-testing with Docker Compose.

Consult `containers/hive-metastore/README.md` for the full walkthrough, including how upstream versions are discovered and promoted.

## Automation Overview
The repository ships with batteries included:
- `scripts/package.py` centralizes build, test, version, and publish commands and understands metadata tokens such as `!version.current`.
- `make build|test|publish PACKAGE=<slug>` provides a thin wrapper around the Python helper.
- Tests can launch container-specific smoke suites defined under `containers/<pkg>/tests/`.
- CI (`.github/workflows/ci.yml`) exercises metadata checks and test suites across all packages on every pull request.

## Next Steps
- Create a new package definition by copying `_template`.
- Update the metadata and Dockerfile to match the upstream you want to package.
- Extend or override the shared automation only when necessary; prefer contributing improvements back to `templates/`.

Refer to `docs/maintenance.md` for ongoing upkeep tasks such as updating base images, rotating credentials, and auditing vulnerabilities.
