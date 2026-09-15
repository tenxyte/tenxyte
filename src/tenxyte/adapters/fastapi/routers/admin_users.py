"""
Parity_Group D — Admin Users (spec z_aud_3, Wave D chunk 3/5, task 10.1): admin/users/* — 8 of
Group D's 46 endpoints. Contract extracted from `views/user_views.py` (`UserListView`,
`UserDetailView`, `UserBanView`, `UserUnbanView`, `UserLockView`, `UserUnlockView`) and
`serializers/user_admin_serializers.py`. See `admin_user_service.py`'s module docstring for two
real Django fidelity findings (silently-dropped update fields, silently-dropped ban/lock
`reason`) replicated here rather than "fixed".
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import admin_user_service
from tenxyte.adapters.fastapi.deps import get_db_session
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.pagination import get_page_params, paginated_response
from tenxyte.adapters.fastapi.schemas import AdminUserUpdateRequest, BanUserRequest, LockUserRequest
from tenxyte.adapters.fastapi.security import require_permission

router = APIRouter()


def _parse_bool_param(request: Request, name: str) -> bool | None:
    raw = request.query_params.get(name)
    if raw is None:
        return None
    return raw.lower() in ("true", "1", "yes")


@router.get("/admin/users/")
async def list_users(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await admin_user_service.list_users_async(
        session,
        search=request.query_params.get("search", "").strip(),
        is_active=_parse_bool_param(request, "is_active"),
        is_locked=_parse_bool_param(request, "is_locked"),
        is_banned=_parse_bool_param(request, "is_banned"),
        is_deleted=_parse_bool_param(request, "is_deleted"),
        is_email_verified=_parse_bool_param(request, "is_email_verified"),
        is_2fa_enabled=_parse_bool_param(request, "is_2fa_enabled"),
        role=request.query_params.get("role"),
        date_from=request.query_params.get("date_from"),
        date_to=request.query_params.get("date_to"),
        ordering=request.query_params.get("ordering", "-created_at"),
        page=page,
        page_size=page_size,
    )
    items = [await admin_user_service.serialize_user_list_item_async(session, u) for u in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.get("/admin/users/{user_id}/")
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.view")),  # noqa: B008
):
    user = await admin_user_service.get_user_by_id_async(session, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    return await admin_user_service.serialize_user_detail_async(session, user)


@router.patch("/admin/users/{user_id}/")
async def update_user(
    user_id: str,
    body: AdminUserUpdateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.update")),  # noqa: B008
):
    user = await admin_user_service.get_user_by_id_async(session, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    fields = body.model_dump(exclude_unset=True)
    updated = await admin_user_service.update_user_async(session, user, fields)
    return await admin_user_service.serialize_user_detail_async(session, updated)


@router.delete("/admin/users/{user_id}/")
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.delete")),  # noqa: B008
):
    user = await admin_user_service.get_user_by_id_async(session, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    if user.is_deleted:
        raise TenxyteAPIError("User already deleted", code="ALREADY_DELETED", status_code=400)
    await admin_user_service.soft_delete_async(session, user)
    return {"message": "User soft-deleted successfully", "user_id": user_id}


@router.post("/admin/users/{user_id}/ban/")
async def ban_user(
    user_id: str,
    body: BanUserRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.ban")),  # noqa: B008
):
    user = await admin_user_service.get_user_by_id_async(session, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    if user.is_banned:
        raise TenxyteAPIError("User already banned", code="ALREADY_BANNED", status_code=400)
    await admin_user_service.ban_async(session, user)
    return {
        "message": "User banned successfully",
        "user": await admin_user_service.serialize_user_detail_async(session, user),
    }


@router.post("/admin/users/{user_id}/unban/")
async def unban_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.ban")),  # noqa: B008
):
    user = await admin_user_service.get_user_by_id_async(session, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    if not user.is_banned:
        raise TenxyteAPIError("User is not banned", code="NOT_BANNED", status_code=400)
    await admin_user_service.unban_async(session, user)
    return {
        "message": "User unbanned successfully",
        "user": await admin_user_service.serialize_user_detail_async(session, user),
    }


@router.post("/admin/users/{user_id}/lock/")
async def lock_user(
    user_id: str,
    body: LockUserRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.lock")),  # noqa: B008
):
    user = await admin_user_service.get_user_by_id_async(session, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    if user.is_locked:
        raise TenxyteAPIError("User already locked", code="ALREADY_LOCKED", status_code=400)
    duration = await admin_user_service.lock_async(session, user, duration_minutes=body.duration_minutes)
    return {
        "message": f"User locked for {duration} minutes",
        "user": await admin_user_service.serialize_user_detail_async(session, user),
    }


@router.post("/admin/users/{user_id}/unlock/")
async def unlock_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.lock")),  # noqa: B008
):
    user = await admin_user_service.get_user_by_id_async(session, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    if not user.is_locked:
        raise TenxyteAPIError("User is not locked", code="NOT_LOCKED", status_code=400)
    await admin_user_service.unlock_async(session, user)
    return {
        "message": "User unlocked successfully",
        "user": await admin_user_service.serialize_user_detail_async(session, user),
    }
