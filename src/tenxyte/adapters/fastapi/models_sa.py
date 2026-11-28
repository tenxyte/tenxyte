"""
SQLAlchemy 2.0 models for the FastAPI Reference_Stack (spec z_aud_3, Requirement 3.2).

Schema parity with the Django models (`tenxyte.models.*`):
- Every table name, column name, M2M join table, and foreign key matches the canonical Django
  schema (`tenxyte_*`), so a deployment can switch between Django and FastAPI on the exact same
  database (SQLite, PostgreSQL, or MySQL) without migrating or losing users, sessions, roles,
  organizations, 2FA, passkeys, or AIRS tokens.
- `DjangoUUID` stores UUIDs as 32-char lowercase hex (`CHAR(32)`) on SQLite/MySQL and native
  `UUID` on PostgreSQL, while exposing canonical hyphenated UUID strings in Python — identical to
  Django's `models.UUIDField`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from tenxyte.ports.repositories import MFAType, UserStatus


def generate_uuid() -> str:
    return str(uuid.uuid4())


class DjangoUUID(TypeDecorator):
    """Cross-database UUID column matching Django's `models.UUIDField` storage format.

    - PostgreSQL: native `UUID` column (returns hyphenated string via `as_uuid=False`).
    - SQLite / MySQL / other: `CHAR(32)` storing 32-char lowercase hex without hyphens.
    - Python side: always returns canonical hyphenated UUID strings (`str(uuid.UUID(...))`),
      falling back gracefully for synthetic non-UUID test IDs (e.g. `"u1"`).
    """

    impl = CHAR(32)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value) if dialect.name == "postgresql" else value.hex
        s = str(value)
        try:
            u = uuid.UUID(s)
        except ValueError:
            return s
        return str(u) if dialect.name == "postgresql" else u.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        s = str(value)
        try:
            return str(uuid.UUID(s))
        except ValueError:
            return s


class Base(DeclarativeBase):
    pass


# =============================================================================
# Many-to-Many association tables (exact Django M2M table & column names)
# =============================================================================

role_permissions_table = Table(
    "tenxyte_roles_permissions",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("role_id", DjangoUUID, ForeignKey("tenxyte_roles.id", ondelete="CASCADE"), nullable=False),
    Column("permission_id", DjangoUUID, ForeignKey("tenxyte_permissions.id", ondelete="CASCADE"), nullable=False),
    UniqueConstraint("role_id", "permission_id", name="uq_tenxyte_roles_permissions"),
)

user_roles_table = Table(
    "tenxyte_users_roles",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), nullable=False),
    Column("role_id", DjangoUUID, ForeignKey("tenxyte_roles.id", ondelete="CASCADE"), nullable=False),
    UniqueConstraint("user_id", "role_id", name="uq_tenxyte_users_roles"),
)

user_direct_permissions_table = Table(
    "tenxyte_users_direct_permissions",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), nullable=False),
    Column("permission_id", DjangoUUID, ForeignKey("tenxyte_permissions.id", ondelete="CASCADE"), nullable=False),
    UniqueConstraint("user_id", "permission_id", name="uq_tenxyte_users_direct_permissions"),
)

agent_token_granted_permissions_table = Table(
    "tenxyte_agent_tokens_granted_permissions",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("agenttoken_id", DjangoUUID, ForeignKey("tenxyte_agent_tokens.id", ondelete="CASCADE"), nullable=False),
    Column("permission_id", DjangoUUID, ForeignKey("tenxyte_permissions.id", ondelete="CASCADE"), nullable=False),
    UniqueConstraint("agenttoken_id", "permission_id", name="uq_tenxyte_agent_tokens_granted_permissions"),
)


# =============================================================================
# Core Auth & RBAC Models
# =============================================================================


class UserDB(Base):
    """Mirrors `tenxyte.models.auth.User` (`tenxyte_users`) column-for-column."""

    __tablename__ = "tenxyte_users"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)

    # Identifiers
    email: Mapped[str | None] = mapped_column(String(191), unique=True, index=True, nullable=True)
    phone_country_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Security (SQL column is `password`, matching Django AbstractUser.password)
    password_hash: Mapped[str] = mapped_column("password", String(128), nullable=False, default="")

    # Profile
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    username: Mapped[str | None] = mapped_column(String(191), unique=True, index=True, nullable=True)
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    timezone: Mapped[str] = mapped_column(String(63), nullable=False, default="")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    user_metadata: Mapped[dict | None] = mapped_column("custom_fields", JSON, nullable=True, default=None)

    # OAuth
    google_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)

    # Verification (SQL columns `is_email_verified`, `is_phone_verified`)
    email_verified: Mapped[bool] = mapped_column("is_email_verified", Boolean, nullable=False, default=False)
    phone_verified: Mapped[bool] = mapped_column("is_phone_verified", Boolean, nullable=False, default=False)

    # Passwordless & force password change
    has_usable_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 2FA / TOTP (SQL columns `totp_secret`, `is_2fa_enabled`, `backup_codes`)
    mfa_secret: Mapped[str | None] = mapped_column("totp_secret", String(255), nullable=True)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    backup_codes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Account state
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lockout_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Soft delete & GDPR
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    anonymization_token: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    is_restricted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Admin flags
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Session limits
    max_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_devices: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    refresh_tokens: Mapped[list[RefreshTokenDB]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_tenxyte_users_phone", "phone_country_code", "phone_number"),)

    @property
    def mfa_type(self) -> MFAType:
        return MFAType.TOTP if self.is_2fa_enabled else MFAType.NONE

    @mfa_type.setter
    def mfa_type(self, value: MFAType | str) -> None:
        if isinstance(value, MFAType):
            self.is_2fa_enabled = value != MFAType.NONE
        else:
            self.is_2fa_enabled = str(value).lower() not in ("", "none", "false")

    @property
    def status(self) -> UserStatus:
        if self.is_banned or self.is_deleted or self.is_locked:
            return UserStatus.SUSPENDED
        if not self.is_active:
            return UserStatus.INACTIVE
        return UserStatus.ACTIVE

    @status.setter
    def status(self, value: UserStatus | str) -> None:
        resolved = value if isinstance(value, UserStatus) else UserStatus(str(value))
        if resolved == UserStatus.SUSPENDED:
            self.is_banned = True
        elif resolved in (UserStatus.INACTIVE, UserStatus.PENDING):
            self.is_active = False
        elif resolved == UserStatus.ACTIVE:
            self.is_banned = False
            self.is_locked = False

    def to_port_model(self):
        from tenxyte.ports.repositories import User

        metadata = dict(self.user_metadata or {})
        if self.phone_country_code and self.phone_number:
            metadata.setdefault("phone_country_code", self.phone_country_code)
            metadata.setdefault("phone_number", self.phone_number)
        if self.backup_codes:
            metadata.setdefault("backup_codes", self.backup_codes)

        return User(
            id=self.id,
            email=self.email or "",
            password_hash=self.password_hash or None,
            first_name=self.first_name,
            last_name=self.last_name,
            is_active=self.is_active,
            is_superuser=self.is_superuser,
            is_staff=self.is_staff,
            status=self.status,
            mfa_type=self.mfa_type,
            mfa_secret=self.mfa_secret,
            email_verified=self.email_verified,
            phone_verified=self.phone_verified,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_login=self.last_login,
            metadata=metadata,
        )


class PermissionDB(Base):
    """Mirrors `tenxyte.models.auth.Permission` (`tenxyte_permissions`)."""

    __tablename__ = "tenxyte_permissions"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parent_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_permissions.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class RoleDB(Base):
    """Mirrors `tenxyte.models.auth.Role` (`tenxyte_roles`)."""

    __tablename__ = "tenxyte_roles"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# =============================================================================
# Applications & Operational Models
# =============================================================================


class ApplicationDB(Base):
    """Mirrors `tenxyte.models.application.Application` (`tenxyte_applications`)."""

    __tablename__ = "tenxyte_applications"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    access_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    access_secret: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_origins: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    redirect_uris: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class RefreshTokenDB(Base):
    """Mirrors `tenxyte.models.operational.RefreshToken` (`tenxyte_refresh_tokens`)."""

    __tablename__ = "tenxyte_refresh_tokens"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    application_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_applications.id", ondelete="CASCADE"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column("token", String(191), unique=True, index=True, nullable=False)
    device_info: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ip_address: Mapped[str | None] = mapped_column(String(39), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[UserDB] = relationship(back_populates="refresh_tokens")


class OTPCodeDB(Base):
    """Mirrors `tenxyte.models.operational.OTPCode` (`tenxyte_otp_codes`)."""

    __tablename__ = "tenxyte_otp_codes"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code_hash: Mapped[str] = mapped_column("code", String(64), nullable=False)
    otp_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("ix_tenxyte_otp_codes_lookup", "user_id", "otp_type", "is_used", "created_at"),)


class MagicLinkTokenDB(Base):
    """Mirrors `tenxyte.models.magic_link.MagicLinkToken` (`tenxyte_magic_link_tokens`)."""

    __tablename__ = "tenxyte_magic_link_tokens"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    application_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_applications.id", ondelete="CASCADE"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column("token", String(191), unique=True, index=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(39), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# =============================================================================
# AIRS (AI Agent Tokens & HITL)
# =============================================================================


class AgentTokenDB(Base):
    """Mirrors `tenxyte.models.agent.AgentToken` (`tenxyte_agent_tokens`)."""

    __tablename__ = "tenxyte_agent_tokens"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    token_hash: Mapped[str] = mapped_column("token", String(128), unique=True, index=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    triggered_by_user_id: Mapped[str] = mapped_column(
        "triggered_by_id", DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    application_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_applications.id", ondelete="CASCADE"), nullable=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_organizations.id", ondelete="SET NULL"), nullable=True
    )

    # -- Lifecycle (AIRS/1.0 §3) --
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by_user_id: Mapped[str | None] = mapped_column(
        "revoked_by_id", DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    suspended_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # -- Circuit breaker (AIRS/1.0 §6.1) --
    max_requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_requests_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    current_request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_failed_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    current_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # -- Dead man's switch (AIRS/1.0 §6.2) --
    heartbeat_required_every: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # -- Budget (AIRS/1.0 §6.3) --
    budget_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    current_spend_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)

    # -- Audit --
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    granted_permission_rows: Mapped[list[PermissionDB]] = relationship(
        "PermissionDB",
        secondary=agent_token_granted_permissions_table,
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_tenxyte_agent_tokens_status_expires", "status", "expires_at"),
        Index("ix_tenxyte_agent_tokens_user_status", "triggered_by_id", "status"),
    )

    @property
    def granted_permissions(self) -> list[str]:
        return [p.code for p in self.granted_permission_rows]


class AgentPendingActionDB(Base):
    """Mirrors `tenxyte.models.agent.AgentPendingAction` (`tenxyte_agent_pending_actions`)."""

    __tablename__ = "tenxyte_agent_pending_actions"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    agent_token_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_agent_tokens.id", ondelete="CASCADE"), index=True, nullable=False
    )
    permission_requested: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confirmation_token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    denied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    prompt_trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


# =============================================================================
# Security & Audit Models
# =============================================================================


class BlacklistedTokenDB(Base):
    """Mirrors `tenxyte.models.security.BlacklistedToken` (`tenxyte_blacklisted_tokens`)."""

    __tablename__ = "tenxyte_blacklisted_tokens"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    token_jti: Mapped[str] = mapped_column(String(191), unique=True, index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), nullable=True
    )
    blacklisted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False, default="")


class AuditLogDB(Base):
    """Mirrors `tenxyte.models.security.AuditLog` (`tenxyte_audit_logs`), including AIRS context."""

    __tablename__ = "tenxyte_audit_logs"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
    agent_token_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_agent_tokens.id", ondelete="SET NULL"), nullable=True
    )
    on_behalf_of_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
    prompt_trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(39), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    application_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_applications.id", ondelete="SET NULL"), nullable=True
    )
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class PasswordHistoryDB(Base):
    """Mirrors `tenxyte.models.security.PasswordHistory` (`tenxyte_password_history`)."""

    __tablename__ = "tenxyte_password_history"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class LoginAttemptDB(Base):
    """Mirrors `tenxyte.models.operational.LoginAttempt` (`tenxyte_login_attempts`)."""

    __tablename__ = "tenxyte_login_attempts"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    identifier: Mapped[str] = mapped_column(String(191), index=True, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(39), nullable=False)
    application_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_applications.id", ondelete="CASCADE"), nullable=True
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failure_reason: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# =============================================================================
# Organizations (Multi-Tenancy)
# =============================================================================


class OrganizationDB(Base):
    """Mirrors `tenxyte.models.organization.Organization` (`tenxyte_organizations`)."""

    __tablename__ = "tenxyte_organizations"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parent_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_organizations.id", ondelete="CASCADE"), nullable=True
    )
    org_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_members: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (Index("ix_tenxyte_organizations_parent_active", "parent_id", "is_active"),)


class OrganizationRoleDB(Base):
    """Mirrors `tenxyte.models.organization.OrganizationRole` (`tenxyte_organization_roles`)."""

    __tablename__ = "tenxyte_organization_roles"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class OrganizationMembershipDB(Base):
    """Mirrors `tenxyte.models.organization.OrganizationMembership` (`tenxyte_organization_memberships`)."""

    __tablename__ = "tenxyte_organization_memberships"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_organization_roles.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    invited_by_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
    invited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_tenxyte_org_membership_user_org"),
        Index("ix_tenxyte_org_membership_org_status", "organization_id", "status"),
    )


class OrganizationInvitationDB(Base):
    """Mirrors `tenxyte.models.organization.OrganizationInvitation` (`tenxyte_organization_invitations`)."""

    __tablename__ = "tenxyte_organization_invitations"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(191), nullable=False)
    role_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_organization_roles.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    invited_by_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_tenxyte_org_invitations_org_status", "organization_id", "status"),)


# =============================================================================
# WebAuthn, Social, and GDPR Models
# =============================================================================


class WebAuthnCredentialDB(Base):
    """Mirrors `tenxyte.models.webauthn.WebAuthnCredential` (`tenxyte_webauthn_credentials`)."""

    __tablename__ = "tenxyte_webauthn_credentials"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    credential_id: Mapped[str] = mapped_column(String(191), unique=True, index=True, nullable=False)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    aaguid: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    transports: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WebAuthnChallengeDB(Base):
    """Mirrors `tenxyte.models.webauthn.WebAuthnChallenge` (`tenxyte_webauthn_challenges`)."""

    __tablename__ = "tenxyte_webauthn_challenges"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), nullable=True
    )
    challenge: Mapped[str] = mapped_column(String(191), unique=True, index=True, nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SocialConnectionDB(Base):
    """Mirrors `tenxyte.models.social.SocialConnection` (`tenxyte_social_connections`)."""

    __tablename__ = "tenxyte_social_connections"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(191), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(191), nullable=False, default="")
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # Always empty per R10 security audit, retained for exact schema parity with Django.
    access_token: Mapped[str] = mapped_column(Text, nullable=False, default="")
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_tenxyte_social_connection_provider_user"),
    )


class AccountDeletionRequestDB(Base):
    """Mirrors `tenxyte.models.gdpr.AccountDeletionRequest` (`tenxyte_account_deletion_requests`)."""

    __tablename__ = "tenxyte_account_deletion_requests"

    id: Mapped[str] = mapped_column(DjangoUUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    confirmation_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(39), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    admin_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    processed_by_id: Mapped[str | None] = mapped_column(
        DjangoUUID, ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
