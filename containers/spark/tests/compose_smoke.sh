#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not available; cannot run compose smoke test" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose not available; cannot run compose smoke test" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if git_root="$(git -C "${repo_root}" rev-parse --show-toplevel 2>/dev/null)"; then
  repo_root="${git_root}"
fi
compose_file="${repo_root}/docker-compose.spark.local.yml"

if [[ ! -f "${compose_file}" ]]; then
  echo "compose file not found: ${compose_file}" >&2
  exit 1
fi

project_name="spark-smoke-$$"

cleanup() {
  docker compose -f "${compose_file}" --project-name "${project_name}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! docker image inspect spark-runtime:local >/dev/null 2>&1; then
  if [[ "${RUN_COMPOSE_SMOKE:-0}" != "1" || -n "${CI:-}" ]]; then
    echo "compose smoke skipped (spark-runtime:local not found)" >&2
    exit 0
  fi
  echo "spark-runtime:local image not found; run 'make build PACKAGE=spark' first" >&2
  exit 1
fi


docker compose -f "${compose_file}" --project-name "${project_name}" up --exit-code-from spark-smoke
