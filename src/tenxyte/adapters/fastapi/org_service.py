"""
Framework-agnostic-in-spirit organizations service for the Reference_Stack (spec z_aud_3, Wave E,
task 11.1) — organization CRUD (create/list/get/update/delete), hierarchy (tree, chunk 2/4),
org-roles listing (chunk 2/4), and membership/permission resolution shared by every chunk.
Contract extracted from `views/organization_views.py`,
`services/organization_service.py`'s `OrganizationService`, `serializers/organization_serializers.py`,
`filters.py` (`apply_organization_filters`), and the `User.get_org_*`/`has_org_*`/`is_org_*` methods
on `models/auth.py`. Like `rbac_service.py`, Django never extracted this to Core — this is a new
implementation verified against the real service/model code, not a port of existing Core code.

**Error responses have no `code` field, verified by reading every actual `return Response(...)`
call site in `organization_views.py` (not assumed from its `@extend_schema`/`OpenApiExample`
blocks, which document a `code` key — e.g. `NOT_OWNER`, `HIERARCHY_DEPTH_LIMIT` — that the real
code never emits).** Every error body is exactly `{"error": "<message>"}`; `TenxyteAPIError`
callers in `routers/orgs.py` therefore pass `code=None` throughout this wave, unlike every other
Wave A-D router. Validation errors (missing/invalid request fields) are DRF's own
`serializer.errors` shape (field-name-keyed), which this port's Pydantic layer already produces
close enough via FastAPI's default 422 — not specially replicated field-by-field.

**`update_organization`'s real accepted fields are only `name`/`description`/`metadata`/
`max_members`** — despite the Django view's own `@extend_schema` documenting `slug`/`parent_id`/
`is_active` and describing hierarchy-move validation, `UpdateOrganizationSerializer` doesn't
expose those fields at all, so they can never reach the service; there is no circular-hierarchy
check on update (that logic exists only in `OrganizationService.move_organization`, which no view
in `organization_views.py` calls — `PATCH .../update/` can never change an org's parent). Not
replicated here either, for the same reason: matching the real, reachable behavior, not the
aspirational docs.

**No default `OrganizationRole` rows are auto-seeded beyond `owner`** — verified by grepping every
`OrganizationRole.objects.create`/`get_or_create` call site in the whole Django codebase: only two
exist, both in `OrganizationService` — `create_organization` lazily `get_or_create`s just the
`owner` role (permissions `["org.*"]`) the first time any organization is created, and
`initialize_system_roles` (which would also create `admin`/`member`/`viewer`) is never invoked by
any application code path — no signal, no management command, no `AppConfig.ready()` hook. It's
only ever called from Django's own test fixtures. `initialize_system_roles_async` is ported here
for the same reason (test/seed symmetry) but is likewise never auto-invoked.

**`create_organization` has no permission check against `parent_id` at all** — verified by reading
the view: it's gated only by `@require_jwt`, nothing else. Any authenticated user who knows another
organization's id can nest a brand-new organization under it (subject only to the parent's depth
limit) and become that new child's owner, with zero relationship to the parent required — not a
membership, not any role, not even knowledge of the parent's slug (numeric `parent_id`, not slug).
Replicated exactly: `create_organization_async` below performs no such check either.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import (
    AuditLogDB,
    OrganizationDB,
    OrganizationInvitationDB,
    OrganizationMembershipDB,
    OrganizationRoleDB,
    UserDB,
)
from tenxyte.adapters.fastapi.pagination import apply_ordering

OWNER_ROLE_CODE = "owner"


# ============================================================
# Hierarchy
# ============================================================


async def _ancestors_async(session: AsyncSession, organization: OrganizationDB) -> list[OrganizationDB]:
    """Mirrors `Organization.get_ancestors(include_self=False)` — walks the parent chain to the
    root, not including `organization` itself."""
    ancestors: list[OrganizationDB] = []
    current = organization
    while current.parent_id:
        parent = await session.get(OrganizationDB, current.parent_id)
        if parent is None:
            break
        ancestors.append(parent)
        current = parent
    return ancestors


async def _depth_async(session: AsyncSession, organization: OrganizationDB) -> int:
    """Mirrors `Organization.depth` (root = 0)."""
    return len(await _ancestors_async(session, organization))


async def _can_add_child_async(session: AsyncSession, organization: OrganizationDB, *, org_max_depth: int) -> bool:
    """Mirrors `Organization.can_add_child()`: `self.depth < ORG_MAX_DEPTH - 1`."""
    return await _depth_async(session, organization) < org_max_depth - 1


async def get_root_async(session: AsyncSession, organization: OrganizationDB) -> OrganizationDB:
    """Mirrors `Organization.get_root()`."""
    current = organization
    while current.parent_id:
        parent = await session.get(OrganizationDB, current.parent_id)
        if parent is None:
            break
        current = parent
    return current


async def get_organization_tree_async(session: AsyncSession, organization: OrganizationDB) -> dict:
    """Mirrors `OrganizationService.get_organization_tree` exactly — including the real (if
    slightly surprising) behavior that it always builds the tree from the *root* ancestor down,
    not from `organization` itself: even scoped into a child via `X-Org-Slug`, the response starts
    at the top of the hierarchy. Active children only at every level (`children.filter(is_active=
    True)`), recursive."""

    async def _build(org: OrganizationDB) -> dict:
        children_stmt = select(OrganizationDB).where(
            OrganizationDB.parent_id == org.id, OrganizationDB.is_active.is_(True)
        )
        children = (await session.execute(children_stmt)).scalars().all()
        return {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "depth": await _depth_async(session, org),
            "is_root": org.parent_id is None,
            "member_count": await get_member_count_async(session, org.id),
            "children": [await _build(child) for child in children],
        }

    root = await get_root_async(session, organization)
    return await _build(root)


# ============================================================
# Membership / permission resolution
# ============================================================


async def get_org_membership_async(
    session: AsyncSession, user_id: str, organization_id: str
) -> OrganizationMembershipDB | None:
    stmt = select(OrganizationMembershipDB).where(
        OrganizationMembershipDB.user_id == user_id, OrganizationMembershipDB.organization_id == organization_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def is_org_member_async(session: AsyncSession, user_id: str, organization_id: str) -> bool:
    membership = await get_org_membership_async(session, user_id, organization_id)
    return membership is not None and membership.status == "active"


async def get_org_role_async(session: AsyncSession, user_id: str, organization_id: str) -> OrganizationRoleDB | None:
    """Mirrors `User.get_org_role()` — the role of the direct membership only, no inheritance
    (used by `OrganizationSerializer.get_user_role`, which never checks ancestors either)."""
    membership = await get_org_membership_async(session, user_id, organization_id)
    if membership is None:
        return None
    return await session.get(OrganizationRoleDB, membership.role_id)


def _role_has_permission(permissions: list[str], permission_code: str) -> bool:
    """Mirrors `OrganizationRole.has_permission()`: exact match, or a `"prefix.*"` wildcard
    matching `permission_code == prefix` or `permission_code.startswith(prefix + ".")`."""
    for perm in permissions:
        if perm == permission_code:
            return True
        if perm.endswith(".*"):
            prefix = perm[:-2]
            if permission_code == prefix or permission_code.startswith(prefix + "."):
                return True
    return False


async def has_org_role_async(
    session: AsyncSession,
    user_id: str,
    organization: OrganizationDB,
    role_code: str,
    *,
    check_inheritance: bool = True,
    org_role_inheritance: bool = True,
) -> bool:
    """Mirrors `User.has_org_role()` exactly."""
    membership = await get_org_membership_async(session, user_id, organization.id)
    if membership is not None and membership.status == "active":
        role = await session.get(OrganizationRoleDB, membership.role_id)
        if role is not None and role.code == role_code:
            return True

    if check_inheritance and org_role_inheritance:
        for ancestor in await _ancestors_async(session, organization):
            ancestor_membership = await get_org_membership_async(session, user_id, ancestor.id)
            if ancestor_membership is not None and ancestor_membership.status == "active":
                role = await session.get(OrganizationRoleDB, ancestor_membership.role_id)
                if role is not None and role.code == role_code:
                    return True

    return False


async def has_org_permission_async(
    session: AsyncSession,
    user_id: str,
    organization: OrganizationDB,
    permission_code: str,
    *,
    check_inheritance: bool = True,
    org_role_inheritance: bool = True,
) -> bool:
    """Mirrors `User.has_org_permission()` exactly."""
    membership = await get_org_membership_async(session, user_id, organization.id)
    if membership is not None and membership.status == "active":
        role = await session.get(OrganizationRoleDB, membership.role_id)
        if role is not None and _role_has_permission(role.permissions, permission_code):
            return True

    if check_inheritance and org_role_inheritance:
        for ancestor in await _ancestors_async(session, organization):
            ancestor_membership = await get_org_membership_async(session, user_id, ancestor.id)
            if ancestor_membership is not None and ancestor_membership.status == "active":
                role = await session.get(OrganizationRoleDB, ancestor_membership.role_id)
                if role is not None and _role_has_permission(role.permissions, permission_code):
                    return True

    return False


async def get_member_count_async(session: AsyncSession, organization_id: str) -> int:
    """Mirrors `Organization.get_member_count()` — active members only."""
    stmt = select(func.count(OrganizationMembershipDB.id)).where(
        OrganizationMembershipDB.organization_id == organization_id, OrganizationMembershipDB.status == "active"
    )
    return (await session.execute(stmt)).scalar_one()


async def is_at_member_limit_async(session: AsyncSession, organization: OrganizationDB) -> bool:
    """Mirrors `Organization.is_at_member_limit()` — `max_members == 0` always means unlimited."""
    if organization.max_members == 0:
        return False
    return await get_member_count_async(session, organization.id) >= organization.max_members


async def get_user_organizations_async(session: AsyncSession, user_id: str) -> list[OrganizationDB]:
    """Mirrors `User.get_organizations()` — organizations the user is an *active* member of."""
    stmt = (
        select(OrganizationDB)
        .join(OrganizationMembershipDB, OrganizationMembershipDB.organization_id == OrganizationDB.id)
        .where(OrganizationMembershipDB.user_id == user_id, OrganizationMembershipDB.status == "active")
        .distinct()
    )
    return list((await session.execute(stmt)).scalars().all())


# ============================================================
# Serialization — matches OrganizationSerializer exactly.
# ============================================================


async def serialize_organization_async(
    session: AsyncSession, organization: OrganizationDB, *, current_user_id: str | None = None
) -> dict:
    """Matches `OrganizationSerializer` exactly, **including a real DRF quirk verified by the
    Contract_Suite (task 11.2), not just static reading**: `parent_name`/`created_by_email` are
    `CharField(source="parent.name" / "created_by.email", read_only=True)` — a *dotted* source
    DRF resolves by attribute-chasing the instance. When the first hop (`parent`/`created_by`) is
    `None`, that chase raises `AttributeError`; DRF's `Field.get_attribute()` catches it and,
    because a `read_only` field is implicitly `required=False`, raises `SkipField()` instead of
    falling back to `None` — so the key is **omitted from the response body entirely**, not
    present with a `null` value. `parent` itself (a plain FK field, not a dotted `CharField`
    source) still serializes as `null` normally when there's no parent — only the *_name/*_email
    sibling fields disappear. Both are handled the same way below since both use the same DRF
    dotted-source pattern, even though only `parent_name` is empirically exercised by
    `create_organization` (every org this port can create always has a real `created_by`)."""
    fields = {
        "id": organization.id,
        "name": organization.name,
        "slug": organization.slug,
        "description": organization.description,
        "parent": organization.parent_id,
        "metadata": organization.org_metadata,
        "is_active": organization.is_active,
        "max_members": organization.max_members,
        "member_count": await get_member_count_async(session, organization.id),
        "created_at": organization.created_at.isoformat(),
        "updated_at": organization.updated_at.isoformat(),
    }

    if organization.parent_id:
        parent = await session.get(OrganizationDB, organization.parent_id)
        if parent is not None:
            fields["parent_name"] = parent.name

    if organization.created_by_id:
        creator = await session.get(UserDB, organization.created_by_id)
        if creator is not None:
            fields["created_by_email"] = creator.email

    if current_user_id:
        role = await get_org_role_async(session, current_user_id, organization.id)
        fields["user_role"] = role.code if role else None
    else:
        fields["user_role"] = None

    return fields


# ============================================================
# CRUD
# ============================================================


async def _audit_log_async(session: AsyncSession, action: str, user_id: str | None, details: dict) -> None:
    """Mirrors `OrganizationService._audit_log` — `ip_address` is always `None` from this service,
    same as Django (never sourced from the request here either)."""
    session.add(AuditLogDB(action=action, user_id=user_id, ip_address=None, details=details))
    await session.commit()


def _slugify(name: str) -> str:
    """A minimal `django.utils.text.slugify` equivalent for the ASCII organization names this
    port's tests use: lowercase, non-alphanumerics collapsed to single hyphens, stripped."""
    import re

    slug = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug).strip("-")


async def create_organization_async(
    session: AsyncSession,
    *,
    name: str,
    created_by_id: str,
    slug: str | None = None,
    description: str = "",
    parent_id: str | None = None,
    metadata: dict | None = None,
    max_members: int = 0,
    org_max_members_default: int = 0,
    org_max_depth: int = 5,
) -> tuple[OrganizationDB | None, str | None]:
    """Mirrors `OrganizationService.create_organization` — returns `(organization, error)`."""
    if not slug:
        slug = _slugify(name)
        base_slug = slug
        counter = 1
        while (await session.execute(select(OrganizationDB).where(OrganizationDB.slug == slug))).scalar_one_or_none():
            slug = f"{base_slug}-{counter}"
            counter += 1

    parent = None
    if parent_id:
        parent = await session.get(OrganizationDB, parent_id)
        if parent is None:
            return None, "Parent organization not found"
        if not await _can_add_child_async(session, parent, org_max_depth=org_max_depth):
            return None, f"Maximum organization depth ({org_max_depth}) reached"

    organization = OrganizationDB(
        name=name,
        slug=slug,
        description=description,
        parent_id=parent.id if parent else None,
        org_metadata=metadata or {},
        # Mirrors `max_members or org_settings.ORG_MAX_MEMBERS` exactly — with default settings
        # (both default to 0) this is a no-op, but a deployment that overrides ORG_MAX_MEMBERS to
        # a nonzero value would see `max_members=0` requests silently get that default instead of
        # "unlimited" (Django's real, slightly surprising behavior — not "fixed" here).
        max_members=max_members or org_max_members_default,
        created_by_id=created_by_id,
    )
    session.add(organization)
    await session.commit()
    await session.refresh(organization)

    owner_role_stmt = select(OrganizationRoleDB).where(OrganizationRoleDB.code == OWNER_ROLE_CODE)
    owner_role = (await session.execute(owner_role_stmt)).scalar_one_or_none()
    if owner_role is None:
        owner_role = OrganizationRoleDB(
            code=OWNER_ROLE_CODE,
            name="Owner",
            description="Organization owner with full access",
            is_system=True,
            permissions=["org.*"],
        )
        session.add(owner_role)
        await session.commit()
        await session.refresh(owner_role)

    session.add(
        OrganizationMembershipDB(
            user_id=created_by_id, organization_id=organization.id, role_id=owner_role.id, status="active"
        )
    )
    await session.commit()

    await _audit_log_async(
        session,
        "organization_created",
        created_by_id,
        {
            "organization_id": organization.id,
            "organization_name": organization.name,
            "slug": organization.slug,
            "parent_id": parent_id,
        },
    )

    return organization, None


async def get_organization_by_slug_async(session: AsyncSession, slug: str) -> OrganizationDB | None:
    """Mirrors `OrganizationService.get_organization(slug=...)` — only ever returns an active
    organization (soft-deleted organizations are invisible here, same as Django)."""
    stmt = select(OrganizationDB).where(OrganizationDB.slug == slug, OrganizationDB.is_active.is_(True))
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_organizations_async(
    session: AsyncSession,
    user_id: str,
    *,
    search: str = "",
    is_active: bool | None = None,
    parent: str | None = None,
    ordering: str = "name",
    page: int,
    page_size: int,
) -> tuple[list[OrganizationDB], int]:
    """Mirrors `list_organizations`: `request.user.get_organizations()` filtered by
    `apply_organization_filters`."""
    org_ids_stmt = (
        select(OrganizationMembershipDB.organization_id)
        .where(OrganizationMembershipDB.user_id == user_id, OrganizationMembershipDB.status == "active")
        .distinct()
    )
    stmt = select(OrganizationDB).where(OrganizationDB.id.in_(org_ids_stmt))
    count_stmt = select(func.count(OrganizationDB.id)).where(OrganizationDB.id.in_(org_ids_stmt))

    if search:
        like = f"%{search}%"
        clause = or_(OrganizationDB.name.ilike(like), OrganizationDB.slug.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if is_active is not None:
        stmt = stmt.where(OrganizationDB.is_active == is_active)
        count_stmt = count_stmt.where(OrganizationDB.is_active == is_active)

    if parent is not None:
        if parent.lower() == "null" or parent == "":
            stmt = stmt.where(OrganizationDB.parent_id.is_(None))
            count_stmt = count_stmt.where(OrganizationDB.parent_id.is_(None))
        else:
            stmt = stmt.where(OrganizationDB.parent_id == parent)
            count_stmt = count_stmt.where(OrganizationDB.parent_id == parent)

    allowed_ordering = {
        "name": OrganizationDB.name,
        "slug": OrganizationDB.slug,
        "created_at": OrganizationDB.created_at,
        "is_active": OrganizationDB.is_active,
    }
    stmt = apply_ordering(stmt, ordering, allowed_ordering, default="name")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


async def update_organization_async(
    session: AsyncSession,
    organization: OrganizationDB,
    user_id: str,
    *,
    org_role_inheritance: bool = True,
    **updates,
) -> tuple[bool, str | None]:
    """Mirrors `OrganizationService.update_organization` exactly, including its field whitelist
    (`name`/`description`/`metadata`/`max_members` — anything else in `updates` is silently
    ignored) and its `has_org_role(..., "owner") or has_org_role(..., "admin")` permission check
    (default `check_inheritance=True` on both, so an admin/owner role held in an ancestor
    organization satisfies this too, when `org_role_inheritance` is enabled)."""
    is_owner = await has_org_role_async(
        session, user_id, organization, "owner", org_role_inheritance=org_role_inheritance
    )
    is_admin = await has_org_role_async(
        session, user_id, organization, "admin", org_role_inheritance=org_role_inheritance
    )
    if not is_owner and not is_admin:
        return False, "Insufficient permissions to update organization"

    if "max_members" in updates:
        new_max = updates["max_members"]
        if new_max > 0:
            current_count = await get_member_count_async(session, organization.id)
            if new_max < current_count:
                return False, (
                    f"Cannot set max_members to {new_max}: " f"organization already has {current_count} active members"
                )

    allowed_fields = {"name", "description", "max_members"}
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(organization, field, value)
        elif field == "metadata":
            organization.org_metadata = value

    organization.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(organization)

    await _audit_log_async(
        session, "organization_updated", user_id, {"organization_id": organization.id, "updates": updates}
    )

    return True, None


async def delete_organization_async(
    session: AsyncSession, organization: OrganizationDB, user_id: str
) -> tuple[bool, str | None]:
    """Mirrors `OrganizationService.delete_organization` — owner-only, `check_inheritance=False`
    (an inherited owner role from an ancestor org does NOT count), soft delete."""
    is_owner = await has_org_role_async(session, user_id, organization, "owner", check_inheritance=False)
    if not is_owner:
        return False, "Only the owner can delete an organization"

    children_stmt = select(func.count(OrganizationDB.id)).where(OrganizationDB.parent_id == organization.id)
    if (await session.execute(children_stmt)).scalar_one() > 0:
        return False, "Cannot delete organization with child organizations"

    organization.is_active = False
    await session.commit()

    await _audit_log_async(
        session,
        "organization_deleted",
        user_id,
        {"organization_id": organization.id, "organization_name": organization.name},
    )

    return True, None


# ============================================================
# Member management (Wave E chunk 3/4)
# ============================================================


async def serialize_membership_async(session: AsyncSession, membership: OrganizationMembershipDB) -> dict:
    """Matches `OrganizationMembershipSerializer` exactly — nested `user`/`role` objects, not just
    ids/codes."""
    user = await session.get(UserDB, membership.user_id)
    role = await session.get(OrganizationRoleDB, membership.role_id)
    organization = await session.get(OrganizationDB, membership.organization_id)
    return {
        "id": membership.id,
        "user": (
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            if user
            else None
        ),
        "organization_name": organization.name if organization else None,
        "role": serialize_org_role(role) if role else None,
        "status": membership.status,
        "invited_by": membership.invited_by_id,
        "invited_at": membership.invited_at.isoformat() if membership.invited_at else None,
        "created_at": membership.created_at.isoformat(),
        "updated_at": membership.updated_at.isoformat(),
    }


async def get_members_async(
    session: AsyncSession, organization_id: str, *, status: str | None = "active"
) -> list[OrganizationMembershipDB]:
    """Mirrors `OrganizationService.get_members` — defaults to `status="active"` (applied before
    `apply_member_filters`'s own optional `?status=` even runs, so pending/suspended memberships
    are excluded from `list_members` by default, not just filterable)."""
    stmt = select(OrganizationMembershipDB).where(OrganizationMembershipDB.organization_id == organization_id)
    if status:
        stmt = stmt.where(OrganizationMembershipDB.status == status)
    stmt = stmt.order_by(OrganizationMembershipDB.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def list_members_async(
    session: AsyncSession,
    organization_id: str,
    *,
    search: str = "",
    role: str | None = None,
    status: str | None = "active",
    ordering: str = "-created_at",
    page: int,
    page_size: int,
) -> tuple[list[OrganizationMembershipDB], int]:
    """Mirrors `list_members`: `get_members(organization)` (already `status="active"`-filtered by
    default) then `apply_member_filters`'s own `search`/`role`/`status`/`ordering`. Any `status`
    value here is accepted verbatim (not restricted to a fixed enum, despite the view's own
    `@extend_schema` documenting one) — matching `apply_member_filters`'s real
    `queryset.filter(status=status)`, no validation. `status` defaults to `"active"` here as it
    does in `get_members`; pass `status=None` to see every membership regardless of status."""
    stmt = select(OrganizationMembershipDB).where(OrganizationMembershipDB.organization_id == organization_id)
    count_stmt = select(func.count(OrganizationMembershipDB.id)).where(
        OrganizationMembershipDB.organization_id == organization_id
    )

    if status:
        stmt = stmt.where(OrganizationMembershipDB.status == status)
        count_stmt = count_stmt.where(OrganizationMembershipDB.status == status)

    needs_user_join = search or ordering in ("user__email", "-user__email")
    if needs_user_join:
        stmt = stmt.join(UserDB, UserDB.id == OrganizationMembershipDB.user_id)

    if search:
        count_stmt = count_stmt.join(UserDB, UserDB.id == OrganizationMembershipDB.user_id)
        like = f"%{search}%"
        clause = or_(UserDB.email.ilike(like), UserDB.first_name.ilike(like), UserDB.last_name.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if role:
        role_subq = select(OrganizationRoleDB.id).where(OrganizationRoleDB.code == role)
        stmt = stmt.where(OrganizationMembershipDB.role_id.in_(role_subq))
        count_stmt = count_stmt.where(OrganizationMembershipDB.role_id.in_(role_subq))

    if ordering in ("user__email", "-user__email"):
        stmt = stmt.order_by(UserDB.email.desc() if ordering.startswith("-") else UserDB.email.asc())
    elif ordering in ("role__code", "-role__code"):
        stmt = stmt.join(OrganizationRoleDB, OrganizationRoleDB.id == OrganizationMembershipDB.role_id)
        stmt = stmt.order_by(
            OrganizationRoleDB.code.desc() if ordering.startswith("-") else OrganizationRoleDB.code.asc()
        )
    else:
        allowed_ordering = {
            "created_at": OrganizationMembershipDB.created_at,
            "status": OrganizationMembershipDB.status,
        }
        stmt = apply_ordering(stmt, ordering, allowed_ordering, default="-created_at")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


async def add_member_async(
    session: AsyncSession,
    organization: OrganizationDB,
    user_to_add_id: str,
    role_code: str,
    added_by_id: str,
    *,
    org_role_inheritance: bool = True,
) -> tuple[OrganizationMembershipDB | None, str | None]:
    """Mirrors `OrganizationService.add_member` exactly — order: permission -> member-limit ->
    role lookup -> already-member check -> create."""
    has_permission = await has_org_permission_async(
        session, added_by_id, organization, "org.members.invite", org_role_inheritance=org_role_inheritance
    )
    if not has_permission:
        return None, "Insufficient permissions to add members"

    if await is_at_member_limit_async(session, organization):
        return None, "Organization has reached its member limit"

    role_stmt = select(OrganizationRoleDB).where(OrganizationRoleDB.code == role_code)
    role = (await session.execute(role_stmt)).scalar_one_or_none()
    if role is None:
        return None, f"Role {role_code} not found"

    existing = await get_org_membership_async(session, user_to_add_id, organization.id)
    if existing is not None:
        return None, "User is already a member"

    membership = OrganizationMembershipDB(
        user_id=user_to_add_id,
        organization_id=organization.id,
        role_id=role.id,
        status="active",
        invited_by_id=added_by_id,
        invited_at=datetime.now(timezone.utc),
    )
    session.add(membership)
    await session.commit()
    await session.refresh(membership)

    await _audit_log_async(
        session,
        "member_added",
        added_by_id,
        {"organization_id": organization.id, "user_id": user_to_add_id, "role_code": role_code},
    )

    return membership, None


async def update_member_role_async(
    session: AsyncSession,
    organization: OrganizationDB,
    user_to_update_id: str,
    new_role_code: str,
    updated_by_id: str,
    *,
    org_role_inheritance: bool = True,
) -> tuple[bool, str | None]:
    """Mirrors `OrganizationService.update_member_role` exactly — order: permission -> owner-guard
    (`check_inheritance=False`, unconditional regardless of `new_role_code`) -> membership lookup
    -> new-role lookup -> mutate."""
    has_permission = await has_org_permission_async(
        session, updated_by_id, organization, "org.members.manage", org_role_inheritance=org_role_inheritance
    )
    if not has_permission:
        return False, "Insufficient permissions to manage members"

    is_owner = await has_org_role_async(session, user_to_update_id, organization, "owner", check_inheritance=False)
    if is_owner:
        return False, "Cannot change owner role"

    membership = await get_org_membership_async(session, user_to_update_id, organization.id)
    if membership is None:
        return False, "User is not a member"

    new_role_stmt = select(OrganizationRoleDB).where(OrganizationRoleDB.code == new_role_code)
    new_role = (await session.execute(new_role_stmt)).scalar_one_or_none()
    if new_role is None:
        return False, f"Role {new_role_code} not found"

    old_role = await session.get(OrganizationRoleDB, membership.role_id)
    membership.role_id = new_role.id
    membership.updated_at = datetime.now(timezone.utc)
    await session.commit()

    await _audit_log_async(
        session,
        "member_role_updated",
        updated_by_id,
        {
            "organization_id": organization.id,
            "user_id": user_to_update_id,
            "old_role": old_role.code if old_role else None,
            "new_role": new_role_code,
        },
    )

    return True, None


async def remove_member_async(
    session: AsyncSession,
    organization: OrganizationDB,
    user_to_remove_id: str,
    removed_by_id: str,
    *,
    org_role_inheritance: bool = True,
) -> tuple[bool, str | None]:
    """Mirrors `OrganizationService.remove_member` exactly — order: permission -> owner-guard
    (`check_inheritance=False`) -> membership lookup -> hard delete (not soft)."""
    has_permission = await has_org_permission_async(
        session, removed_by_id, organization, "org.members.remove", org_role_inheritance=org_role_inheritance
    )
    if not has_permission:
        return False, "Insufficient permissions to remove members"

    is_owner = await has_org_role_async(session, user_to_remove_id, organization, "owner", check_inheritance=False)
    if is_owner:
        return False, "Cannot remove organization owner"

    membership = await get_org_membership_async(session, user_to_remove_id, organization.id)
    if membership is None:
        return False, "User is not a member"

    await session.delete(membership)
    await session.commit()

    await _audit_log_async(
        session, "member_removed", removed_by_id, {"organization_id": organization.id, "user_id": user_to_remove_id}
    )

    return True, None


# ============================================================
# Invitations (Wave E chunk 4/4)
# ============================================================


async def serialize_invitation_async(session: AsyncSession, invitation: OrganizationInvitationDB) -> dict:
    """Matches `OrganizationInvitationSerializer` exactly — flattened `organization_name`/
    `role_name`/`invited_by_email` strings, not nested objects (despite the view's own
    `@extend_schema` documenting `organization`/`role`/`invited_by` as nested objects — verified
    against the real serializer, which has none of those three fields)."""
    organization = await session.get(OrganizationDB, invitation.organization_id)
    role = await session.get(OrganizationRoleDB, invitation.role_id)
    invited_by = await session.get(UserDB, invitation.invited_by_id) if invitation.invited_by_id else None
    return {
        "id": invitation.id,
        "organization_name": organization.name if organization else None,
        "email": invitation.email,
        "role_name": role.name if role else None,
        "status": invitation.status,
        "invited_by_email": invited_by.email if invited_by else None,
        "created_at": invitation.created_at.isoformat(),
        "expires_at": invitation.expires_at.isoformat(),
        "token": invitation.token,
    }


async def create_invitation_async(
    session: AsyncSession,
    organization: OrganizationDB,
    *,
    email: str,
    role_code: str,
    invited_by_id: str,
    expires_in_days: int = 7,
    org_role_inheritance: bool = True,
) -> tuple[OrganizationInvitationDB | None, str | None]:
    """Mirrors `OrganizationService.create_invitation` exactly — order: permission -> member-limit
    -> role lookup -> already-a-member check (only if a `User` with that email exists; skipped
    silently otherwise) -> cancel any existing pending invitation for the same `(organization,
    email)` (`status="expired"`, not rejected as a duplicate — see below) -> create.

    **No `INVITATION_EXISTS`/duplicate-rejection error is ever raised** — verified by reading the
    real method: a second invite to the same email silently expires the first and creates a fresh
    one, despite `@extend_schema`'s docs implying a 400 for that case. Replicated exactly.

    **No email is actually sent** — Django's own method body ends with a bare `# TODO: Send
    invitation email` comment; the token is only ever returned in the response body. Not
    replicated with a fake send here either — same "no real delivery backend" posture already
    documented for OTP/magic-link in `otp_service.py`/`login_response.py`, except here Django
    itself never wired one in the first place, not just the Reference_Stack."""
    has_permission = await has_org_permission_async(
        session, invited_by_id, organization, "org.members.invite", org_role_inheritance=org_role_inheritance
    )
    if not has_permission:
        return None, "Insufficient permissions to invite members"

    if await is_at_member_limit_async(session, organization):
        return None, "Organization has reached its member limit"

    role_stmt = select(OrganizationRoleDB).where(OrganizationRoleDB.code == role_code)
    role = (await session.execute(role_stmt)).scalar_one_or_none()
    if role is None:
        return None, f"Role {role_code} not found"

    user_stmt = select(UserDB).where(UserDB.email == email)
    existing_user = (await session.execute(user_stmt)).scalar_one_or_none()
    if existing_user is not None and await is_org_member_async(session, existing_user.id, organization.id):
        return None, "User is already a member"

    await session.execute(
        update(OrganizationInvitationDB)
        .where(
            OrganizationInvitationDB.organization_id == organization.id,
            OrganizationInvitationDB.email == email,
            OrganizationInvitationDB.status == "pending",
        )
        .values(status="expired")
    )

    invitation = OrganizationInvitationDB(
        organization_id=organization.id,
        email=email,
        role_id=role.id,
        token=secrets.token_urlsafe(48),
        invited_by_id=invited_by_id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)

    await _audit_log_async(
        session,
        "invitation_created",
        invited_by_id,
        {
            "organization_id": organization.id,
            "email": email,
            "role_code": role_code,
            "invitation_id": invitation.id,
        },
    )

    return invitation, None


# ============================================================
# Utility — ported for test/seed symmetry with Django, never auto-invoked (see module docstring).
# ============================================================


async def initialize_system_roles_async(session: AsyncSession) -> list[OrganizationRoleDB]:
    """Mirrors `OrganizationService.initialize_system_roles()` exactly — `get_or_create` per role,
    idempotent (an existing role's `permissions` are NOT reset by a second call)."""
    system_roles = [
        {
            "code": "owner",
            "name": "Owner",
            "description": "Organization owner with full access",
            "is_system": True,
            "permissions": ["org.*"],
        },
        {
            "code": "admin",
            "name": "Admin",
            "description": "Administrator with management permissions",
            "is_system": True,
            "permissions": [
                "org.members.invite",
                "org.members.manage",
                "org.members.remove",
                "org.settings.read",
                "org.settings.write",
            ],
        },
        {
            "code": "member",
            "name": "Member",
            "description": "Regular member with basic access",
            "is_system": True,
            "is_default": True,
            "permissions": ["org.read", "org.members.read"],
        },
        {
            "code": "viewer",
            "name": "Viewer",
            "description": "Read-only access",
            "is_system": True,
            "permissions": ["org.read"],
        },
    ]

    created_roles = []
    for role_data in system_roles:
        stmt = select(OrganizationRoleDB).where(OrganizationRoleDB.code == role_data["code"])
        role = (await session.execute(stmt)).scalar_one_or_none()
        if role is None:
            role = OrganizationRoleDB(**role_data)
            session.add(role)
            await session.commit()
            await session.refresh(role)
        created_roles.append(role)

    return created_roles


def serialize_org_role(role: OrganizationRoleDB) -> dict:
    """Matches `OrganizationRoleSerializer` exactly."""
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "is_default": role.is_default,
        "permissions": role.permissions,
        "created_at": role.created_at.isoformat(),
    }


async def list_org_roles_async(session: AsyncSession) -> list[OrganizationRoleDB]:
    """Mirrors `list_org_roles`: every `OrganizationRole` row, globally — not tenant-scoped, no
    pagination, no filtering (`@require_jwt` only, no `X-Org-Slug`/membership needed)."""
    return list((await session.execute(select(OrganizationRoleDB))).scalars().all())
