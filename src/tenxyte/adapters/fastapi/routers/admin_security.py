"""
Parity_Group D — Admin Security (spec z_aud_3, Wave D chunk 4/5, task 10.1): admin/audit-logs/*,
admin/login-attempts/*, admin/blacklisted-tokens/*, admin/refresh-tokens/* — 7 of Group D's 46
endpoints. Contract extracted from `views/security_views.py`. All 7 endpoints require
`security.view` — verified by reading the Django views directly (both POST actions,
blacklisted-tokens cleanup and refresh-token revoke, use the same permission as the GET listings,
not a separate write permission). See `admin_security_service.py`'s module docstring for the two
replicated ordering quirks and the audit-log/login-attempt population scope note.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import admin_security_service
from tenxyte.adapters.fastapi.deps import get_db_session
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.pagination import get_page_params, paginated_response
from tenxyte.adapters.fastapi.refresh_tokens import revoke_refresh_token_row
from tenxyte.adapters.fastapi.security import require_permission

router = APIRouter()


def _parse_bool_param(request: Request, name: str) -> bool | None:
    raw = request.query_params.get(name)
    if raw is None:
        return None
    return raw.lower() in ("true", "1", "yes")


@router.get("/admin/audit-logs/")
async def list_audit_logs(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("security.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await admin_security_service.list_audit_logs_async(
        session,
        user_id=request.query_params.get("user_id"),
        action=request.query_params.get("action"),
        ip_address=request.query_params.get("ip_address"),
        application_id=request.query_params.get("application_id"),
        date_from=request.query_params.get("date_from"),
        date_to=request.query_params.get("date_to"),
        ordering=request.query_params.get("ordering", "-created_at"),
        page=page,
        page_size=page_size,
    )
    items = [await admin_security_service.serialize_audit_log_async(session, r) for r in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.get("/admin/audit-logs/{log_id}/")
async def get_audit_log(
    log_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("security.view")),  # noqa: B008
):
    log = await admin_security_service.get_audit_log_by_id_async(session, log_id)
    if log is None:
        raise TenxyteAPIError("Audit log not found", code="NOT_FOUND", status_code=404)
    return await admin_security_service.serialize_audit_log_async(session, log)


@router.get("/admin/login-attempts/")
async def list_login_attempts(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("security.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await admin_security_service.list_login_attempts_async(
        session,
        identifier=request.query_params.get("identifier"),
        ip_address=request.query_params.get("ip_address"),
        success=_parse_bool_param(request, "success"),
        date_from=request.query_params.get("date_from"),
        date_to=request.query_params.get("date_to"),
        ordering=request.query_params.get("ordering", "-created_at"),
        page=page,
        page_size=page_size,
    )
    items = [admin_security_service.serialize_login_attempt(r) for r in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.get("/admin/blacklisted-tokens/")
async def list_blacklisted_tokens(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("security.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await admin_security_service.list_blacklisted_tokens_async(
        session,
        user_id=request.query_params.get("user_id"),
        reason=request.query_params.get("reason"),
        expired=_parse_bool_param(request, "expired"),
        ordering=request.query_params.get("ordering", "-blacklisted_at"),
        page=page,
        page_size=page_size,
    )
    items = [await admin_security_service.serialize_blacklisted_token_async(session, r) for r in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.post("/admin/blacklisted-tokens/cleanup/")
async def cleanup_blacklisted_tokens(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("security.view")),  # noqa: B008
):
    deleted_count = await admin_security_service.cleanup_expired_blacklisted_tokens_async(session)
    return {"message": f"{deleted_count} expired tokens cleaned up", "deleted_count": deleted_count}


@router.get("/admin/refresh-tokens/")
async def list_refresh_tokens(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("security.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await admin_security_service.list_refresh_tokens_admin_async(
        session,
        user_id=request.query_params.get("user_id"),
        application_id=request.query_params.get("application_id"),
        is_revoked=_parse_bool_param(request, "is_revoked"),
        expired=_parse_bool_param(request, "expired"),
        ordering=request.query_params.get("ordering", "-created_at"),
        page=page,
        page_size=page_size,
    )
    items = [await admin_security_service.serialize_refresh_token_admin_async(session, r) for r in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.post("/admin/refresh-tokens/{token_id}/revoke/")
async def revoke_refresh_token_admin(
    token_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("security.view")),  # noqa: B008
):
    token = await admin_security_service.get_refresh_token_by_id_async(session, token_id)
    if token is None:
        raise TenxyteAPIError("Refresh token not found", code="NOT_FOUND", status_code=404)
    if token.is_revoked:
        raise TenxyteAPIError("Token already revoked", code="ALREADY_REVOKED", status_code=400)

    await revoke_refresh_token_row(session, token)
    return {
        "message": "Token revoked successfully",
        "token": await admin_security_service.serialize_refresh_token_admin_async(session, token),
    }
