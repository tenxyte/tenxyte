"""
Application-level authentication for the FastAPI_Adapter (spec z_aud_3, Requirement 3.4) —
`X-Access-Key`/`X-Access-Secret`, parity with the Django_Adapter's `ApplicationAuthMiddleware`:
same exempt-path rules, same `APP_AUTH_REQUIRED`/`APP_AUTH_INVALID`/`APP_AUTH_ORIGIN_REQUIRED`/
`APP_AUTH_ORIGIN_DENIED` codes, same key-only (frontend, Origin-checked) vs key+secret
(server-to-server) modes, same `TENXYTE_APPLICATION_AUTH_ENABLED` toggle.
"""

from __future__ import annotations

import base64
import secrets

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tenxyte.adapters.fastapi.models_sa import ApplicationDB


def hash_secret(raw_secret: str) -> str:
    """Same scheme as `AbstractApplication._hash_secret`: bcrypt, base64-encoded for storage."""
    hashed = bcrypt.hashpw(raw_secret.encode("utf-8"), bcrypt.gensalt())
    return base64.b64encode(hashed).decode("utf-8")


def verify_secret(raw_secret: str, stored_secret: str) -> bool:
    if not stored_secret or not raw_secret:
        return False
    try:
        hashed = base64.b64decode(stored_secret.encode("utf-8"))
        return bcrypt.checkpw(raw_secret.encode("utf-8"), hashed)
    except Exception:  # noqa: BLE001 — any malformed stored value means "does not verify"
        return False


def is_origin_allowed(app: ApplicationDB, origin: str) -> bool:
    if not app.allowed_origins:
        return False
    return origin in app.allowed_origins


async def create_application(
    session: AsyncSession, name: str, allowed_origins: list[str] | None = None
) -> tuple[ApplicationDB, str]:
    """Create an Application and return (instance, raw_secret) — the raw secret is shown once."""
    raw_secret = secrets.token_hex(32)
    application = ApplicationDB(
        name=name,
        access_key=secrets.token_hex(32),
        access_secret=hash_secret(raw_secret),
        allowed_origins=allowed_origins or [],
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application, raw_secret


class ApplicationAuthMiddleware(BaseHTTPMiddleware):
    """Parity with `tenxyte.middleware.ApplicationAuthMiddleware` (Requirement 3.4)."""

    def _error(self, message: str, code: str, status_code: int = 401) -> JSONResponse:
        return JSONResponse({"error": message, "code": code}, status_code=status_code)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = request.app.state.tenxyte_settings

        if not settings.application_auth_enabled:
            request.state.application = None
            return await call_next(request)

        path = request.url.path
        if path in settings.exact_exempt_paths:
            request.state.application = None
            return await call_next(request)
        if any(path.startswith(prefix) for prefix in settings.exempt_paths):
            request.state.application = None
            return await call_next(request)

        access_key = request.headers.get("X-Access-Key")
        access_secret = request.headers.get("X-Access-Secret")

        if not access_key:
            return self._error("Missing application credentials", "APP_AUTH_REQUIRED")

        session_factory = request.app.state.tenxyte_session_factory
        async with session_factory() as session:
            stmt = select(ApplicationDB).where(ApplicationDB.access_key == access_key, ApplicationDB.is_active == True)
            application = (await session.execute(stmt)).scalar_one_or_none()

        if not application:
            return self._error("Invalid application credentials", "APP_AUTH_INVALID")

        if access_secret:
            if not verify_secret(access_secret, application.access_secret):
                return self._error("Invalid application credentials", "APP_AUTH_INVALID")
        else:
            origin = request.headers.get("Origin")
            if not origin:
                return self._error("Missing Origin header for key-only auth", "APP_AUTH_ORIGIN_REQUIRED")
            if not is_origin_allowed(application, origin):
                return self._error("Origin not allowed for this application", "APP_AUTH_ORIGIN_DENIED")

        request.state.application = application
        return await call_next(request)
