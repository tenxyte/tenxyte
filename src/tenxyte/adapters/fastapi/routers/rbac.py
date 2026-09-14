"""
Parity_Group D — RBAC (spec z_aud_3, task 10.1): permissions/*, roles/*, roles/{id}/permissions/*,
users/{id}/roles/*, users/{id}/permissions/* — 19 of Group D's 46 endpoints. Contract extracted
from `views/rbac_views.py`, `serializers/rbac_serializers.py`, `filters.py`'s
`apply_permission_filters`/`apply_role_filters`, and `models/auth.py`'s `AbstractPermission`/
`AbstractRole`/`User` RBAC methods (`has_permission`, `_get_effective_permission_codes`,
`assign_role`, `remove_role`, `get_all_roles`).

Every endpoint here is gated by `security.require_permission(code)`, the FastAPI equivalent of
`@require_permission(code)` — see that function's docstring for the exact denial contract
(generic `"Permission denied."`, matching Django's non-verbose default).

**Not replicated: the MongoDB-compatible fallback** in `RolePermissionsView`/
`UserDirectPermissionsView`'s `_safe_add_permissions`/`_safe_remove_permissions` — those exist
purely to work around a MongoDB-backend deletion-collector quirk in Django's ORM; the
Reference_Stack's SQLAlchemy backend has no such quirk, so `rbac_service.py`'s plain
`insert()`/`delete()` statements against the association tables need no fallback path.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Query, Request
from tenxyte.adapters.fastapi import rbac_service
from tenxyte.adapters.fastapi.deps import get_db_session
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.adapters.fastapi.pagination import get_page_params, paginated_response
from tenxyte.adapters.fastapi.schemas import (
    AssignRoleRequest,
    ManageRolePermissionsRequest,
    PermissionCreateRequest,
    PermissionUpdateRequest,
    RoleCreateRequest,
    RoleUpdateRequest,
)
from tenxyte.adapters.fastapi.security import require_permission

router = APIRouter()


# ============================================================
# Permissions
# ============================================================


@router.get("/permissions/")
async def list_permissions(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("permissions.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await rbac_service.list_permissions_async(
        session,
        search=request.query_params.get("search", "").strip(),
        parent=request.query_params.get("parent"),
        ordering=request.query_params.get("ordering", "code"),
        page=page,
        page_size=page_size,
    )
    items = [await rbac_service.serialize_permission_async(session, p) for p in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.post("/permissions/", status_code=201)
async def create_permission(
    body: PermissionCreateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("permissions.create")),  # noqa: B008
):
    row, error = await rbac_service.create_permission_async(
        session, code=body.code, name=body.name, description=body.description, parent_code=body.parent_code
    )
    if error == "PARENT_NOT_FOUND":
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"parent_code": [f'Permission "{body.parent_code}" not found']},
        )
    return await rbac_service.serialize_permission_async(session, row)


@router.get("/permissions/{permission_id}/")
async def get_permission(
    permission_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("permissions.view")),  # noqa: B008
):
    permission = await rbac_service.get_permission_by_id_async(session, permission_id)
    if permission is None:
        raise TenxyteAPIError("Permission not found", code="NOT_FOUND", status_code=404)
    return await rbac_service.serialize_permission_async(session, permission)


@router.put("/permissions/{permission_id}/")
async def update_permission(
    permission_id: str,
    body: PermissionUpdateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("permissions.update")),  # noqa: B008
):
    permission = await rbac_service.get_permission_by_id_async(session, permission_id)
    if permission is None:
        raise TenxyteAPIError("Permission not found", code="NOT_FOUND", status_code=404)

    updated, error = await rbac_service.update_permission_async(
        session, permission, name=body.name, description=body.description, parent_code=body.parent_code
    )
    if error == "PARENT_NOT_FOUND":
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"parent_code": [f'Permission "{body.parent_code}" not found']},
        )
    return await rbac_service.serialize_permission_async(session, updated)


@router.delete("/permissions/{permission_id}/")
async def delete_permission(
    permission_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("permissions.delete")),  # noqa: B008
):
    permission = await rbac_service.get_permission_by_id_async(session, permission_id)
    if permission is None:
        raise TenxyteAPIError("Permission not found", code="NOT_FOUND", status_code=404)
    await rbac_service.delete_permission_async(session, permission)
    return {"message": "Permission deleted"}


# ============================================================
# Roles
# ============================================================


@router.get("/roles/")
async def list_roles(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    is_default_param = request.query_params.get("is_default")
    is_default = None
    if is_default_param is not None:
        is_default = is_default_param.lower() in ("true", "1", "yes")

    rows, total = await rbac_service.list_roles_async(
        session,
        search=request.query_params.get("search", "").strip(),
        is_default=is_default,
        ordering=request.query_params.get("ordering", "name"),
        page=page,
        page_size=page_size,
    )
    items = [rbac_service.serialize_role_list_item(r) for r in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.post("/roles/", status_code=201)
async def create_role(
    body: RoleCreateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.create")),  # noqa: B008
):
    row = await rbac_service.create_role_async(
        session,
        code=body.code,
        name=body.name,
        description=body.description,
        is_default=body.is_default,
        permission_codes=body.permission_codes,
    )
    return await rbac_service.serialize_role_async(session, row)


@router.get("/roles/{role_id}/")
async def get_role(
    role_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.view")),  # noqa: B008
):
    role = await rbac_service.get_role_by_id_async(session, role_id)
    if role is None:
        raise TenxyteAPIError("Role not found", code="NOT_FOUND", status_code=404)
    return await rbac_service.serialize_role_async(session, role)


@router.put("/roles/{role_id}/")
async def update_role(
    role_id: str,
    body: RoleUpdateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.update")),  # noqa: B008
):
    role = await rbac_service.get_role_by_id_async(session, role_id)
    if role is None:
        raise TenxyteAPIError("Role not found", code="NOT_FOUND", status_code=404)
    updated = await rbac_service.update_role_async(
        session,
        role,
        name=body.name,
        description=body.description,
        is_default=body.is_default,
        permission_codes=body.permission_codes,
    )
    return await rbac_service.serialize_role_async(session, updated)


@router.delete("/roles/{role_id}/")
async def delete_role(
    role_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.delete")),  # noqa: B008
):
    role = await rbac_service.get_role_by_id_async(session, role_id)
    if role is None:
        raise TenxyteAPIError("Role not found", code="NOT_FOUND", status_code=404)
    await rbac_service.delete_role_async(session, role)
    return {"message": "Role deleted"}


@router.get("/roles/{role_id}/permissions/")
async def get_role_permissions(
    role_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.manage_permissions")),  # noqa: B008
):
    role = await rbac_service.get_role_by_id_async(session, role_id)
    if role is None:
        raise TenxyteAPIError("Role not found", code="NOT_FOUND", status_code=404)
    permissions = await rbac_service.get_role_permissions_async(session, role.id)
    return {
        "role_id": role.id,
        "role_code": role.code,
        "permissions": [await rbac_service.serialize_permission_async(session, p) for p in permissions],
    }


@router.post("/roles/{role_id}/permissions/")
async def add_role_permissions(
    role_id: str,
    body: ManageRolePermissionsRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.manage_permissions")),  # noqa: B008
):
    role = await rbac_service.get_role_by_id_async(session, role_id)
    if role is None:
        raise TenxyteAPIError("Role not found", code="NOT_FOUND", status_code=404)
    if not body.permission_codes:
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"permission_codes": ["This field must not be empty."]},
        )

    result = await rbac_service.add_role_permissions_async(session, role, body.permission_codes)
    if result.get("error") == "not_found":
        raise TenxyteAPIError(
            "Some permissions not found",
            code="PERMISSIONS_NOT_FOUND",
            status_code=400,
            extra={"not_found": result["not_found"]},
        )

    permissions = await rbac_service.get_role_permissions_async(session, role.id)
    response_data: dict = {
        "message": f"{len(result['added'])} permission(s) added",
        "added": result["added"],
        "role_code": role.code,
        "permissions": [await rbac_service.serialize_permission_async(session, p) for p in permissions],
    }
    if result["already_assigned"]:
        response_data["already_assigned"] = result["already_assigned"]
    return response_data


@router.delete("/roles/{role_id}/permissions/")
async def remove_role_permissions(
    role_id: str,
    body: ManageRolePermissionsRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("roles.manage_permissions")),  # noqa: B008
):
    role = await rbac_service.get_role_by_id_async(session, role_id)
    if role is None:
        raise TenxyteAPIError("Role not found", code="NOT_FOUND", status_code=404)
    if not body.permission_codes:
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"permission_codes": ["This field must not be empty."]},
        )

    result = await rbac_service.remove_role_permissions_async(session, role, body.permission_codes)
    if result.get("error") == "not_found":
        raise TenxyteAPIError(
            "Some permissions not found",
            code="PERMISSIONS_NOT_FOUND",
            status_code=400,
            extra={"not_found": result["not_found"]},
        )

    permissions = await rbac_service.get_role_permissions_async(session, role.id)
    response_data: dict = {
        "message": f"{len(result['removed'])} permission(s) removed",
        "removed": result["removed"],
        "role_code": role.code,
        "permissions": [await rbac_service.serialize_permission_async(session, p) for p in permissions],
    }
    if result["not_removed"]:
        response_data["not_removed"] = result["not_removed"]
    return response_data


# ============================================================
# User <-> Role
# ============================================================


@router.get("/users/{user_id}/roles/")
async def get_user_roles(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.roles.view")),  # noqa: B008
):
    user = await session.get(UserDB, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    roles = await rbac_service.get_user_roles_async(session, user_id)
    return {"user_id": user.id, "roles": [rbac_service.serialize_role_list_item(r) for r in roles]}


@router.post("/users/{user_id}/roles/")
async def assign_user_role(
    user_id: str,
    body: AssignRoleRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.roles.assign")),  # noqa: B008
):
    user = await session.get(UserDB, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)

    if await rbac_service.assign_role_async(session, user_id, body.role_code):
        roles = await rbac_service.get_all_role_codes_async(session, user_id)
        return {"message": "Role assigned", "roles": roles}
    raise TenxyteAPIError("Role not found", code="ROLE_NOT_FOUND", status_code=404)


@router.delete("/users/{user_id}/roles/")
async def remove_user_role(
    user_id: str,
    role_code: str = Query(""),
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.roles.remove")),  # noqa: B008
):
    user = await session.get(UserDB, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)

    if not role_code:
        raise TenxyteAPIError("role_code query parameter required", code="MISSING_PARAM", status_code=400)

    if await rbac_service.remove_role_async(session, user_id, role_code):
        roles = await rbac_service.get_all_role_codes_async(session, user_id)
        return {"message": "Role removed", "roles": roles}
    raise TenxyteAPIError("Role not found", code="ROLE_NOT_FOUND", status_code=404)


# ============================================================
# User <-> direct Permission
# ============================================================


@router.get("/users/{user_id}/permissions/")
async def get_user_direct_permissions(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.permissions.view")),  # noqa: B008
):
    user = await session.get(UserDB, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)

    direct = await rbac_service.get_user_direct_permissions_async(session, user_id)
    all_permissions = await rbac_service.effective_permission_codes_async(session, user_id)
    return {
        "user_id": user.id,
        "email": user.email,
        "direct_permissions": [await rbac_service.serialize_permission_async(session, p) for p in direct],
        "all_permissions": all_permissions,
    }


@router.post("/users/{user_id}/permissions/")
async def add_user_permissions(
    user_id: str,
    body: ManageRolePermissionsRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.permissions.assign")),  # noqa: B008
):
    user = await session.get(UserDB, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    if not body.permission_codes:
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"permission_codes": ["This field must not be empty."]},
        )

    result = await rbac_service.add_user_direct_permissions_async(session, user_id, body.permission_codes)
    if result.get("error") == "not_found":
        raise TenxyteAPIError(
            "Some permissions not found",
            code="PERMISSIONS_NOT_FOUND",
            status_code=400,
            extra={"not_found": result["not_found"]},
        )

    direct = await rbac_service.get_user_direct_permissions_async(session, user_id)
    response_data: dict = {
        "message": f"{len(result['added'])} permission(s) added",
        "added": result["added"],
        "user_id": user.id,
        "direct_permissions": [await rbac_service.serialize_permission_async(session, p) for p in direct],
    }
    if result["already_assigned"]:
        response_data["already_assigned"] = result["already_assigned"]
    return response_data


@router.delete("/users/{user_id}/permissions/")
async def remove_user_permissions(
    user_id: str,
    body: ManageRolePermissionsRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("users.permissions.remove")),  # noqa: B008
):
    user = await session.get(UserDB, user_id)
    if user is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)
    if not body.permission_codes:
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"permission_codes": ["This field must not be empty."]},
        )

    result = await rbac_service.remove_user_direct_permissions_async(session, user_id, body.permission_codes)
    if result.get("error") == "not_found":
        raise TenxyteAPIError(
            "Some permissions not found",
            code="PERMISSIONS_NOT_FOUND",
            status_code=400,
            extra={"not_found": result["not_found"]},
        )

    direct = await rbac_service.get_user_direct_permissions_async(session, user_id)
    response_data: dict = {
        "message": f"{len(result['removed'])} permission(s) removed",
        "removed": result["removed"],
        "user_id": user.id,
        "direct_permissions": [await rbac_service.serialize_permission_async(session, p) for p in direct],
    }
    if result["not_removed"]:
        response_data["not_removed"] = result["not_removed"]
    return response_data
