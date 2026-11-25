"""
Shared login-response finalization for the Reference_Stack (spec z_aud_3) — moving
`refresh_token` into an HttpOnly cookie and out of the JSON body when
`TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED` is on. Used by every endpoint that issues a fresh token
pair (`routers/auth.py`'s login/refresh, and Wave C's `routers/login_otp.py`) — factored out here
rather than duplicated per router (unlike the small, router-local `_resolved_application_id`
helper) because cookie settings (httponly/secure/samesite/path) are security-relevant and must
never drift between call sites.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse
from tenxyte.core.settings import Settings


def set_refresh_cookie(response: JSONResponse, settings: Settings, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        max_age=settings.jwt_refresh_token_lifetime,
        httponly=True,
        secure=True,
        samesite=settings.refresh_token_cookie_samesite,
        path=settings.refresh_token_cookie_path,
    )


def clear_refresh_cookie(response: JSONResponse, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=settings.refresh_token_cookie_path,
        samesite=settings.refresh_token_cookie_samesite,
    )


def finalize_login_response(data: dict, settings: Settings, status_code: int = 200) -> JSONResponse:
    """Builds the outgoing response, moving `refresh_token` into an HttpOnly cookie and out of
    the JSON body when `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED` is on — same conditional shape the
    Django_Adapter's `_set_refresh_cookie` produces."""
    refresh_token = data.get("refresh_token")
    if settings.refresh_token_cookie_enabled and refresh_token is not None:
        data = {k: v for k, v in data.items() if k != "refresh_token"}
        response = JSONResponse(status_code=status_code, content=data)
        set_refresh_cookie(response, settings, refresh_token)
        return response
    return JSONResponse(status_code=status_code, content=data)
