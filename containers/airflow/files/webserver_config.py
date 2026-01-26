"""Airflow FAB webserver configuration.

This file is loaded via `AIRFLOW__FAB__CONFIG_FILE`.

What this file CAN do:
- Configure Flask AppBuilder (FAB) settings used by the FAB auth manager (e.g., AUTH_REMOTE_USER).
- Provide startup diagnostics proving the file was loaded and showing key env values.

Important for Airflow 3 `api-server` (uvicorn / FastAPI):
- The new UI fetches data via FastAPI endpoints (for example `/ui/config`). Those endpoints require a JWT token.
- With `AUTH_REMOTE_USER`, you usually do not have a username/password to call `/auth/token`.
- Therefore, to make the UI/API work behind ALB OIDC, you typically must implement a *custom* auth manager
  that overrides `FabAuthManager.create_token()` to derive the user from the ALB header (for example
  `x-amzn-oidc-identity`) and then return/create the Airflow user.

This file alone cannot implement `create_token()`; it only configures FAB.
"""

import logging
import os

from flask_appbuilder.security.manager import AUTH_REMOTE_USER

log = logging.getLogger("airflow.fab.webserver_config")


def _env_bool(name: str, default: str) -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}

#
# NOTE: These access_log* settings apply to the legacy gunicorn-based webserver.
# Airflow 3 `api-server` uses uvicorn access logging instead.
#
access_logfile = "-"
access_logformat = (
    "%(h)s %(r)s %(s)s "
    "oidc=%({x-amzn-oidc-identity}i)s "
    "host=%({host}i)s "
    "proto=%({x-forwarded-proto}i)s"
)

# Startup diagnostics: prove this config file was loaded and what env vars it sees.
# These logs should appear in container stdout/stderr early in startup.
log.warning(
    "Loaded webserver_config.py (FAB config_file). access_logfile=%s",
    access_logfile,
)

auth_manager = os.getenv("AIRFLOW__CORE__AUTH_MANAGER", "").strip()
fab_enabled = (
    auth_manager
    == "airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager"
)
remote_user_header = os.getenv("AIRFLOW__FAB__REMOTE_USER_HEADER", "").strip()

log.warning(
    "FAB config detection: auth_manager=%r fab_enabled=%s remote_user_header=%r",
    auth_manager,
    fab_enabled,
    remote_user_header,
)

if fab_enabled and remote_user_header:
    auth_type_env = os.getenv("AIRFLOW__FAB__AUTH_TYPE", "AUTH_REMOTE_USER").strip().upper()
    log.warning("FAB REMOTE_USER enabling: AIRFLOW__FAB__AUTH_TYPE=%r", auth_type_env)
    auth_type_map = {
        "AUTH_REMOTE_USER": AUTH_REMOTE_USER,
    }
    AUTH_TYPE = auth_type_map.get(auth_type_env, AUTH_REMOTE_USER)
    REMOTE_USER_HEADER = remote_user_header
    AUTH_USER_REGISTRATION = _env_bool(
        "AIRFLOW__FAB__AUTH_USER_REGISTRATION", "true"
    )
    AUTH_USER_REGISTRATION_ROLE = os.getenv(
        "AIRFLOW__FAB__AUTH_USER_REGISTRATION_ROLE",
        "Viewer"
    ).strip()
    log.warning(
        "FAB REMOTE_USER configured: AUTH_TYPE=%r REMOTE_USER_HEADER=%r AUTH_USER_REGISTRATION=%s AUTH_USER_REGISTRATION_ROLE=%r",
        AUTH_TYPE,
        REMOTE_USER_HEADER,
        AUTH_USER_REGISTRATION,
        AUTH_USER_REGISTRATION_ROLE,
    )
else:
    log.warning(
        "FAB REMOTE_USER NOT enabled (expected FabAuthManager + AIRFLOW__FAB__REMOTE_USER_HEADER). "
        "fab_enabled=%s remote_user_header=%r",
        fab_enabled,
        remote_user_header,
    )
