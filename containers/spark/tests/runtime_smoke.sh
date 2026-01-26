#!/usr/bin/env bash
set -euo pipefail

metadata_path="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/container.yaml"

image_ref="$(
  METADATA_PATH="$metadata_path" python3 - <<'PY'
import re
import os
from pathlib import Path

text = Path(os.environ["METADATA_PATH"]).read_text()
image = None
version = None
for line in text.splitlines():
    if image is None and re.match(r"^\s*image:\s*", line):
        image = re.sub(r"^\s*image:\s*", "", line).strip().strip('"').strip("'")
    if version is None and re.match(r"^\s*current:\s*", line):
        version = re.sub(r"^\s*current:\s*", "", line).strip().strip('"').strip("'")

if not image or not version:
    raise SystemExit("unable to resolve publish.image or version.current from container.yaml")

print(f"{image}:{version}")
PY
)"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not available; cannot run runtime smoke test" >&2
  exit 1
fi

set +e
version_output="$(docker run --rm "${image_ref}" spark-submit --version 2>&1)"
version_status=$?
set -e
if [[ $version_status -ne 0 ]]; then
  echo "${version_output}" >&2
  echo "spark-submit version check failed (exit ${version_status})" >&2
  exit 1
fi
echo "${version_output}"

if ! echo "${version_output}" | grep -q "Welcome to"; then
  echo "spark version banner not detected" >&2
  exit 1
fi

set +e
python_output="$(docker run --rm --entrypoint python3 "${image_ref}" --version 2>&1)"
python_status=$?
set -e
if [[ $python_status -ne 0 ]]; then
  echo "${python_output}" >&2
  echo "python version check failed (exit ${python_status})" >&2
  exit 1
fi
if ! echo "${python_output}" | grep -q "Python"; then
  echo "python version output not detected" >&2
  exit 1
fi

deps_env=()
while IFS= read -r line; do
  if [[ -n "$line" ]]; then
    deps_env+=("-e" "$line")
  fi
done < <(
  METADATA_PATH="$metadata_path" python3 - <<'PY'
import os
import re
from pathlib import Path

text = Path(os.environ["METADATA_PATH"]).read_text()
keys = [
    "PANDAS_VERSION",
    "PYARROW_VERSION",
    "FASTPARQUET_VERSION",
    "GRPCIO_VERSION",
    "GRPCIO_STATUS_VERSION",
    "GOOGLEAPIS_COMMON_PROTOS_VERSION",
    "ZSTANDARD_VERSION",
]
for key in keys:
    pattern = rf"^\s*{re.escape(key)}:\s*"
    value = None
    for line in text.splitlines():
        if re.match(pattern, line):
            value = re.sub(pattern, "", line).strip().strip('"').strip("'")
            break
    if value:
        print(f"{key}={value}")
PY
)

set +e
deps_output="$(
  docker run --rm "${deps_env[@]}" --entrypoint python3 "${image_ref}" - <<'PY'
import importlib.metadata
import os
import sys

required = {
    "pyspark": None,
    "py4j": None,
    "pandas": os.environ.get("PANDAS_VERSION"),
    "pyarrow": os.environ.get("PYARROW_VERSION"),
    "fastparquet": os.environ.get("FASTPARQUET_VERSION"),
    "grpcio": os.environ.get("GRPCIO_VERSION"),
    "grpcio-status": os.environ.get("GRPCIO_STATUS_VERSION"),
    "googleapis-common-protos": os.environ.get("GOOGLEAPIS_COMMON_PROTOS_VERSION"),
    "zstandard": os.environ.get("ZSTANDARD_VERSION"),
}

module_map = {
    "pyspark": "pyspark",
    "py4j": "py4j",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "fastparquet": "fastparquet",
    "grpcio": "grpc",
    "grpcio-status": "grpc_status",
    "googleapis-common-protos": "google.api",
    "zstandard": "zstandard",
}

missing = []
version_mismatch = []
for pkg, expected in required.items():
    try:
        __import__(module_map[pkg])
    except ModuleNotFoundError:
        missing.append(pkg)
        continue
    if expected:
        version = importlib.metadata.version(pkg)
        if version != expected:
            version_mismatch.append(f"{pkg} {version} != {expected}")

if missing:
    print("Missing modules:", ", ".join(missing))
if version_mismatch:
    print("Version mismatches:", ", ".join(version_mismatch))

if missing or version_mismatch:
    sys.exit(1)

print("Dependency import/version check passed")
PY
)"
deps_status=$?
set -e
if [[ $deps_status -ne 0 ]]; then
  echo "${deps_output}" >&2
  echo "dependency import/version check failed (exit ${deps_status})" >&2
  exit 1
fi
echo "${deps_output}"
