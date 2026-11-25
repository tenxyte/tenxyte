"""
Parity_Group E — Organizations (spec z_aud_3, Wave E, task 11.1): organization CRUD (chunk 1/4:
create, list, get, update, delete), hierarchy tree and org-roles listing (chunk 2/4), member
management (chunk 3/4: list, add, update role, remove), invitations (chunk 4/4: invite_member —
the last of Group E's 12 real endpoints). Contract extracted from `views/organization_views.py`
(`create_organization`, `list_organizations`, `get_organization`, `update_organization`,
`delete_organization`, `get_organization_tree`, `list_org_roles`, `list_members`, `add_member`,
`update_member_role`, `remove_member`, `invite_member`). Only registered into the app when
`settings.organizations_enabled` is `True` (see `app.py`) — mirrors Django's own
conditionally-registered `urlpatterns` block exactly (a disabled deployment 404s on these paths
rather than getting a JSON `ORG_FEATURE_DISABLED` body; see `org_context.py`'s module docstring
for why that body only exists as unreachable defense-in-depth on both adapters).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import org_service
from tenxyte.adapters.fastapi.deps import get_db_session, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.adapters.fastapi.org_context import (
    OrgAuthContext,
    require_org_admin,
    require_org_membership,
    require_org_owner,
    require_org_permission,
)
from tenxyte.adapters.fastapi.pagination import get_page_params, paginated_response
from tenxyte.adapters.fastapi.schemas import (
    OrganizationAddMemberRequest,
    OrganizationCreateRequest,
    OrganizationInviteMemberRequest,
    OrganizationUpdateMemberRoleRequest,
    OrganizationUpdateRequest,
)
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.core.settings import Settings

router = APIRouter()


@router.post("/organizations/", status_code=201)
async def create_organization(
    body: OrganizationCreateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    organization, error = await org_service.create_organization_async(
        session,
        name=body.name,
        created_by_id=auth.user.id,
        slug=body.slug or None,
        description=body.description,
        parent_id=body.parent_id,
        metadata=body.metadata,
        max_members=body.max_members,
        org_max_members_default=settings.org_max_members,
        org_max_depth=settings.org_max_depth,
    )
    if error is not None:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return await org_service.serialize_organization_async(session, organization, current_user_id=auth.user.id)


@router.get("/organizations/list/")
async def list_organizations(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    page, page_size = get_page_params(request)
    is_active_param = request.query_params.get("is_active")
    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() in ("true", "1", "yes")

    rows, total = await org_service.list_organizations_async(
        session,
        auth.user.id,
        search=request.query_params.get("search", "").strip(),
        is_active=is_active,
        parent=request.query_params.get("parent"),
        ordering=request.query_params.get("ordering", "name"),
        page=page,
        page_size=page_size,
    )
    items = [await org_service.serialize_organization_async(session, org, current_user_id=auth.user.id) for org in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.get("/organizations/detail/")
async def get_organization(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_membership()),  # noqa: B008
):
    return await org_service.serialize_organization_async(session, ctx.organization, current_user_id=ctx.auth.user.id)


@router.patch("/organizations/update/")
async def update_organization(
    body: OrganizationUpdateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_admin()),  # noqa: B008
):
    updates = body.model_dump(exclude_unset=True)
    success, error = await org_service.update_organization_async(
        session, ctx.organization, ctx.auth.user.id, org_role_inheritance=settings.org_role_inheritance, **updates
    )
    if not success:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return await org_service.serialize_organization_async(session, ctx.organization, current_user_id=ctx.auth.user.id)


@router.delete("/organizations/delete/")
async def delete_organization(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_owner()),  # noqa: B008
):
    success, error = await org_service.delete_organization_async(session, ctx.organization, ctx.auth.user.id)
    if not success:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return {"message": "Organization deleted successfully"}


@router.get("/organizations/tree/")
async def get_organization_tree(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_membership()),  # noqa: B008
):
    return await org_service.get_organization_tree_async(session, ctx.organization)


@router.get("/org-roles/")
async def list_org_roles(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    roles = await org_service.list_org_roles_async(session)
    return [org_service.serialize_org_role(role) for role in roles]


@router.get("/organizations/members/")
async def list_members(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_membership()),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await org_service.list_members_async(
        session,
        ctx.organization.id,
        search=request.query_params.get("search", "").strip(),
        role=request.query_params.get("role"),
        status=request.query_params.get("status", "active"),
        ordering=request.query_params.get("ordering", "-created_at"),
        page=page,
        page_size=page_size,
    )
    items = [await org_service.serialize_membership_async(session, m) for m in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.post("/organizations/members/add/", status_code=201)
async def add_member(
    body: OrganizationAddMemberRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_permission("org.members.invite")),  # noqa: B008
):
    user_to_add = await session.get(UserDB, body.user_id)
    if user_to_add is None:
        raise TenxyteAPIError("User not found", code=None, status_code=404)

    membership, error = await org_service.add_member_async(
        session,
        ctx.organization,
        user_to_add.id,
        body.role_code,
        ctx.auth.user.id,
        org_role_inheritance=settings.org_role_inheritance,
    )
    if error is not None:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return await org_service.serialize_membership_async(session, membership)


@router.patch("/organizations/members/{user_id}/")
async def update_member_role(
    user_id: str,
    body: OrganizationUpdateMemberRoleRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_permission("org.members.manage")),  # noqa: B008
):
    user_to_update = await session.get(UserDB, user_id)
    if user_to_update is None:
        raise TenxyteAPIError("User not found", code=None, status_code=404)

    success, error = await org_service.update_member_role_async(
        session,
        ctx.organization,
        user_to_update.id,
        body.role_code,
        ctx.auth.user.id,
        org_role_inheritance=settings.org_role_inheritance,
    )
    if not success:
        raise TenxyteAPIError(error, code=None, status_code=400)

    membership = await org_service.get_org_membership_async(session, user_to_update.id, ctx.organization.id)
    return await org_service.serialize_membership_async(session, membership)


@router.delete("/organizations/members/{user_id}/remove/")
async def remove_member(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_permission("org.members.remove")),  # noqa: B008
):
    user_to_remove = await session.get(UserDB, user_id)
    if user_to_remove is None:
        raise TenxyteAPIError("User not found", code=None, status_code=404)

    success, error = await org_service.remove_member_async(
        session,
        ctx.organization,
        user_to_remove.id,
        ctx.auth.user.id,
        org_role_inheritance=settings.org_role_inheritance,
    )
    if not success:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return {"message": "Member removed successfully"}


@router.post("/organizations/invitations/", status_code=201)
async def invite_member(
    body: OrganizationInviteMemberRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    ctx: OrgAuthContext = Depends(require_org_permission("org.members.invite")),  # noqa: B008
):
    invitation, error = await org_service.create_invitation_async(
        session,
        ctx.organization,
        email=body.email,
        role_code=body.role_code,
        invited_by_id=ctx.auth.user.id,
        expires_in_days=body.expires_in_days,
        org_role_inheritance=settings.org_role_inheritance,
    )
    if error is not None:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return await org_service.serialize_invitation_async(session, invitation)
