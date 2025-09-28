#!/usr/bin/env python3
import json
from pathlib import Path

metadata_path = Path(__file__).resolve().parent.parent / "container.yaml"
metadata = metadata_path.read_text()

if 'version:' not in metadata:
    raise SystemExit('missing version block')

# Basic safeguard to avoid placeholder versions
if 'current: "0.0.0"' in metadata:
    raise SystemExit('version.current must be set to a real release')

print(json.dumps({"status": "ok"}))
