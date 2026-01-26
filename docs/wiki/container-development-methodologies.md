# Container Development Methodologies

This wiki captures the shared patterns we apply when crafting and maintaining data plane images. Treat it as the design contract for any new container added to this repository.

## Design Principles
- **Open standards first** – Favor Apache and CNCF projects (Spark, Iceberg, Hive, Airflow, Trino) and interoperable protocols such as Thrift and JDBC, pairing them with self-hosted tooling like devpi and GX for supply-chain resilience and observability.
- **Production by default** – Assume images will run in regulated environments. Harden base layers, limit attack surface, and document runtime requirements.
- **Idempotent builds** – Dockerfiles must be deterministic, pinning artifact versions and checksums where possible.
- **Runtime minimalism** – Ship only what operators need. Optional tools belong in profile-specific images or are mounted at runtime.

## Base Image Strategy
- Start from upstream-maintained base images whenever supported (e.g., `apache/airflow`). For scratch builds, lean on Debian/Ubuntu slim or distroless variants.
- Document why a particular base image was chosen inside `container.yaml#notes` for future reviews.
- Bake in locale and timezone data only when the application requires them. Otherwise, leave configuration to runtime.

## Dependency Management
- Store Python/Java dependencies in `requirements.txt` or metadata-managed lists. Pin exact versions to prevent sneaky upstream changes.
- Cache downloads during build stages with BuildKit mounts (`--mount=type=cache`) to speed up iterative development.
- Prefer fetching artifacts from official archives or registries. Validate them with SHA sums when available (see the Spark image).
- Pin base images by digest and refresh on a cadence (monthly or with CVE-driven updates); record the rationale for any over-pinning in `container.yaml#notes`.

## Security Hardening
- Drop to non-root users before shipping. If the upstream entrypoint runs as root, provide explicit justification in `container.yaml`.
- Remove package managers (`apt`, `apk`) and residual caches at the end of each stage.
- Provide health checks and readiness signals so orchestrators can detect misconfigurations quickly.
- Track CVEs with automated scans (`make check` runs Trivy by default) and remediate high-severity findings before tagging releases.

## Configuration Patterns
- Expose environment variables through `container.yaml#runtime.env` and document them in the container README.
- Support mounting external config via predictable directories under `/opt`.
- When multiple configuration layers exist, log the active path at startup (see `containers/spark/files/entrypoint.sh`).

## Testing Expectations
- Provide smoke tests in `containers/<name>/tests/` and register them under `container.yaml#tests`.
- For services with dependencies, add helper scripts or compose files under `tests/` so CI can stand up the full flow.
- If the smoke tests depend on a locally built image, ensure `make build` tags a `:local` variant and document the expected tag in the container README.
- Include YAML or BATS fixtures to verify entrypoint behavior (e.g., ensures required env vars produce actionable errors).
- Treat per-image README docs as part of the contract: include env vars, ports, volumes, example runs, and any integration prerequisites.

## Release Workflow
- Keep `container.yaml#version.current` in sync with upstream tags. When automation is possible, implement a detector in `scripts/package.py`.
- Document manual upgrade steps (schema migrations, config changes) in the container-specific README and reference them from `docs/maintenance.md`.
- Publish images using the `make publish PACKAGE=<name>` workflow. It signs the digest via cosign and attaches SBOM/provenance metadata.
- Record why dependencies are pinned above upstream minimums (e.g., CVE, bugfix) in `container.yaml#notes` to aid future reviewers.

## Review Checklist
Before merging a new container or major change:
- [ ] Dockerfile follows the principles above and passes `make check`.
- [ ] Smoke tests cover the critical happy path.
- [ ] Required secrets/configuration are clearly documented.
- [ ] Release notes explain upgrade impacts for operators.

Following this methodology keeps every image aligned with the broader data platform vision while staying simple to operate in production.
