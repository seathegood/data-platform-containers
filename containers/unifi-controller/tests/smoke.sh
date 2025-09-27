#!/usr/bin/env bash
set -euo pipefail

python3 <<'PY'
import pathlib
import sys
import yaml
metadata = yaml.safe_load(pathlib.Path('container.yaml').read_text())
version = metadata.get('version', {}).get('current')
if not version or version == '0.0.0':
    raise SystemExit('version.current must be set to a non-placeholder value')
expected_ports = {'https': 8443, 'inform': 8080, 'stun': 3478}
ports = {p['name']: p['container_port'] for p in metadata.get('runtime', {}).get('ports', [])}
missing = expected_ports.keys() - ports.keys()
if missing:
    raise SystemExit(f'missing expected ports in metadata: {sorted(missing)}')
for name, port in expected_ports.items():
    actual = ports[name]
    if actual != port:
        raise SystemExit(f'port mismatch for {name}: expected {port}, got {actual}')
PY

grep -q "ENTRYPOINT" Dockerfile
