# Devpi Server Container

Packaged [devpi-server](https://devpi.net/) image that ships a configured runtime for private Python package caching and index management. The container bundles devpi-server and devpi-client within a dedicated virtual environment, defaulting to an empty server directory under `/var/lib/devpi`.

## Ports
- 3141/tcp — HTTP API and simple web UI.

## Environment Variables
| Name | Default | Description |
| --- | --- | --- |
| `DEVPI_SERVERDIR` | `/var/lib/devpi` | Filesystem location used for the devpi data directory. Mount persistent storage here for production. |
| `DEVPI_HOST` | `0.0.0.0` | Interface bound by devpi-server when no custom command is supplied. |
| `DEVPI_PORT` | `3141` | Port exposed by the service. Update alongside published port mappings. |
| `DEVPI_SERVER_FLAGS` | _(empty)_ | Extra arguments appended to the devpi-server command. Example: `--threads 10 --offline-mode`. |
| `DEVPI_HEALTHCHECK_HOST` | `127.0.0.1` | Host probed by the container healthcheck. Override when binding to a different interface. |

## Volumes
- `/var/lib/devpi` — persistent server directory. Store users, indexes, and cached packages.

## Build Arguments
| Name | Default | Description |
| --- | --- | --- |
| `DEVPI_UID` | `885` | Numeric UID assigned to the `devpi` runtime user inside the image. Override to align with cluster security policies. |
| `DEVPI_GID` | `885` | Numeric GID assigned to the `devpi` group. Customize when host environments reserve the default ID. |

## Usage
Initialize a devpi instance with basic defaults:

```bash
docker run -d --name devpi \
  -p 3141:3141 \
  -v devpi_data:/var/lib/devpi \
  ghcr.io/seathegood/data-platform-containers/devpi-server:latest
```

To customize the runtime, either pass environment variables or override the command:

```bash
docker run -d --name devpi \
  -p 3141:3141 \
  -v devpi_data:/var/lib/devpi \
  -e DEVPI_SERVER_FLAGS="--threads 10 --mirror-cache-expiry 60" \
  ghcr.io/seathegood/data-platform-containers/devpi-server:latest
```

Check health status via the built-in endpoint:

```bash
curl http://localhost:3141/+status
```

## Bootstrap and publish example
Initialize the server (first run only) and create a root user/index:

```bash
docker exec -it devpi devpi-init
docker exec -it devpi devpi use http://localhost:3141
docker exec -it devpi devpi user -c root --password changeme
docker exec -it devpi devpi login root --password changeme
docker exec -it devpi devpi index -c root/prod volatile=false
```

Publish a wheel to the `root/prod` index:

```bash
python -m pip install --upgrade devpi-client
devpi use http://localhost:3141/root/prod
devpi login root --password changeme
devpi upload  # run inside your package directory
```
