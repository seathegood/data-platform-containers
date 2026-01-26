# Package Skeleton

Copy this directory to create a new upstream container definition. Update the files that carry `TODO` comments and adjust commands to match the upstream project.

## Files
- `container.yaml` — machine-readable metadata that drives builds, tests, and publishing.
- `Dockerfile` — image build instructions. It receives build arguments declared in `container.yaml`.
- `files/` — overlay assets staged into the image.
- `tests/` — smoke tests executed via `make test PACKAGE=<name>`.

## Checklist for new containers
- Pin the base image by digest and record the rationale in `container.yaml#notes`.
- Set the publish target to `ghcr.io/seathegood/data-platform-containers/<slug>`.
- Add at least one smoke test (compose scenario if external deps are required) and register it under `container.yaml#tests`.
- Document required env vars, ports, and volumes in this README.
- If using shared snippets, prefer `templates/` assets to avoid duplication.

## Customization Tips
- Add additional build arguments by extending `container.yaml#build.args`.
- If you need multi-stage builds, edit the Dockerfile as required. The automation will pass the same build arguments to every stage.
- Document run instructions in this README so operators know how to launch and configure the container.

Keep examples minimal—real documentation lives alongside the final package definition.
