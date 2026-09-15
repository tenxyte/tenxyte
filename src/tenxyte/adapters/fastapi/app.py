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
from tenxyte.adapters.fastapi.routers.dashboard import router as dashboard_router
from tenxyte.adapters.fastapi.routers.gdpr import router as gdpr_router
from tenxyte.adapters.fastapi.routers.gdpr_admin import router as gdpr_admin_router
from tenxyte.adapters.fastapi.routers.login_otp import router as login_otp_router
from tenxyte.adapters.fastapi.routers.magic_link import router as magic_link_router
from tenxyte.adapters.fastapi.routers.orgs import router as orgs_router
from tenxyte.adapters.fastapi.routers.otp import router as otp_router
from tenxyte.adapters.fastapi.routers.password import router as password_router
from tenxyte.adapters.fastapi.routers.rbac import router as rbac_router
from tenxyte.adapters.fastapi.routers.social import router as social_router
from tenxyte.adapters.fastapi.routers.twofa import router as twofa_router
from tenxyte.adapters.fastapi.routers.webauthn import router as webauthn_router
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
    Wave F's AIRS router (`routers/airs.py`), Wave D's full set of routers
    (`routers/rbac.py`, `routers/applications.py`, `routers/admin_users.py`,
    `routers/admin_security.py`, `routers/dashboard.py` — Wave D is complete), and Wave E's
    organizations router (`routers/orgs.py`, conditionally registered — see below).
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
    router.include_router(dashboard_router)
    # Wave G (z_aud_3 task 12.1) — unconditionally registered, unlike Organizations: Django's own
    # urls.py registers webauthn/* unconditionally too, gating WEBAUTHN_ENABLED at the
    # service-call level instead (see webauthn_service.py's module docstring).
    router.include_router(webauthn_router)
    # Wave G chunk 2/4 (z_aud_3 task 12.1) — social/* is also unconditionally registered in
    # Django's urls.py; per-provider enablement is gated at the service-call level via
    # `settings.social_providers` (see social_auth_service.py's module docstring).
    router.include_router(social_router)
    # Wave G chunk 3/4 (z_aud_3 task 12.1) — GDPR user endpoints, unconditionally registered too
    # (Django's urls.py never gates these behind a feature flag).
    router.include_router(gdpr_router)
    # Wave G chunk 4/4 (z_aud_3 task 12.1) — GDPR admin endpoints, closing out Group G.
    router.include_router(gdpr_admin_router)

    # Wave E (z_aud_3 task 11.1) — mirrors Django's own conditionally-registered `urlpatterns`
    # block exactly (`if org_settings.ORGANIZATIONS_ENABLED: urlpatterns += [...]`, evaluated once
    # at urls.py load time): a disabled deployment never registers these paths at all, so it 404s
    # on `/organizations/*`/`/org-roles/` rather than returning a JSON `ORG_FEATURE_DISABLED` body
    # — see `org_context.py`'s module docstring.
    if settings.organizations_enabled:
        router.include_router(orgs_router)

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

    # `docs_url`/`openapi_url`/`redoc_url` explicitly placed under the API prefix rather than
    # left at FastAPI's own bare-root default (`/docs`, `/openapi.json`, `/redoc`) — Core's
    # shared `exempt_paths` default (`conf/base.py`'s `EXEMPT_PATHS`, also read by
    # `ApplicationAuthMiddleware` here) has always exempted `{api_prefix}/docs/` from
    # application-level auth, a Django-project convention (a real deployment mounts
    # drf-spectacular's Swagger view there itself). Left at FastAPI's own unprefixed default,
    # that exemption pattern matches nothing real, so `/docs` stayed silently gated behind
    # `X-Access-Key`/`X-Access-Secret` even for a fresh, zero-config app — found while verifying
    # the FastAPI quickstart doc's own "Swagger reachable at /docs" claim (spec z_aud_3,
    # Requirement 7.1, MT-1) end-to-end against a real running server, not by reading the code.
    docs_prefix = f"{resolved_settings.api_prefix}/docs/"
    app = FastAPI(
        title="Tenxyte",
        lifespan=lifespan,
        # `exempt_paths`'s default entry is a *prefix* match on `{api_prefix}/docs/` (trailing
        # slash) — every one of `docs_url`/`openapi_url`/`redoc_url` is placed AT or UNDER that
        # exact prefix (not left as FastAPI's own root-level `/docs`/`/openapi.json`/`/redoc`
        # defaults) so the one exemption entry actually covers every asset Swagger UI's page
        # needs to fetch, not just the HTML shell.
        docs_url=docs_prefix,
        openapi_url=f"{docs_prefix}openapi.json",
        redoc_url=f"{docs_prefix}redoc",
    )
    register_exception_handlers(app)
    app.add_middleware(ApplicationAuthMiddleware)
    app.include_router(create_tenxyte_router(resolved_settings))
    return app
