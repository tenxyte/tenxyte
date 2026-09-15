"""
Framework-agnostic-in-spirit RBAC service for the Reference_Stack (spec z_aud_3, Wave D, task
10.1) — a from-scratch equivalent of the permission/role logic on Django's
`tenxyte.models.auth.User`/`AbstractRole`/`AbstractPermission` (`has_permission`,
`_get_effective_permission_codes`, `assign_role`, `remove_role`, `get_all_roles`,
`get_all_permissions`). Like `otp_service.py`/`airs_service.py`, Django has never extracted RBAC
to Core — this is a new implementation verified against the real model methods in
`models/auth.py`, not a port of existing Core code.

**Hierarchy**: holding a permission implicitly grants every one of its descendants (and,
equivalently, a permission is held if the caller holds it directly OR holds any of its
ancestors) — see `has_permission_async` and `effective_permission_codes_async`, which replicate
`User.has_permission()`/`_get_effective_permission_codes()` exactly, including the superuser and
`super_admin`-role bypasses `has_permission()` checks first.

Association tables (`role_permissions_table`, `user_roles_table`,
`user_direct_permissions_table` — see `models_sa.py`) are queried directly with explicit
`select()`/`insert()`/`delete()` statements rather than through ORM `relationship(secondary=...)`
collections, consistent with the rest of this adapter's async-first style.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import (
    PermissionDB,
    RoleDB,
    role_permissions_table,
    user_direct_permissions_table,
    user_roles_table,
)
from tenxyte.adapters.fastapi.pagination import apply_ordering
from tenxyte.ports.repositories import User

SUPER_ADMIN_ROLE_CODE = "super_admin"


# ============================================================
# Serialization — matches PermissionSerializer/RoleSerializer/RoleListSerializer exactly.
# ============================================================


async def serialize_permission_async(session: AsyncSession, permission: PermissionDB) -> dict:
    parent = None
    if permission.parent_id:
        parent_row = await session.get(PermissionDB, permission.parent_id)
        if parent_row:
            parent = {"id": parent_row.id, "code": parent_row.code}

    children_stmt = select(PermissionDB).where(PermissionDB.parent_id == permission.id)
    children_rows = (await session.execute(children_stmt)).scalars().all()
    children = [{"id": c.id, "code": c.code, "name": c.name} for c in children_rows]

    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "description": permission.description,
        "parent": parent,
        "children": children,
        "created_at": permission.created_at.isoformat(),
        "updated_at": permission.updated_at.isoformat(),
    }


async def get_role_permissions_async(session: AsyncSession, role_id: str) -> list[PermissionDB]:
    stmt = (
        select(PermissionDB)
        .join(role_permissions_table, role_permissions_table.c.permission_id == PermissionDB.id)
        .where(role_permissions_table.c.role_id == role_id)
        .order_by(PermissionDB.code)
    )
    return list((await session.execute(stmt)).scalars().all())


async def serialize_role_async(session: AsyncSession, role: RoleDB) -> dict:
    permissions = await get_role_permissions_async(session, role.id)
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "permissions": [await serialize_permission_async(session, p) for p in permissions],
        "permission_codes": [p.code for p in permissions],
        "is_default": role.is_default,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
    }


def serialize_role_list_item(role: RoleDB) -> dict:
    return {"id": role.id, "code": role.code, "name": role.name, "is_default": role.is_default}


# ============================================================
# Permission CRUD
# ============================================================


async def get_permission_by_id_async(session: AsyncSession, permission_id: str) -> PermissionDB | None:
    return await session.get(PermissionDB, permission_id)


async def get_permission_by_code_async(session: AsyncSession, code: str) -> PermissionDB | None:
    stmt = select(PermissionDB).where(PermissionDB.code == code)
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_permission_async(
    session: AsyncSession, *, code: str, name: str, description: str = "", parent_code: str | None = None
) -> tuple[PermissionDB | None, str | None]:
    """Returns `(row, error)` — `error` is `"PARENT_NOT_FOUND"` when `parent_code` doesn't
    resolve, matching `PermissionSerializer.create`'s validation error."""
    parent_id = None
    if parent_code:
        parent = await get_permission_by_code_async(session, parent_code)
        if parent is None:
            return None, "PARENT_NOT_FOUND"
        parent_id = parent.id

    row = PermissionDB(code=code, name=name, description=description, parent_id=parent_id)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row, None


async def update_permission_async(
    session: AsyncSession,
    permission: PermissionDB,
    *,
    name: str | None = None,
    description: str | None = None,
    parent_code: str | None = "__unset__",
) -> tuple[PermissionDB | None, str | None]:
    if name is not None:
        permission.name = name
    if description is not None:
        permission.description = description
    if parent_code != "__unset__":
        if parent_code:
            parent = await get_permission_by_code_async(session, parent_code)
            if parent is None:
                return None, "PARENT_NOT_FOUND"
            permission.parent_id = parent.id
        else:
            permission.parent_id = None
    permission.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(permission)
    return permission, None


async def delete_permission_async(session: AsyncSession, permission: PermissionDB) -> None:
    await session.delete(permission)
    await session.commit()


async def list_permissions_async(
    session: AsyncSession,
    *,
    search: str = "",
    parent: str | None = None,
    ordering: str = "code",
    page: int,
    page_size: int,
) -> tuple[list[PermissionDB], int]:
    stmt = select(PermissionDB)
    count_stmt = select(func.count(PermissionDB.id))

    if search:
        like = f"%{search}%"
        clause = or_(PermissionDB.code.ilike(like), PermissionDB.name.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if parent is not None:
        if parent.lower() == "null" or parent == "":
            stmt = stmt.where(PermissionDB.parent_id.is_(None))
            count_stmt = count_stmt.where(PermissionDB.parent_id.is_(None))
        else:
            stmt = stmt.where(PermissionDB.parent_id == parent)
            count_stmt = count_stmt.where(PermissionDB.parent_id == parent)

    allowed_ordering = {"code": PermissionDB.code, "name": PermissionDB.name, "created_at": PermissionDB.created_at}
    stmt = apply_ordering(stmt, ordering, allowed_ordering, default="code")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


# ============================================================
# Role CRUD
# ============================================================


async def get_role_by_id_async(session: AsyncSession, role_id: str) -> RoleDB | None:
    return await session.get(RoleDB, role_id)


async def get_role_by_code_async(session: AsyncSession, code: str) -> RoleDB | None:
    stmt = select(RoleDB).where(RoleDB.code == code)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _set_role_permissions_async(session: AsyncSession, role_id: str, permission_codes: list[str]) -> None:
    await session.execute(delete(role_permissions_table).where(role_permissions_table.c.role_id == role_id))
    if permission_codes:
        stmt = select(PermissionDB).where(PermissionDB.code.in_(permission_codes))
        permissions = (await session.execute(stmt)).scalars().all()
        if permissions:
            await session.execute(
                insert(role_permissions_table),
                [{"role_id": role_id, "permission_id": p.id} for p in permissions],
            )
    await session.commit()


async def create_role_async(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    description: str = "",
    is_default: bool = False,
    permission_codes: list[str] | None = None,
) -> RoleDB:
    row = RoleDB(code=code, name=name, description=description, is_default=is_default)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    if permission_codes:
        await _set_role_permissions_async(session, row.id, permission_codes)
        await session.refresh(row)
    return row


async def update_role_async(
    session: AsyncSession,
    role: RoleDB,
    *,
    name: str | None = None,
    description: str | None = None,
    is_default: bool | None = None,
    permission_codes: list[str] | None = None,
) -> RoleDB:
    if name is not None:
        role.name = name
    if description is not None:
        role.description = description
    if is_default is not None:
        role.is_default = is_default
    role.updated_at = datetime.now(timezone.utc)
    await session.commit()
    if permission_codes is not None:
        await _set_role_permissions_async(session, role.id, permission_codes)
    await session.refresh(role)
    return role


async def delete_role_async(session: AsyncSession, role: RoleDB) -> None:
    await session.delete(role)
    await session.commit()


async def list_roles_async(
    session: AsyncSession,
    *,
    search: str = "",
    is_default: bool | None = None,
    ordering: str = "name",
    page: int,
    page_size: int,
) -> tuple[list[RoleDB], int]:
    stmt = select(RoleDB)
    count_stmt = select(func.count(RoleDB.id))

    if search:
        like = f"%{search}%"
        clause = or_(RoleDB.code.ilike(like), RoleDB.name.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if is_default is not None:
        stmt = stmt.where(RoleDB.is_default == is_default)
        count_stmt = count_stmt.where(RoleDB.is_default == is_default)

    allowed_ordering = {
        "code": RoleDB.code,
        "name": RoleDB.name,
        "is_default": RoleDB.is_default,
        "created_at": RoleDB.created_at,
    }
    stmt = apply_ordering(stmt, ordering, allowed_ordering, default="name")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


async def add_role_permissions_async(session: AsyncSession, role: RoleDB, permission_codes: list[str]) -> dict:
    """Mirrors `RolePermissionsView.post` exactly: validates every code exists first (all-or-
    nothing), then adds only the ones not already assigned."""
    stmt = select(PermissionDB).where(PermissionDB.code.in_(permission_codes))
    found = (await session.execute(stmt)).scalars().all()
    found_codes = {p.code for p in found}
    not_found = set(permission_codes) - found_codes
    if not_found:
        return {"error": "not_found", "not_found": sorted(not_found)}

    existing_stmt = (
        select(PermissionDB.code)
        .join(role_permissions_table, role_permissions_table.c.permission_id == PermissionDB.id)
        .where(role_permissions_table.c.role_id == role.id, PermissionDB.code.in_(permission_codes))
    )
    existing_codes = set((await session.execute(existing_stmt)).scalars().all())

    new_permissions = [p for p in found if p.code not in existing_codes]
    if new_permissions:
        await session.execute(
            insert(role_permissions_table), [{"role_id": role.id, "permission_id": p.id} for p in new_permissions]
        )
        await session.commit()

    return {
        "added": [p.code for p in new_permissions],
        "already_assigned": sorted(existing_codes),
    }


async def remove_role_permissions_async(session: AsyncSession, role: RoleDB, permission_codes: list[str]) -> dict:
    stmt = select(PermissionDB).where(PermissionDB.code.in_(permission_codes))
    found = (await session.execute(stmt)).scalars().all()
    found_codes = {p.code for p in found}
    not_found = set(permission_codes) - found_codes
    if not_found:
        return {"error": "not_found", "not_found": sorted(not_found)}

    assigned_stmt = (
        select(PermissionDB.code)
        .join(role_permissions_table, role_permissions_table.c.permission_id == PermissionDB.id)
        .where(role_permissions_table.c.role_id == role.id, PermissionDB.code.in_(permission_codes))
    )
    assigned_codes = set((await session.execute(assigned_stmt)).scalars().all())

    to_remove = [p for p in found if p.code in assigned_codes]
    not_removed = [p.code for p in found if p.code not in assigned_codes]
    if to_remove:
        await session.execute(
            delete(role_permissions_table).where(
                role_permissions_table.c.role_id == role.id,
                role_permissions_table.c.permission_id.in_([p.id for p in to_remove]),
            )
        )
        await session.commit()

    return {"removed": [p.code for p in to_remove], "not_removed": not_removed}


# ============================================================
# User <-> Role / User <-> direct Permission assignment
# ============================================================


async def get_user_roles_async(session: AsyncSession, user_id: str) -> list[RoleDB]:
    stmt = (
        select(RoleDB)
        .join(user_roles_table, user_roles_table.c.role_id == RoleDB.id)
        .where(user_roles_table.c.user_id == user_id)
        .order_by(RoleDB.name)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_all_role_codes_async(session: AsyncSession, user_id: str) -> list[str]:
    """Mirrors `User.get_all_roles()`."""
    return [r.code for r in await get_user_roles_async(session, user_id)]


async def assign_role_async(session: AsyncSession, user_id: str, role_code: str) -> bool:
    """Mirrors `User.assign_role()` — `False` if `role_code` doesn't exist. Idempotent: assigning
    an already-held role is a silent no-op (same as Django's `ManyToManyField.add()`)."""
    role = await get_role_by_code_async(session, role_code)
    if role is None:
        return False
    exists_stmt = select(user_roles_table).where(
        user_roles_table.c.user_id == user_id, user_roles_table.c.role_id == role.id
    )
    already = (await session.execute(exists_stmt)).first()
    if not already:
        await session.execute(insert(user_roles_table).values(user_id=user_id, role_id=role.id))
        await session.commit()
    return True


async def remove_role_async(session: AsyncSession, user_id: str, role_code: str) -> bool:
    """Mirrors `User.remove_role()` — `False` if `role_code` doesn't exist (note: this matches
    Django exactly, including that removing a role the user never had still returns `True`, since
    Django's `ManyToManyField.remove()` on a non-member is a silent no-op, not an error)."""
    role = await get_role_by_code_async(session, role_code)
    if role is None:
        return False
    await session.execute(
        delete(user_roles_table).where(user_roles_table.c.user_id == user_id, user_roles_table.c.role_id == role.id)
    )
    await session.commit()
    return True


async def get_user_direct_permissions_async(session: AsyncSession, user_id: str) -> list[PermissionDB]:
    stmt = (
        select(PermissionDB)
        .join(user_direct_permissions_table, user_direct_permissions_table.c.permission_id == PermissionDB.id)
        .where(user_direct_permissions_table.c.user_id == user_id)
        .order_by(PermissionDB.code)
    )
    return list((await session.execute(stmt)).scalars().all())


async def add_user_direct_permissions_async(session: AsyncSession, user_id: str, permission_codes: list[str]) -> dict:
    stmt = select(PermissionDB).where(PermissionDB.code.in_(permission_codes))
    found = (await session.execute(stmt)).scalars().all()
    found_codes = {p.code for p in found}
    not_found = set(permission_codes) - found_codes
    if not_found:
        return {"error": "not_found", "not_found": sorted(not_found)}

    existing_stmt = (
        select(PermissionDB.code)
        .join(user_direct_permissions_table, user_direct_permissions_table.c.permission_id == PermissionDB.id)
        .where(user_direct_permissions_table.c.user_id == user_id, PermissionDB.code.in_(permission_codes))
    )
    existing_codes = set((await session.execute(existing_stmt)).scalars().all())

    new_permissions = [p for p in found if p.code not in existing_codes]
    if new_permissions:
        await session.execute(
            insert(user_direct_permissions_table),
            [{"user_id": user_id, "permission_id": p.id} for p in new_permissions],
        )
        await session.commit()

    return {"added": [p.code for p in new_permissions], "already_assigned": sorted(existing_codes)}


async def remove_user_direct_permissions_async(
    session: AsyncSession, user_id: str, permission_codes: list[str]
) -> dict:
    stmt = select(PermissionDB).where(PermissionDB.code.in_(permission_codes))
    found = (await session.execute(stmt)).scalars().all()
    found_codes = {p.code for p in found}
    not_found = set(permission_codes) - found_codes
    if not_found:
        return {"error": "not_found", "not_found": sorted(not_found)}

    assigned_stmt = (
        select(PermissionDB.code)
        .join(user_direct_permissions_table, user_direct_permissions_table.c.permission_id == PermissionDB.id)
        .where(user_direct_permissions_table.c.user_id == user_id, PermissionDB.code.in_(permission_codes))
    )
    assigned_codes = set((await session.execute(assigned_stmt)).scalars().all())

    to_remove = [p for p in found if p.code in assigned_codes]
    not_removed = [p.code for p in found if p.code not in assigned_codes]
    if to_remove:
        await session.execute(
            delete(user_direct_permissions_table).where(
                user_direct_permissions_table.c.user_id == user_id,
                user_direct_permissions_table.c.permission_id.in_([p.id for p in to_remove]),
            )
        )
        await session.commit()

    return {"removed": [p.code for p in to_remove], "not_removed": not_removed}


# ============================================================
# Effective-permission resolution — mirrors `User.has_permission`/`_get_effective_permission_codes`.
# ============================================================


async def _user_holds_permission_code_async(session: AsyncSession, user_id: str, code: str) -> bool:
    stmt = select(PermissionDB.id).where(
        PermissionDB.code == code,
        or_(
            PermissionDB.id.in_(
                select(role_permissions_table.c.permission_id)
                .join(user_roles_table, user_roles_table.c.role_id == role_permissions_table.c.role_id)
                .where(user_roles_table.c.user_id == user_id)
            ),
            PermissionDB.id.in_(
                select(user_direct_permissions_table.c.permission_id).where(
                    user_direct_permissions_table.c.user_id == user_id
                )
            ),
        ),
    )
    return (await session.execute(stmt)).first() is not None


async def _ancestor_codes_async(session: AsyncSession, permission: PermissionDB) -> list[str]:
    codes = []
    current = permission
    while current.parent_id:
        parent = await session.get(PermissionDB, current.parent_id)
        if parent is None:
            break
        codes.append(parent.code)
        current = parent
    return codes


async def _descendant_codes_async(session: AsyncSession, permission_id: str) -> set[str]:
    codes: set[str] = set()
    stmt = select(PermissionDB).where(PermissionDB.parent_id == permission_id)
    children = (await session.execute(stmt)).scalars().all()
    for child in children:
        codes.add(child.code)
        codes |= await _descendant_codes_async(session, child.id)
    return codes


async def has_permission_async(session: AsyncSession, user: User, permission_code: str) -> bool:
    """Mirrors `User.has_permission()` exactly: superuser bypass, `super_admin` role bypass,
    direct match (role or direct grant), then a hierarchical ancestor check."""
    if user.is_superuser:
        return True

    super_admin = await get_role_by_code_async(session, SUPER_ADMIN_ROLE_CODE)
    if super_admin is not None:
        stmt = select(user_roles_table).where(
            user_roles_table.c.user_id == user.id, user_roles_table.c.role_id == super_admin.id
        )
        if (await session.execute(stmt)).first() is not None:
            return True

    if await _user_holds_permission_code_async(session, user.id, permission_code):
        return True

    permission = await get_permission_by_code_async(session, permission_code)
    if permission is None:
        return False

    for ancestor_code in await _ancestor_codes_async(session, permission):
        if await _user_holds_permission_code_async(session, user.id, ancestor_code):
            return True

    return False


async def effective_permission_codes_async(session: AsyncSession, user_id: str) -> list[str]:
    """Mirrors `User.get_all_permissions()`/`_get_effective_permission_codes()`: role permissions
    + direct permissions, expanded to include every descendant of each held permission."""
    stmt = select(PermissionDB).where(
        or_(
            PermissionDB.id.in_(
                select(role_permissions_table.c.permission_id)
                .join(user_roles_table, user_roles_table.c.role_id == role_permissions_table.c.role_id)
                .where(user_roles_table.c.user_id == user_id)
            ),
            PermissionDB.id.in_(
                select(user_direct_permissions_table.c.permission_id).where(
                    user_direct_permissions_table.c.user_id == user_id
                )
            ),
        )
    )
    base = (await session.execute(stmt)).scalars().all()
    codes = {p.code for p in base}
    for p in base:
        codes |= await _descendant_codes_async(session, p.id)
    return sorted(codes)
