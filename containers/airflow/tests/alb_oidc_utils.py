#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "files"))

from airflow_ext.alb_oidc_utils import decode_oidc_claims, map_user_info  # noqa: E402


def _b64url(payload: dict) -> str:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _make_token(payload: dict) -> str:
    header = {"alg": "none", "typ": "JWT"}
    return f"{_b64url(header)}.{_b64url(payload)}."


def _assert_equal(actual, expected, label):
    if actual != expected:
        raise SystemExit(f"{label} mismatch: {actual!r} != {expected!r}")


def test_decode_claims():
    payload = {"email": "alice@example.com", "name": "Alice Example"}
    token = _make_token(payload)
    decoded = decode_oidc_claims(token)
    _assert_equal(decoded, payload, "decode_oidc_claims")


def test_mapping_email_name():
    claims = {"email": "alice@example.com", "name": "Alice Example", "preferred_username": "alice"}
    info = map_user_info("sub-123", claims)
    _assert_equal(info, ("alice@example.com", "alice@example.com", "Alice", "Example"), "email/name")


def test_mapping_given_family():
    claims = {"preferred_username": "alice", "given_name": "Alice", "family_name": "Example"}
    info = map_user_info("sub-123", claims)
    _assert_equal(info, ("alice", None, "Alice", "Example"), "given/family")


def test_mapping_fallback():
    claims = {}
    info = map_user_info("sub-123", claims)
    _assert_equal(info, ("sub-123", None, "sub-123", "OIDC"), "fallback")


def test_mapping_missing_identity():
    info = map_user_info(None, {})
    _assert_equal(info, None, "missing identity")


def main():
    test_decode_claims()
    test_mapping_email_name()
    test_mapping_given_family()
    test_mapping_fallback()
    test_mapping_missing_identity()
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
