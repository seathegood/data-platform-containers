# Great Expectations Core Container

Containerized [Great Expectations](https://greatexpectations.io/) CLI (GX Core) for building data quality workflows without managing local Python installs. The image packages Great Expectations inside a virtual environment and runs under a dedicated non-root user with a writable home at `/var/lib/gx`.

## Environment Variables
| Name | Default | Description |
| --- | --- | --- |
| `GX_HOME` | `/var/lib/gx` | Directory that stores GX data contexts, expectation suites, and validation artifacts. Mount persistent storage to retain project state. |

## Volume Mounts
- `/var/lib/gx` — persistent location for all GX artifacts. Mount a host directory or Docker volume here for long-lived projects.

## Build Arguments
| Name | Default | Description |
| --- | --- | --- |
| `GX_UID` | `886` | Numeric UID used for the `gx` user account. Set to match enterprise UID/GID mappings. |
| `GX_GID` | `886` | Numeric GID used for the `gx` group. Override if the default collides with existing IDs. |

## Quick Start
Initialize a new GX project and launch an interactive session:

```bash
docker run --rm -it \
  -v "$(pwd)/gx-project:/var/lib/gx" \
  ghcr.io/seathegood/data-platform-containers/gx-core:latest \
  init
```

Run validations or other CLI commands by appending arguments after the image reference:

```bash
docker run --rm -it \
  -v "$(pwd)/gx-project:/var/lib/gx" \
  ghcr.io/seathegood/data-platform-containers/gx-core:latest \
  checkpoint run my_checkpoint
```

Use `GX_HOME` to point to an alternate directory inside the container if you need multiple contexts:

```bash
docker run --rm -it \
  -e GX_HOME=/var/lib/gx/sandbox \
  -v "$(pwd)/gx-project:/var/lib/gx" \
  ghcr.io/seathegood/data-platform-containers/gx-core:latest \
  suite list
```

## CI-friendly usage
Mount your GX project and run validations non-interactively:

```bash
docker run --rm \
  -v "$(pwd)/gx-project:/var/lib/gx" \
  ghcr.io/seathegood/data-platform-containers/gx-core:latest \
  checkpoint run nightly_data_quality
```

The image runs as non-root `gx` (UID/GID 886) on top of Python 3.11 slim with GX installed in a venv.
