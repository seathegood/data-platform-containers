#!/usr/bin/env python3
"""Apply upstream version updates to container metadata."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTAINERS_DIR = ROOT / "containers"


def fetch_digest(image: str) -> str:
    cmd = ["docker", "buildx", "imagetools", "inspect", image]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    for line in completed.stdout.splitlines():
        if line.strip().startswith("Digest:"):
            return line.split("Digest:", 1)[1].strip()
    raise SystemExit(f"Unable to find digest for {image}")


def replace_key(lines: list[str], key: str, value: str) -> bool:
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f"{key}:"):
            indent = line[: len(line) - len(stripped)]
            lines[idx] = f'{indent}{key}: "{value}"\n'
            return True
    return False


def update_container(entry: dict) -> bool:
    slug = entry.get("package")
    latest = entry.get("latest")
    if not slug or not latest:
        return False

    metadata_path = CONTAINERS_DIR / slug / "container.yaml"
    if not metadata_path.exists():
        raise SystemExit(f"Missing container metadata: {metadata_path}")

    data = yaml.safe_load(metadata_path.read_text())
    lines = metadata_path.read_text().splitlines(keepends=True)

    changed = replace_key(lines, "current", str(latest))
    if slug == "airflow":
        py_version = (
            data.get("build", {}).get("args", {}).get("PYTHON_VERSION")
            if isinstance(data, dict)
            else None
        )
        if not py_version:
            runtime_base = str(data.get("runtime", {}).get("base_image", ""))
            match = re.search(r"python(\d+\.\d+)", runtime_base)
            py_version = match.group(1) if match else None
        if not py_version:
            raise SystemExit("Unable to determine Airflow PYTHON_VERSION for base image update")

        tag = f"apache/airflow:{latest}-python{py_version}"
        digest = fetch_digest(tag)
        base_image = f"{tag}@{digest}"
        if not replace_key(lines, "base_image", base_image):
            raise SystemExit("Unable to update Airflow runtime.base_image")
        changed = True

    if slug == "spark":
        build_args = data.get("build", {}).get("args", {})
        current_flavor = str(build_args.get("ICEBERG_RUNTIME_FLAVOR", ""))
        current_version = str(build_args.get("ICEBERG_VERSION", ""))
        new_flavor = entry.get("iceberg_runtime_flavor") or current_flavor
        new_version = entry.get("iceberg_version") or current_version

        if new_flavor and new_flavor != current_flavor:
            if replace_key(lines, "ICEBERG_RUNTIME_FLAVOR", str(new_flavor)):
                changed = True
        if new_version and new_version != current_version:
            if replace_key(lines, "ICEBERG_VERSION", str(new_version)):
                changed = True

    if changed:
        metadata_path.write_text("".join(lines))
    return changed


def main() -> None:
    updates_json = os.environ.get("UPDATES_JSON")
    if not updates_json:
        print("No updates provided; nothing to do.")
        return

    updates = json.loads(updates_json)
    if not updates:
        print("No updates detected.")
        return

    touched = []
    for entry in updates:
        if update_container(entry):
            touched.append(entry.get("package"))

    if touched:
        print("Updated:", ", ".join(sorted(set(touched))))
    else:
        print("No container metadata changes applied.")


if __name__ == "__main__":
    main()
