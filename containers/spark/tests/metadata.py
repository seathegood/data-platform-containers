#!/usr/bin/env python3
import json
from pathlib import Path

metadata_path = Path(__file__).resolve().parent.parent / "container.yaml"
metadata = metadata_path.read_text()

if 'current: "' not in metadata:
    raise SystemExit('version.current must be set')

print(json.dumps({"status": "ok"}))
