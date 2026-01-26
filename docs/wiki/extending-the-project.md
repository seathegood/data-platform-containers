# Extending the Data Platform

Use this guide when you need to add a new service, swap dependencies, or tailor the platform to a specific deployment target.

## 1. Scope the Extension
1. Identify whether the change belongs in an existing container or warrants a new one.
2. Capture requirements up front: protocols, external systems, security constraints, scaling expectations.
3. Open an issue describing the desired outcome so reviewers can align on architecture before code changes land.

## 2. Create or Update a Container
- Clone `containers/_template` when introducing a new workload. The skeleton includes metadata, tests, and docs placeholders.
- Edit `container.yaml` to declare:
  - `name`, `description`, and expected runtime arguments.
  - `publish` targets (registry, tags, provenance settings).
  - `tests` to execute after image builds.
- Adapt the Dockerfile following the [Container Development Methodologies](container-development-methodologies.md) playbook.
- Document runtime usage in `containers/<name>/README.md` and link to it from the root README.

## 3. Wire Automation
- Register the container with the CLI: `make build PACKAGE=<name>` should succeed locally.
- Add smoke tests or integration suites under `containers/<name>/tests/` so CI validates future changes.
- Update `.github/workflows/` only when you need bespoke steps; otherwise rely on the shared job matrix.

## 4. Integrate with the Data Plane
- Decide how the new container participates in the platform: does it replace an existing component, or run alongside others?
- Update sample deployments (`README.md`, `docs/maintenance.md`, or `docs/runbooks/`) to explain how operators stitch the service into the stack.
- If the change alters contracts (ports, schemas, storage), document migration steps and default configuration toggles.
- Prefer open-standard services when introducing catalog or metadata layers. If a cloud-native service like AWS Glue is required, document the decision and provide explicit rollback steps (e.g., switching the Iceberg catalog back to Hive Metastore).
- When adding a new catalog/metadata service, include a minimal compose example and note how to roll back to the previous catalog.

## 5. Promote to Production
- Build and scan the image with `make build PACKAGE=<name>` and `make check`.
- Run end-to-end tests using the sample Docker Compose stack or your environment-specific manifests.
- Tag the release following semantic versioning or the upstream project's cadence. Push via `make publish PACKAGE=<name>`.
- Announce the change in release notes, highlighting breaking changes, new environment variables, and rollback instructions.

## 6. Maintain Over Time
- Track upstream releases using the `version` stanza in `container.yaml`. Automate detection when feeds exist.
- Update dependencies quarterly or after CVE advisories, whichever comes first.
- Schedule smoke tests (via CI or cron jobs) to ensure the composed platform still boots with the new component.

## Helpful References
- [Container Development Methodologies](container-development-methodologies.md)
- [Maintenance Checklist](../maintenance.md)
- [Runbooks Index](../runbooks/README.md)
- `scripts/package.py --help` for automation commands.

Keeping extensions aligned with these steps ensures the platform stays coherent, observable, and portable across environments.
