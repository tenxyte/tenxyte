"""
Organization-context FastAPI dependencies for the Reference_Stack (spec z_aud_3, Wave E chunk
1/4, task 11.1) — parity with `decorators.require_org_context`/`require_org_membership`/
`require_org_role`/`require_org_permission`/`require_org_owner`/`require_org_admin`, and with
`OrganizationContextMiddleware`'s `X-Org-Slug` resolution.

Implemented as a dependency chain (`Depends(...)`), not Starlette middleware — same idiom as
`require_jwt()`/`require_permission()` in `security.py`. This produces identical wire-visible
behavior to Django's real middleware + decorator stack (verified error shape by error shape below)
without needing an ASGI middleware that would have to open its own DB session outside FastAPI's
per-request `Depends(get_db_session)` lifecycle.

**Two distinct error-shape families, verified by reading the real Django code (not the
`@extend_schema`/`OpenApiExample` docs, which invent a `code` field for view/service-layer errors
that don't actually have one — see `org_service.py`'s module docstring)**:
1. Gate-level errors (this module) — a missing/invalid `X-Org-Slug`, a caller who isn't a member,
   or one who lacks a required role/permission — DO carry a `code` (and sometimes extra fields,
   e.g. `ORG_NOT_FOUND`'s `slug`, `ORG_MEMBERSHIP_REQUIRED`'s `organization`), straight out of
   `OrganizationContextMiddleware`'s literal `JsonResponse` and `decorators.py`'s literal
   `JsonResponse`/`_get_permission_denied_response` calls.
2. View/service-level business errors (`org_service.py`'s CRUD/member/invitation functions) —
   never carry a `code`, ever.

**`AUTHENTICATION_REQUIRED` is real but unreachable dead code, not replicated**: every one of
Django's `require_org_membership`/`require_org_role`/`require_org_permission`/`require_org_admin`
decorators has its own internal `if not request.user.is_authenticated: return 401
AUTHENTICATION_REQUIRED` branch — but every view in `organization_views.py` stacks `@require_jwt`
*above* these org decorators (so `require_jwt` always runs first and already guarantees an
authenticated user by the time control reaches them), making that branch permanently unreachable
in the real, wired app. This port's dependency chain has the exact same property — `require_jwt()`
runs first in every `Depends(...)` chain below — so the equivalent branch is omitted rather than
built for a state that can't occur either.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, Request
from tenxyte.adapters.fastapi import org_service
from tenxyte.adapters.fastapi.deps import get_db_session, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.models_sa import OrganizationDB, OrganizationMembershipDB
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.core.settings import Settings


@dataclass
class OrgAuthContext:
    """What an org-scoped route gets after its dependency chain succeeds."""

    auth: AuthContext
    organization: OrganizationDB
    membership: OrganizationMembershipDB | None = None


async def _resolve_organization(request: Request, session: AsyncSession, settings: Settings) -> OrganizationDB:
    """Mirrors `OrganizationContextMiddleware`'s `X-Org-Slug` resolution — including its own
    distinct `ORG_NOT_FOUND` 404 shape (with `code` and `slug`), separate from `require_org_context`'s
    `ORG_CONTEXT_REQUIRED` 400 (raised by the caller below when no header is present at all)."""
    org_slug = request.headers.get("X-Org-Slug")
    if not org_slug:
        raise TenxyteAPIError(
            "Organization context required. Please provide X-Org-Slug header.",
            code="ORG_CONTEXT_REQUIRED",
            status_code=400,
        )
    organization = await org_service.get_organization_by_slug_async(session, org_slug)
    if organization is None:
        raise TenxyteAPIError("Organization not found", code="ORG_NOT_FOUND", status_code=404, extra={"slug": org_slug})
    return organization


def _check_feature_enabled(settings: Settings) -> None:
    if not settings.organizations_enabled:
        raise TenxyteAPIError("Organizations feature is not enabled", code="ORG_FEATURE_DISABLED", status_code=400)


def require_org_context() -> Callable[..., Coroutine[Any, Any, OrgAuthContext]]:
    """Parity with `@require_jwt @require_org_context` — resolves `request.organization`, no
    membership check."""
    _require_jwt = require_jwt()

    async def _dependency(
        request: Request,
        auth: AuthContext = Depends(_require_jwt),  # noqa: B008
        session: AsyncSession = Depends(get_db_session),  # noqa: B008
        settings: Settings = Depends(get_settings),  # noqa: B008
    ) -> OrgAuthContext:
        _check_feature_enabled(settings)
        organization = await _resolve_organization(request, session, settings)
        return OrgAuthContext(auth=auth, organization=organization)

    return _dependency


def require_org_membership() -> Callable[..., Coroutine[Any, Any, OrgAuthContext]]:
    """Parity with `@require_jwt @require_org_context @require_org_membership`."""
    _require_org_context = require_org_context()

    async def _dependency(
        ctx: OrgAuthContext = Depends(_require_org_context),  # noqa: B008
        session: AsyncSession = Depends(get_db_session),  # noqa: B008
    ) -> OrgAuthContext:
        membership = await org_service.get_org_membership_async(session, ctx.auth.user.id, ctx.organization.id)
        if membership is None or membership.status != "active":
            raise TenxyteAPIError(
                "You are not a member of this organization",
                code="ORG_MEMBERSHIP_REQUIRED",
                status_code=403,
                extra={"organization": ctx.organization.slug},
            )
        ctx.membership = membership
        return ctx

    return _dependency


def require_org_role(
    role_code: str, *, check_inheritance: bool = True
) -> Callable[..., Coroutine[Any, Any, OrgAuthContext]]:
    """Parity with `decorators.require_org_role(role_code, check_inheritance)` — the denial
    message is the generic `"Permission denied."` (Django's own default when `VERBOSE_ERRORS` is
    off, which the Reference_Stack always treats it as — same posture as `require_permission` in
    `security.py`)."""
    _require_org_context = require_org_context()

    async def _dependency(
        ctx: OrgAuthContext = Depends(_require_org_context),  # noqa: B008
        session: AsyncSession = Depends(get_db_session),  # noqa: B008
        settings: Settings = Depends(get_settings),  # noqa: B008
    ) -> OrgAuthContext:
        has_role = await org_service.has_org_role_async(
            session,
            ctx.auth.user.id,
            ctx.organization,
            role_code,
            check_inheritance=check_inheritance,
            org_role_inheritance=settings.org_role_inheritance,
        )
        if not has_role:
            raise TenxyteAPIError("Permission denied.", code="ORG_ROLE_REQUIRED", status_code=403)
        ctx.membership = await org_service.get_org_membership_async(session, ctx.auth.user.id, ctx.organization.id)
        return ctx

    return _dependency


def require_org_permission(
    permission_code: str, *, check_inheritance: bool = True
) -> Callable[..., Coroutine[Any, Any, OrgAuthContext]]:
    """Parity with `decorators.require_org_permission(permission_code, check_inheritance)`."""
    _require_org_context = require_org_context()

    async def _dependency(
        ctx: OrgAuthContext = Depends(_require_org_context),  # noqa: B008
        session: AsyncSession = Depends(get_db_session),  # noqa: B008
        settings: Settings = Depends(get_settings),  # noqa: B008
    ) -> OrgAuthContext:
        has_permission = await org_service.has_org_permission_async(
            session,
            ctx.auth.user.id,
            ctx.organization,
            permission_code,
            check_inheritance=check_inheritance,
            org_role_inheritance=settings.org_role_inheritance,
        )
        if not has_permission:
            raise TenxyteAPIError("Permission denied.", code="ORG_PERMISSION_REQUIRED", status_code=403)
        ctx.membership = await org_service.get_org_membership_async(session, ctx.auth.user.id, ctx.organization.id)
        return ctx

    return _dependency


def require_org_owner() -> Callable[..., Coroutine[Any, Any, OrgAuthContext]]:
    """Parity with `decorators.require_org_owner` — `require_org_role("owner",
    check_inheritance=False)`."""
    return require_org_role("owner", check_inheritance=False)


def require_org_admin() -> Callable[..., Coroutine[Any, Any, OrgAuthContext]]:
    """Parity with `decorators.require_org_admin`: admin role WITH inheritance, OR owner role
    WITHOUT inheritance (owner >= admin) — a genuinely different inheritance rule per role, not a
    simplification; replicated exactly rather than normalized to a single `check_inheritance`
    value."""
    _require_org_context = require_org_context()

    async def _dependency(
        ctx: OrgAuthContext = Depends(_require_org_context),  # noqa: B008
        session: AsyncSession = Depends(get_db_session),  # noqa: B008
        settings: Settings = Depends(get_settings),  # noqa: B008
    ) -> OrgAuthContext:
        is_admin = await org_service.has_org_role_async(
            session,
            ctx.auth.user.id,
            ctx.organization,
            "admin",
            check_inheritance=True,
            org_role_inheritance=settings.org_role_inheritance,
        )
        is_owner = await org_service.has_org_role_async(
            session, ctx.auth.user.id, ctx.organization, "owner", check_inheritance=False
        )
        if not (is_admin or is_owner):
            raise TenxyteAPIError("Permission denied.", code="ORG_ROLE_REQUIRED", status_code=403)
        ctx.membership = await org_service.get_org_membership_async(session, ctx.auth.user.id, ctx.organization.id)
        return ctx

    return _dependency
