# UniFi Network Application Container

Opinionated containerization of Ubiquiti's UniFi Network Application (formerly "controller"). Built on the upstream download artifacts and tailored for Kubernetes and Compose deployments.

## Ports
- 8443/tcp — HTTPS controller UI
- 8080/tcp — Inform traffic from UniFi devices
- 3478/udp — STUN for device discovery

## Volumes
- `/var/lib/unifi` — persistent application data and backups

## Environment Variables
- `TZ` — optional timezone (default: `UTC`)
- `JVM_HEAP_SIZE` — maximum heap for the JVM (default: `1024M`)

## Usage
```
docker run -d \
  --name unifi \
  -p 8443:8443 -p 8080:8080 -p 3478:3478/udp \
  -v unifi-data:/var/lib/unifi \
  ghcr.io/your-org/unifi-controller:7.5.187
```

Refer to `container.yaml` for automation metadata and build arguments.
