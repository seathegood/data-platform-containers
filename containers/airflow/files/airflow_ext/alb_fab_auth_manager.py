from __future__ import annotations

import logging
import base64
import json
from typing import cast
from urllib.parse import urljoin

from fastapi import Body, FastAPI, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from starlette import status
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.responses import RedirectResponse

from airflow.api_fastapi.app import AUTH_MANAGER_FASTAPI_APP_PREFIX, get_auth_manager
from airflow.api_fastapi.auth.managers.base_auth_manager import COOKIE_NAME_JWT_TOKEN
from airflow.api_fastapi.common.router import AirflowRouter
from airflow.configuration import conf
from airflow.providers.fab.auth_manager.api_fastapi.datamodels.login import (
    LoginBody,
    LoginResponse,
)
from airflow.providers.fab.auth_manager.api_fastapi.services.login import (
    FABAuthManagerLogin,
)
from airflow.providers.fab.auth_manager.fab_auth_manager import FabAuthManager
from airflow.providers.fab.www.app import create_app
from airflow_ext.alb_oidc_utils import decode_oidc_claims, map_user_info

log = logging.getLogger("airflow.auth.alb_fab_auth_manager")


def _decode_jwt_payload(token: str) -> dict[str, object] | None:
    try:
        payload_b64 = token.split(".", 2)[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def _rollback_auth_session(sm, *, reason: str, force: bool = False) -> None:
    session = getattr(sm, "session", None)
    if session is None:
        return
    try:
        if force or not getattr(session, "is_active", True):
            log.warning("Auth DB session rollback (%s).", reason)
            session.rollback()
    except Exception:
        log.exception("Failed to rollback auth DB session (%s).", reason)


def _ensure_user_id(sm, user, *, username: str, email: str | None) -> object | None:
    if user and getattr(user, "id", None):
        return user
    return sm.find_user(username=username) or (sm.find_user(email=email) if email else None)


class AlbFabAuthManager(FabAuthManager):
    def __init__(self, *args, **kwargs):
        log.warning("AlbFabAuthManager loaded")
        super().__init__(*args, **kwargs)
        self._flask_app = None

    def get_fastapi_app(self) -> FastAPI:
        login_router = AirflowRouter(tags=["AlbFabAuthManager"])

        @login_router.get("/login")
        def login(request: Request):
            next_url = request.query_params.get("next", "/")
            # Prevent open redirects: only allow relative paths.
            if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
                next_url = "/"
            user_info = self._get_user_info(request)
            if not user_info:
                log.warning("Missing remote user header on /login.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing remote user header.",
                )

            username, email, first_name, last_name = user_info
            user = self._get_or_create_user(
                username, email=email, first_name=first_name, last_name=last_name
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not authorized.",
                )

            token = self._generate_token(user)
            if not token or token == "None":
                log.error("Refusing to set JWT cookie with empty token for user=%r.", username)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed to mint token.",
                )
            response = RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
            forwarded_proto = request.headers.get("x-forwarded-proto", "")
            is_https = forwarded_proto.lower() == "https" or request.url.scheme == "https"
            secure = is_https or bool(conf.get("api", "ssl_cert", fallback=""))
            response.set_cookie(
                COOKIE_NAME_JWT_TOKEN,
                token,
                secure=secure,
                httponly=False,
                samesite="lax",
                path="/",
            )
            return response

        @login_router.post(
            "/token",
            response_model=LoginResponse,
            status_code=status.HTTP_201_CREATED,
        )
        def create_token(
            request: Request,
            body: LoginBody | None = Body(default=None),
        ):
            if body and body.username and body.password:
                return FABAuthManagerLogin.create_token(body=body)

            user_info = self._get_user_info(request)
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing remote user header.",
                )

            username, email, first_name, last_name = user_info
            user = self._get_or_create_user(
                username, email=email, first_name=first_name, last_name=last_name
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not authorized.",
                )
            token = self._generate_token(user)
            if not token or token == "None":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed to mint token.",
                )
            return LoginResponse(access_token=token)

        @login_router.post(
            "/token/cli",
            response_model=LoginResponse,
            status_code=status.HTTP_201_CREATED,
        )
        def create_token_cli(
            request: Request,
            body: LoginBody | None = Body(default=None),
        ):
            if body and body.username and body.password:
                return FABAuthManagerLogin.create_token(
                    body=body,
                    expiration_time_in_seconds=conf.getint("api_auth", "jwt_cli_expiration_time"),
                )

            user_info = self._get_user_info(request)
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing remote user header.",
                )

            username, email, first_name, last_name = user_info
            user = self._get_or_create_user(
                username, email=email, first_name=first_name, last_name=last_name
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not authorized.",
                )
            token = self._generate_token(
                user, expiration_time_in_seconds=conf.getint("api_auth", "jwt_cli_expiration_time")
            )
            if not token or token == "None":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed to mint token.",
                )
            return LoginResponse(access_token=token)

        flask_app = create_app(enable_plugins=False)
        self._flask_app = flask_app
        app = FastAPI(
            title="ALB FAB auth manager API",
            description=(
                "Auth manager extension for ALB OIDC header based authentication. "
                "Provides login and token routes that mint Airflow JWTs for the UI."
            ),
        )
        app.include_router(login_router)
        app.mount("/", WSGIMiddleware(flask_app))
        return app

    def get_url_login(self, **kwargs) -> str:
        return urljoin(self.apiserver_endpoint, f"{AUTH_MANAGER_FASTAPI_APP_PREFIX}/login")

    def _get_remote_user(self, request: Request) -> str | None:
        header_name = conf.get(
            "fab", "remote_user_header", fallback="x-amzn-oidc-identity"
        )
        value = request.headers.get(header_name)
        if value is None:
            value = request.headers.get(header_name.lower())
        return value

    def _get_user_info(self, request: Request) -> tuple[str, str | None, str, str] | None:
        identity = self._get_remote_user(request)
        claims_header = conf.get(
            "fab", "remote_user_claims_header", fallback="x-amzn-oidc-data"
        )
        claims_token = request.headers.get(claims_header)
        if claims_token is None:
            claims_token = request.headers.get(claims_header.lower())
        claims = decode_oidc_claims(claims_token)
        return map_user_info(identity, claims)

    def _get_or_create_user(
        self,
        username: str,
        *,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ):
        registration_enabled = conf.getboolean(
            "fab", "auth_user_registration", fallback=True
        )
        default_role = conf.get("fab", "auth_user_registration_role", fallback="User")
        auth_manager = cast(FabAuthManager, get_auth_manager())
        flask_app = self._flask_app or create_app(enable_plugins=False)
        if not self._flask_app:
            self._flask_app = flask_app
        with flask_app.app_context():
            sm = auth_manager.security_manager
            _rollback_auth_session(sm, reason="pre-find-user", force=True)
            user = sm.find_user(username=username)
            if not user and email:
                user = sm.find_user(email=email)
            if user and not getattr(user, "id", None):
                log.warning("User %s found without id; reloading from DB.", username)
                _rollback_auth_session(sm, reason="reload-missing-id")
                user = _ensure_user_id(sm, user, username=username, email=email)
            if user:
                return user

            if not registration_enabled:
                log.warning("User %s not found and auto-registration disabled.", username)
                return None

            role = sm.find_role(default_role)
            if not role:
                log.error("Default role %s not found; cannot auto-register user.", default_role)
                return None

            local_part = username.split("@", 1)[0]
            first_name = first_name or local_part or username
            last_name = last_name or "OIDC"
            log.info("Auto-registering user %s with role %s.", username, default_role)
            if email is not None:
                email_for_user = email
            elif "@" in username:
                email_for_user = username
            else:
                email_for_user = f"{username}@local.invalid"
            try:
                user = sm.add_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email_for_user,
                    role=role,
                )
            except IntegrityError:
                log.warning("User %s already exists; reloading after race.", username)
                _rollback_auth_session(sm, reason="integrity-error", force=True)
                return _ensure_user_id(sm, None, username=username, email=email)
            except Exception:
                log.exception("Unexpected error while adding user %s.", username)
                _rollback_auth_session(sm, reason="add-user-exception")
                return _ensure_user_id(sm, None, username=username, email=email)

            # Avoid using the possibly-detached instance returned by add_user; always re-query.
            user = _ensure_user_id(sm, None, username=username, email=email)
            if not user or not getattr(user, "id", None):
                log.error("User %s created without id; refusing to mint token.", username)
                return None
            return user

    def _generate_token(self, user, *, expiration_time_in_seconds: int | None = None) -> str:
        auth_manager = cast(FabAuthManager, get_auth_manager())
        token = (
            auth_manager.generate_jwt(user=user)
            if expiration_time_in_seconds is None
            else auth_manager.generate_jwt(
            user=user,
            expiration_time_in_seconds=expiration_time_in_seconds,
        )
        )
        user_id = getattr(user, "id", None)
        payload = _decode_jwt_payload(token) if token else None
        if payload:
            log.warning(
                "Minted JWT for user=%r id=%r claims=%s",
                getattr(user, "username", None),
                user_id,
                {k: payload.get(k) for k in ("sub", "user_id", "uid") if k in payload},
            )
        else:
            log.warning(
                "Minted JWT for user=%r id=%r (payload decode failed).",
                getattr(user, "username", None),
                user_id,
            )
        return token
