"""
Application CRUD service for the Reference_Stack (spec z_aud_3, Wave D chunk 2/5, task 10.1) —
mirrors `tenxyte.models.application.AbstractApplication.create_application`/
`regenerate_credentials` exactly (`secrets.token_hex(32)` for both key and raw secret,
bcrypt+base64 hashing via `application_auth.hash_secret` — the same function Wave A's
`ApplicationAuthMiddleware` already verifies against for `X-Access-Key`/`X-Access-Secret` auth, so
an application created here is immediately usable for that, with no separate code path).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.application_auth import hash_secret
from tenxyte.adapters.fastapi.models_sa import ApplicationDB


def serialize_application(app: ApplicationDB) -> dict:
    return {
        "id": app.id,
        "name": app.name,
        "description": app.description,
        "access_key": app.access_key,
        "is_active": app.is_active,
        "allowed_origins": app.allowed_origins,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }


async def get_application_by_id_async(session: AsyncSession, app_id: str) -> ApplicationDB | None:
    return await session.get(ApplicationDB, app_id)


async def create_application_async(
    session: AsyncSession, *, name: str, description: str = "", allowed_origins: list | None = None
) -> tuple[ApplicationDB, str]:
    """Returns `(row, raw_secret)` — the raw secret is shown to the caller exactly once, like
    Django's `create_application` classmethod."""
    raw_secret = secrets.token_hex(32)
    row = ApplicationDB(
        name=name,
        description=description,
        access_key=secrets.token_hex(32),
        access_secret=hash_secret(raw_secret),
        allowed_origins=allowed_origins or [],
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row, raw_secret


async def update_application_async(
    session: AsyncSession,
    app: ApplicationDB,
    *,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
    allowed_origins: list | None = None,
) -> ApplicationDB:
    if name is not None:
        app.name = name
    if description is not None:
        app.description = description
    if is_active is not None:
        app.is_active = is_active
    if allowed_origins is not None:
        app.allowed_origins = allowed_origins
    app.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(app)
    return app


async def toggle_application_active_async(session: AsyncSession, app: ApplicationDB, is_active: bool) -> ApplicationDB:
    app.is_active = is_active
    app.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(app)
    return app


async def delete_application_async(session: AsyncSession, app: ApplicationDB) -> None:
    await session.delete(app)
    await session.commit()


async def regenerate_credentials_async(session: AsyncSession, app: ApplicationDB) -> dict:
    """Mirrors `regenerate_credentials()`: a brand new `access_key` too, not just the secret —
    old credentials are immediately and fully invalidated, matching Django exactly."""
    raw_secret = secrets.token_hex(32)
    app.access_key = secrets.token_hex(32)
    app.access_secret = hash_secret(raw_secret)
    app.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(app)
    return {"access_key": app.access_key, "access_secret": raw_secret}


def _apply_ordering(stmt, ordering: str, allowed: dict, *, default: str):
    fields = [f.strip() for f in (ordering or "").split(",") if f.strip()]
    if not fields:
        fields = [default]
    for field in fields:
        desc = field.startswith("-")
        name = field[1:] if desc else field
        column = allowed.get(name)
        if column is None:
            continue
        stmt = stmt.order_by(column.desc() if desc else column.asc())
    return stmt


async def list_applications_async(
    session: AsyncSession,
    *,
    search: str = "",
    is_active: bool | None = None,
    ordering: str = "name",
    page: int,
    page_size: int,
) -> tuple[list[ApplicationDB], int]:
    stmt = select(ApplicationDB)
    count_stmt = select(func.count(ApplicationDB.id))

    if search:
        like = f"%{search}%"
        clause = or_(ApplicationDB.name.ilike(like), ApplicationDB.description.ilike(like))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if is_active is not None:
        stmt = stmt.where(ApplicationDB.is_active == is_active)
        count_stmt = count_stmt.where(ApplicationDB.is_active == is_active)

    allowed_ordering = {
        "name": ApplicationDB.name,
        "is_active": ApplicationDB.is_active,
        "created_at": ApplicationDB.created_at,
        "updated_at": ApplicationDB.updated_at,
    }
    stmt = _apply_ordering(stmt, ordering, allowed_ordering, default="name")

    total = (await session.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total
