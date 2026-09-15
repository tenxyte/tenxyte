"""
App_Factory for the FastAPI_Adapter (spec z_aud_3, Requirement 3.1): `create_tenxyte_app` (a
runnable app) and `create_tenxyte_router` (a mountable router), both wired to the Reference_Stack
by default — no DI function raises `NotImplementedError` (Requirement 3.3).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from tenxyte.adapters.fastapi import db as db_module
from tenxyte.adapters.fastapi.application_auth import ApplicationAuthMiddleware
from tenxyte.adapters.fastapi.errors import register_exception_handlers
from tenxyte.adapters.fastapi.routers.admin_security import router as admin_security_router
from tenxyte.adapters.fastapi.routers.admin_users import router as admin_users_router
from tenxyte.adapters.fastapi.routers.airs import router as airs_router
from tenxyte.adapters.fastapi.routers.applications import router as applications_router
from tenxyte.adapters.fastapi.routers.auth import router as auth_router
from tenxyte.adapters.fastapi.routers.login_otp import router as login_otp_router
from tenxyte.adapters.fastapi.routers.magic_link import router as magic_link_router
from tenxyte.adapters.fastapi.routers.otp import router as otp_router
from tenxyte.adapters.fastapi.routers.password import router as password_router
from tenxyte.adapters.fastapi.routers.rbac import router as rbac_router
from tenxyte.adapters.fastapi.routers.twofa import router as twofa_router
from tenxyte.adapters.fastapi.settings import get_default_settings
from tenxyte.core.cache_service import InMemoryCacheService
from tenxyte.core.email_service import ConsoleEmailService
from tenxyte.core.jwt_service import InMemoryTokenBlacklistService, JWTService
from tenxyte.core.settings import Settings
from tenxyte.core.totp_service import TOTPService


def _build_router(settings: Settings) -> APIRouter:
    """
    The Parity_Group routers are mounted here as each wave (A→G) ships (spec z_aud_3,
    Requirement 4) — Wave A (`routers/auth.py`), Wave B (`routers/password.py`), Wave C's
    OTP-verification, 2FA-enrollment, magic-link, and passwordless-login-OTP routers
    (`routers/otp.py`, `routers/twofa.py`, `routers/magic_link.py`, `routers/login_otp.py`),
    Wave F's AIRS router (`routers/airs.py`), and Wave D's RBAC/applications/admin-users/
    admin-security routers (`routers/rbac.py`, `routers/applications.py`,
    `routers/admin_users.py`, `routers/admin_security.py`) so far.
    """
    router = APIRouter(prefix=settings.api_prefix)

    # Same path convention as the Django_Adapter's default EXEMPT_PATHS
    # ("{api_prefix}/health/") so the health check is exempt from application auth out of the
    # box, with no settings override needed.
    @router.get("/health/")
    async def health() -> dict:
        return {"status": "ok"}

    router.include_router(auth_router)
    router.include_router(password_router)
    router.include_router(otp_router)
    router.include_router(twofa_router)
    router.include_router(magic_link_router)
    router.include_router(login_otp_router)
    router.include_router(airs_router)
    router.include_router(rbac_router)
    router.include_router(applications_router)
    router.include_router(admin_users_router)
    router.include_router(admin_security_router)
    return router


def create_tenxyte_router(settings: Settings | None = None) -> APIRouter:
    """A mountable router — use this to add Tenxyte's endpoints to an existing FastAPI app."""
    return _build_router(settings or get_default_settings())


def create_tenxyte_app(
    settings: Settings | None = None,
    *,
    database_url: str | None = None,
    auto_create_schema: bool = True,
) -> FastAPI:
    """
    A runnable, self-contained FastAPI application (spec z_aud_3, Requirement 3.1).

    `auto_create_schema=True` (the default, aimed at development and tests) creates the
    Reference_Stack's tables directly from the ORM metadata on startup — production deployments
    should set this to `False` and apply the Alembic migrations under `migrations/` explicitly as
    part of their own deploy process instead (Requirement 3.2).
    """
    resolved_settings = settings or get_default_settings()
    resolved_database_url = database_url or db_module.DEFAULT_DATABASE_URL

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = db_module.create_engine(resolved_database_url)
        session_factory = db_module.create_session_factory(engine)

        if auto_create_schema:
            await db_module.create_all_tables(engine)

        app.state.tenxyte_settings = resolved_settings
        app.state.tenxyte_engine = engine
        app.state.tenxyte_session_factory = session_factory
        app.state.tenxyte_blacklist_service = InMemoryTokenBlacklistService()
        app.state.tenxyte_jwt_service = JWTService(
            settings=resolved_settings, blacklist_service=app.state.tenxyte_blacklist_service
        )
        app.state.tenxyte_cache_service = InMemoryCacheService()
        # A single shared instance — its replay_protection (in-memory by default) must persist
        # across requests to actually protect against TOTP code replay.
        app.state.tenxyte_totp_service = TOTPService(settings=resolved_settings)
        # No real email/SMS backend wired into the Reference_Stack yet — Core's own
        # ConsoleEmailService (prints instead of sending) backs magic-link delivery, the same
        # "no real backend wired in" posture otp_service.py already documents for OTP delivery.
        app.state.tenxyte_email_service = ConsoleEmailService()

        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Tenxyte", lifespan=lifespan)
    register_exception_handlers(app)
    app.add_middleware(ApplicationAuthMiddleware)
    app.include_router(create_tenxyte_router(resolved_settings))
    return app
