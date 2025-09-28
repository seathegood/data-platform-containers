# Creating a New Package Definition

This repository is designed to make upstream-based container images consistent and predictable. Follow the checklist below when onboarding a new package.

## 1. Copy the Skeleton
```
cp -R containers/_template containers/<package-name>
```
Rename files and references to match your package. Keep the directory name lowercase with dashes.

## 2. Describe the Upstream
Edit `containers/<package-name>/container.yaml`:
- `name`: human-readable identifier (e.g. `hive-metastore`).
- `upstream`: source project metadata (homepage, download URL, license).
- `version`: strategy for discovering new releases (manual, http-json, github, etc.).
- `runtime`: base image and runtime configuration.
- `tests`: list of smoke-test commands to run after builds.

If the upstream ships artifacts for multiple architectures, document how to fetch per-arch bundles.

## 3. Customize the Dockerfile
The `_template` Dockerfile uses snippets from `templates/docker/`. Swap snippets or add new ones when:
- The application is JVM-based and needs JAR installation.
- The upstream provides `.deb` or `.rpm` packages.
- Additional OS packages or configuration files are required.

Override files go under `containers/<package-name>/files/`. These are staged into the image during the build according to `container.yaml` instructions.

## 4. Wire Version Detection (Optional)
`./scripts/package.py detect-version <package>` prints the strategy and notes from `container.yaml`. Extend `scripts/package.py` with custom logic (HTTP calls, GitHub API, regex extraction) to auto-detect versions when possible. When automated detection is impossible, set `version.current` manually and update the `notes` field with the playbook for future maintainers.

## 5. Add Tests
Small smoke tests give confidence in CI:
- Bats, pytest, or shell scripts placed under `containers/<package-name>/tests/`.
- Compose scenarios (`docker-compose.yml`) for services needing dependencies (e.g. databases).

Declare each test in `container.yaml#tests`. The `make test PACKAGE=name` target executes them after building.

## 6. Document Run Instructions
Populate `containers/<package-name>/README.md` with:
- Summary of what the container runs.
- Environment variables, ports, volumes.
- Required secrets or TLS assets.
- Example `docker run` and `docker compose` usage.

## 7. CI/CD Wiring
The `CI` workflow enumerates every package under `containers/`, builds them with Docker Buildx, and reuses metadata defined in `container.yaml` to tag images. To plug in a new package:
- Set `publish.image` and `publish.tags` so the workflow knows which registry references to push and sign.
- Provide smoke tests via `tests/` entries; add an optional `tests/e2e.sh` script for dependency bootstrapping (run automatically when present).
- Keep Dockerfiles and shell scripts lint-clean—`make check`, `shellcheck`, `hadolint`, and `trivy` all run in CI before builds.
- Create or update `versions.json` (and optionally set `version.component`) so the scheduled upstream check can flag new releases and open issues automatically.
- Pushing to `main` publishes and cosign-signs images using the registry secrets plus GitHub OIDC; pull requests only build and verify artifacts.

By following this playbook every container package stays well-documented, reproducible, and ready for automated maintenance.
