#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[alb-integration] $*" >&2
}

if [[ "${AIRFLOW_INTEGRATION:-}" != "1" ]]; then
  log "skipping integration test; set AIRFLOW_INTEGRATION=1 to run."
  exit 0
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose_file="${COMPOSE_FILE:-${script_dir}/../../../docker-compose.airflow.local.yml}"

if ! command -v docker >/dev/null 2>&1; then
  log "docker is not available; start the local compose stack first."
  exit 1
fi

compose_err="$(mktemp)"
if ! running_webserver="$(docker compose -f "${compose_file}" ps --status running --quiet airflow-webserver 2>"${compose_err}")"; then
  log "docker compose ps failed:"
  cat "${compose_err}" >&2
  rm -f "${compose_err}"
  exit 1
fi
rm -f "${compose_err}"

if [[ -z "${running_webserver}" ]]; then
  log "airflow-webserver is not running; start the local compose stack first."
  exit 1
fi

headers="$(mktemp)"
body="$(mktemp)"
trap 'rm -f "${headers}" "${body}"' EXIT

oidc_identity="00000000-0000-0000-0000-000000000000"
oidc_data="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDAiLCJvaWQiOiIxMTExMTExMS0xMTExLTExMTEtMTExMS0xMTExMTExMTExMTEiLCJ0aWQiOiIyMjIyMjIyMi0yMjIyLTIyMjItMjIyMi0yMjIyMjIyMjIyMjIiLCJuYW1lIjoiQWRhIExvdmVsYWNlIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiYWRhLmxvdmVsYWNlQGNvbnRvc28uY29tIiwiZW1haWwiOiJhZGEubG92ZWxhY2VAY29udG9zby5jb20ifQ."

base_url="http://localhost:8080"
auth_prefix="${AUTH_MANAGER_PREFIX:-}"

if [[ -z "${auth_prefix}" ]]; then
  if auth_prefix="$(docker compose -f "${compose_file}" exec -T airflow-webserver \
    python - <<'PY'
from airflow.api_fastapi.app import AUTH_MANAGER_FASTAPI_APP_PREFIX
print(AUTH_MANAGER_FASTAPI_APP_PREFIX)
PY
  )"; then
    auth_prefix="$(echo "${auth_prefix}" | tail -n 1 | tr -d '\r')"
  else
    auth_prefix="/auth"
  fi
fi

if [[ -z "${auth_prefix}" ]]; then
  auth_prefix="/auth"
fi
last_status=""

try_request() {
  local method="$1"
  local url="$2"

  : > "${headers}"
  : > "${body}"

  if ! last_status="$(curl -sS -D "${headers}" -o "${body}" -w "%{http_code}" \
    -H "x-amzn-oidc-identity: ${oidc_identity}" \
    -H "x-amzn-oidc-data: ${oidc_data}" \
    -X "${method}" "${url}")"; then
    echo "request failed: ${method} ${url}"
    return 1
  fi

  if [[ "${method}" == "POST" && "${last_status}" == "201" ]]; then
    if grep -q "\"access_token\"" "${body}"; then
      return 0
    fi
  fi

  if [[ "${method}" == "GET" ]]; then
    if [[ "${last_status}" == "302" || "${last_status}" == "303" || "${last_status}" == "307" ]]; then
      if grep -qi "^set-cookie: .*jwt" "${headers}"; then
        return 0
      fi
    fi
  fi

  return 1
}

if ! ( \
  try_request "POST" "${base_url}${auth_prefix}/token" || \
  try_request "GET" "${base_url}${auth_prefix}/login?next=http%3A%2F%2Flocalhost%3A8081%2F" || \
  try_request "POST" "${base_url}/api/v2/auth/token" || \
  try_request "GET" "${base_url}/api/v2/auth/login?next=http%3A%2F%2Flocalhost%3A8081%2F" \
); then
  log "unable to complete auth flow."
  log "status: ${last_status}"
  cat "${headers}"
  cat "${body}"
  exit 1
fi

if ! row="$(docker compose -f "${compose_file}" exec -T postgres \
  psql -U airflow -d airflow -t -A -F ',' \
  -c "select username,email,first_name,last_name from ab_user where username='ada.lovelace@contoso.com';")"; then
  log "failed to query airflow database; is postgres running in compose?"
  exit 1
fi

if [[ -z "${row}" ]]; then
  log "expected user row for ada.lovelace@contoso.com."
  log "login status: ${last_status}"
  cat "${headers}"
  cat "${body}"
  if ! docker compose -f "${compose_file}" exec -T postgres \
    psql -U airflow -d airflow -t -A -F ',' \
    -c "select username,email,first_name,last_name from ab_user order by id desc limit 5;"; then
    log "failed to query recent users from airflow database."
  fi
  exit 1
fi

expected="ada.lovelace@contoso.com,ada.lovelace@contoso.com,Ada,Lovelace"
if [[ "${row}" != "${expected}" ]]; then
  echo "unexpected user row: ${row}"
  exit 1
fi

echo "{\"status\": \"ok\"}"
