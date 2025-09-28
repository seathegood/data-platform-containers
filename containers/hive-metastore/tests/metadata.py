#!/usr/bin/env python3
import sys
from pathlib import Path
import yaml

metadata_path = Path(__file__).resolve().parent.parent / "container.yaml"
metadata = yaml.safe_load(metadata_path.read_text())

if metadata["version"]["current"] in (None, "", "0.0.0"):
    raise SystemExit("version.current must be set")

env_vars = {item["name"] for item in metadata.get("runtime", {}).get("env", [])}
required = {
    "METASTORE_DB_HOST",
    "METASTORE_DB_PORT",
    "METASTORE_DB",
    "METASTORE_DB_USER",
    "METASTORE_DB_PASSWORD",
    "METASTORE_PORT",
}
missing = required - env_vars
if missing:
    raise SystemExit(f"container.yaml missing required env vars: {sorted(missing)}")

print("metadata looks sane")
