#!/usr/bin/env bash
set -euo pipefail

ORG="${ORG:-bssprx}"
DEFAULT_PACKAGES=(
  airflow-runtime
  spark-runtime
  gx-core
  devpi-server
)
PACKAGES=("${@:-${DEFAULT_PACKAGES[@]}}")

# Dry-run by default. Set DRY_RUN=0 to delete.
DRY_RUN="${DRY_RUN:-1}"
# Optionally keep versions that include this tag.
KEEP_TAG="${KEEP_TAG:-}"

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is required (https://cli.github.com/)" >&2
  exit 1
fi

for pkg in "${PACKAGES[@]}"; do
  echo "==> ${ORG}/${pkg}"
  gh api --paginate "/orgs/${ORG}/packages/container/${pkg}/versions" --jq '.[] | @json' \
    | python3 -c 'import json, subprocess, sys
org, pkg, dry_run, keep_tag = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4]
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    item = json.loads(line)
    tags = item.get("metadata", {}).get("container", {}).get("tags", []) or []
    if keep_tag and keep_tag in tags:
        continue
    version_id = item["id"]
    cmd = [
        "gh",
        "api",
        "-X",
        "DELETE",
        f"/orgs/{org}/packages/container/{pkg}/versions/{version_id}",
    ]
    print("→", " ".join(cmd), f"# tags={tags}")
    if not dry_run:
        subprocess.run(cmd, check=True)
' "${ORG}" "${pkg}" "${DRY_RUN}" "${KEEP_TAG}"
done

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "Dry-run complete. Re-run with DRY_RUN=0 to delete."
fi
