"""
SQLAlchemy 2.0 models for the FastAPI Reference_Stack (spec z_aud_3, Requirement 3.2).

Async-queryable (SQLAlchemy 2.0 table/column definitions are query-mode-agnostic — only
`repositories_async.py`'s use of `AsyncSession` makes access async). Built incrementally: only
the tables the parity waves landed so far actually need exist here — see each table's docstring
for which wave introduced it. This intentionally does not front-load the full Django schema
surface (roles, organizations, agent tokens, ...) before any endpoint needs it.

Security invariants carried over unchanged from the Django/Core reference (Requirement 8.3 — no
duplicated security logic): passwords are bcrypt hashes computed by Core, never touched here;
refresh tokens are stored hashed, never in plaintext.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from tenxyte.ports.repositories import MFAType, UserStatus


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class UserDB(Base):
    """Wave A (Auth de base). Mirrors `tenxyte.ports.repositories.User`."""

    __tablename__ = "tenxyte_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Wave A follow-up (login/phone, z_aud_3 task 5.1) — mirrors
    # tenxyte.models.auth.User's phone_country_code/phone_number, indexed the same way (a
    # composite index for lookup; SQLite has no partial-unique-index support in this dev driver,
    # so uniqueness among phone users is enforced at the application layer, not the schema, same
    # as documented for the Reference_Stack elsewhere).
    phone_country_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    mfa_type: Mapped[MFAType] = mapped_column(Enum(MFAType), default=MFAType.NONE)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    refresh_tokens: Mapped[list[RefreshTokenDB]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_tenxyte_users_phone", "phone_country_code", "phone_number"),)

    def to_port_model(self):
        from tenxyte.ports.repositories import User

        metadata = dict(self.user_metadata or {})
        if self.phone_country_code and self.phone_number:
            metadata.setdefault("phone_country_code", self.phone_country_code)
            metadata.setdefault("phone_number", self.phone_number)

        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            first_name=self.first_name,
            last_name=self.last_name,
            is_active=self.is_active,
            is_superuser=self.is_superuser,
            is_staff=self.is_staff,
            status=self.status,
            mfa_type=self.mfa_type,
            mfa_secret=self.mfa_secret,
            email_verified=self.email_verified,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_login=self.last_login,
            metadata=metadata,
        )


class RefreshTokenDB(Base):
    """
    Wave A (Auth de base). Stores only a SHA-256 hash of the refresh token, mirroring the
    Django_Adapter's invariant — the raw token is never persisted.
    """

    __tablename__ = "tenxyte_refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[UserDB] = relationship(back_populates="refresh_tokens")


class ApplicationDB(Base):
    """
    Application-level credentials (spec z_aud_3, Requirement 3.4) — mirrors
    `tenxyte.models.application.AbstractApplication`'s essential fields. `access_secret` stores
    the same bcrypt-hashed, base64-encoded format (see `application_auth.hash_secret`), never
    the raw secret.
    """

    __tablename__ = "tenxyte_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100))
    access_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    access_secret: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_origins: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
