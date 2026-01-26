# Ongoing Maintenance

The automation in this repository keeps containers healthy, but humans still need to review change streams and apply security patches. Use the checklist below as part of your operational cadence.

## Weekly
- Run `make check` to lint metadata and confirm scripts work on your platform.
- Review upstream project release feeds; confirm `./scripts/package.py detect-version <package>` still reports the correct version.
- Inspect CI runs for flakiness or skipped tests.

## Monthly
- Update base image digests under `templates/docker/` to pick up OS patches.
- Update base image digests referenced in `containers/*/container.yaml` and open PRs with the refreshed pins.
- Re-run vulnerability scans with your preferred tooling and address critical findings immediately.
- Rotate any expiring credentials used for registry pushes.

## Base Image Migrations
- Spark now uses Eclipse Temurin (OpenJDK images are deprecated upstream). When updating Java base images, use Temurin tags and pin digests in `containers/spark/container.yaml`.

## Quarterly
- Audit container READMEs for outdated instructions.
- Run `make smoke-all` to rebuild and smoke-test every package.
- Validate backup/restore or disaster recovery procedures documented in `docs/runbooks/` if applicable.

## When Upstream Releases Ship
1. Run `./scripts/package.py detect-version <package>` to confirm the latest tag.
2. Update `containers/<package>/container.yaml` with the new version if auto-update failed.
3. Execute `make build PACKAGE=<package>` followed by `make test PACKAGE=<package>`.
4. Tag the repo and trigger the publish workflow if results look good.

## Spark Runtime Notes
- `make test PACKAGE=spark` runs a compose-based smoke test that exercises MinIO, S3A, AWS SDK classes, and Iceberg; ensure Docker and Docker Compose are available on the host.

## Release Tagging
- `latest` moves on every push; `stable` moves only on explicit release.
- Release tags include `x.y.z`, `x`, `x.y`, and `sha-<git>`.
- Record digests in release notes and treat mutable tags as pointers only.

## Incident Response
If a high-severity vulnerability is reported:
- Bump base images immediately.
- Review `containers/<package>/files/` overrides for vulnerable dependencies.
- Document the incident in `docs/runbooks/security.md` and link to patches or mitigations.

Keeping this template healthy ensures every downstream image follows secure, repeatable practices.
