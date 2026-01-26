from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional

log = logging.getLogger("airflow.auth.alb_fab_auth_manager")


def decode_oidc_claims(token: str | None) -> dict[str, Any]:
    if not token:
        return {}
    try:
        parts = token.split(".", 2)
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64 + padding)
        obj = json.loads(payload.decode("utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception as exc:
        log.warning("Failed to parse x-amzn-oidc-data claims (%s).", exc.__class__.__name__)
        return {}


def _as_str(v: Any) -> Optional[str]:
    return v if isinstance(v, str) and v else None


def map_user_info(identity: str | None, claims: dict[str, Any]) -> tuple[str, str | None, str, str] | None:
    # Prefer email-like identifiers from Azure/Entra
    email = _as_str(claims.get("email"))
    preferred_username = _as_str(claims.get("preferred_username"))
    upn = _as_str(claims.get("upn"))
    subject = _as_str(identity)

    username = email or preferred_username or upn or subject
    if not username:
        return None

    # Only treat something as email if it looks like one
    email_out = email or preferred_username or upn
    if email_out and "@" not in email_out:
        email_out = None

    name = _as_str(claims.get("name"))
    given_name = _as_str(claims.get("given_name"))
    family_name = _as_str(claims.get("family_name"))

    if name:
        parts = name.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    elif given_name or family_name:
        first_name = given_name or ""
        last_name = family_name or ""
    else:
        local_part = username.split("@", 1)[0]
        first_name = local_part or username
        last_name = "OIDC"

    return username, email_out, first_name, last_name