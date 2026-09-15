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
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
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
    # Wave C follow-up (z_aud_3 task 7.1) — mirrors tenxyte.models.auth.User.is_phone_verified.
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Wave D chunk 3 follow-up (z_aud_3 task 10.1) — mirrors tenxyte.models.auth.User's
    # ban/lock/soft-delete/session-limit fields, added only now since no earlier wave needed them.
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lockout_count: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    anonymization_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    max_sessions: Mapped[int] = mapped_column(Integer, default=1)
    max_devices: Mapped[int] = mapped_column(Integer, default=1)

    # Wave C (z_aud_3 task 7.1) — bcrypt-hashed 2FA backup codes (never the plaintext codes,
    # shown to the caller once at generation time and never persisted), mirroring
    # tenxyte.models.auth.User.backup_codes.
    backup_codes: Mapped[list] = mapped_column(JSON, default=list)

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
        if self.backup_codes:
            metadata.setdefault("backup_codes", self.backup_codes)

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
            phone_verified=self.phone_verified,
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

    # Wave D chunk 4 follow-up (z_aud_3 task 10.1) — mirrors tenxyte.models.operational.
    # RefreshToken's admin-visible fields (application/device_info/ip_address/last_used_at),
    # added only now since no earlier wave's contract needed them. `device_id` (above) is a
    # distinct, earlier (Wave A) concept — a caller-supplied device identifier used for lookup,
    # not the free-text description `device_info` mirrors.
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_applications.id", ondelete="SET NULL"), nullable=True
    )
    device_info: Mapped[str] = mapped_column(String(255), default="")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    # Wave D follow-up (z_aud_3 task 10.1) — mirrors AbstractApplication.description, missing
    # from Wave A's original columns (which only needed access-credential fields for
    # X-Access-Key/X-Access-Secret auth, not the full CRUD surface applications/* exposes).
    description: Mapped[str] = mapped_column(Text, default="")
    access_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    access_secret: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_origins: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OTPCodeDB(Base):
    """
    Wave C (z_aud_3 task 7.1) — one-time codes for email/phone verification, password reset, and
    passwordless login. Mirrors `tenxyte.models.operational.OTPCode` exactly: `code` stores only
    the SHA-256 hex digest of the 6-digit code (the raw code is returned once by
    `otp_service.generate_otp` and never persisted), and `attempts` is only ever incremented via
    an atomic conditional `UPDATE` (see `otp_service.py`'s `_consume_attempt`), never a Python-side
    read-then-write — required to avoid a race where concurrent verify calls each observe a stale
    `attempts` value and collectively exceed `max_attempts`.
    """

    __tablename__ = "tenxyte_otp_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    otp_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=3)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_tenxyte_otp_codes_lookup", "user_id", "otp_type", "is_used", "created_at"),)


class MagicLinkTokenDB(Base):
    """
    Wave C (z_aud_3 task 7.1) — mirrors `tenxyte.models.magic_link.MagicLinkToken`. `token_hash`
    stores only the SHA-256 hash of the opaque token (`secrets.token_urlsafe(32)`, generated by
    `core.magic_link_service.MagicLinkService`), never the raw token — same invariant as
    `RefreshTokenDB`.
    """

    __tablename__ = "tenxyte_magic_link_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentTokenDB(Base):
    """
    Wave F (z_aud_3 task 9.1) — mirrors `tenxyte.models.agent.AgentToken`. `token_hash` stores
    only the SHA-256 hash of the raw 48-character token (`AgentTokenService._generate_token`),
    never the raw value — same invariant as every other bearer credential in the Reference_Stack,
    and required by AIRS/1.0 [AIRS-CORE-12].

    `granted_permissions` is a JSON array of permission-code strings rather than a many-to-many
    relation to a `Permission` table, the way Django's model does it — the Reference_Stack has no
    RBAC/permission tables yet (Group D). This is a genuine simplification, not a full port: see
    `airs_service.py`'s module docstring for how permission validation is scoped down accordingly
    until Group D ships.
    """

    __tablename__ = "tenxyte_agent_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(100))
    triggered_by_user_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True)
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_applications.id", ondelete="SET NULL"), nullable=True
    )
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    granted_permissions: Mapped[list] = mapped_column(JSON, default=list)

    # -- Lifecycle (AIRS/1.0 §3) --
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    suspended_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # -- Circuit breaker (AIRS/1.0 §6.1) --
    max_requests_per_minute: Mapped[int] = mapped_column(default=60)
    max_requests_total: Mapped[int] = mapped_column(default=1000)
    current_request_count: Mapped[int] = mapped_column(default=0)
    max_failed_requests: Mapped[int] = mapped_column(default=10)
    current_failed_count: Mapped[int] = mapped_column(default=0)

    # -- Dead man's switch (AIRS/1.0 §6.2) --
    heartbeat_required_every: Mapped[int | None] = mapped_column(nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # -- Budget (AIRS/1.0 §6.3) --
    budget_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    current_spend_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)

    # -- Audit --
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_tenxyte_agent_tokens_status_expires", "status", "expires_at"),
        Index("ix_tenxyte_agent_tokens_user_status", "triggered_by_user_id", "status"),
    )


class AgentPendingActionDB(Base):
    """
    Wave F (z_aud_3 task 9.1) — mirrors `tenxyte.models.agent.AgentPendingAction`: a HITL
    (Human-In-The-Loop) action awaiting confirmation or denial, per AIRS/1.0 §5.
    """

    __tablename__ = "tenxyte_agent_pending_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    agent_token_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_agent_tokens.id", ondelete="CASCADE"), index=True)
    permission_requested: Mapped[str] = mapped_column(String(100))
    endpoint: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmation_token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    denied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    prompt_trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class AgentActionLogDB(Base):
    """
    Wave F (z_aud_3 task 9.1) — a minimal internal audit trail for successful, state-changing
    Agent Token requests, existing specifically to satisfy AIRS/1.0 [AIRS-TRACE-3]: "a server
    offering the `trace` Conformance Level MUST durably persist the Prompt Trace ID somewhere it
    associates with that action... persistence usable by the implementation's own
    operators/tooling... is sufficient to satisfy this clause; exposing it through a public
    endpoint is enough but not required." No FastAPI route currently reads this table — it is
    intentionally not part of the public wire contract, mirroring the Django_Adapter's own current
    state (Annex A: `prompt_trace_id` is persisted on `AuditLog` but not yet serialized by any
    public admin endpoint either).
    """

    __tablename__ = "tenxyte_agent_action_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    agent_token_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_agent_tokens.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(String(255))
    prompt_trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Wave D (z_aud_3 task 10.1) — plain association `Table`s, not ORM `relationship(secondary=...)`
# collections: every other many-to-many-shaped access in this adapter already goes through
# explicit `select()`/`join()` calls rather than lazy relationship traversal (see
# `routers/airs.py`'s `list_pending_actions`), since SQLAlchemy's async session needs an explicit
# eager-loading strategy for lazy relationships anyway — querying the association tables directly
# in `rbac_service.py` avoids that entirely and stays consistent with the rest of the file.
role_permissions_table = Table(
    "tenxyte_role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("tenxyte_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("tenxyte_permissions.id", ondelete="CASCADE"), primary_key=True),
)

user_roles_table = Table(
    "tenxyte_user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("tenxyte_users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("tenxyte_roles.id", ondelete="CASCADE"), primary_key=True),
)

user_direct_permissions_table = Table(
    "tenxyte_user_direct_permissions",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("tenxyte_users.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("tenxyte_permissions.id", ondelete="CASCADE"), primary_key=True),
)


class PermissionDB(Base):
    """
    Wave D (z_aud_3 task 10.1) — mirrors `tenxyte.models.auth.Permission`. Hierarchical via
    `parent_id`: holding a permission implicitly grants every one of its descendants too (see
    `rbac_service.py`'s `has_permission_async`, which replicates Django's real
    `User.has_permission()` ancestor-walk exactly).
    """

    __tablename__ = "tenxyte_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_permissions.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RoleDB(Base):
    """Wave D (z_aud_3 task 10.1) — mirrors `tenxyte.models.auth.Role`."""

    __tablename__ = "tenxyte_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlacklistedTokenDB(Base):
    """Wave D chunk 4 (z_aud_3 task 10.1) — mirrors `tenxyte.models.security.BlacklistedToken`'s
    admin-visible fields. A separate, persisted record from the actual blacklist-checking path
    (`core.jwt_service.InMemoryTokenBlacklistService`, still in-memory and still what
    `require_jwt()` actually checks against) — this table only exists to give
    `admin/blacklisted-tokens/*` something real to list, written alongside (not instead of) the
    in-memory blacklist at every call site that already blacklists a token (`routers/auth.py`'s
    `logout`/`logout_all`, `routers/twofa.py`'s bootstrap-token blacklist on 2FA confirm) — see
    `admin_security_service.record_blacklisted_token_async`.
    """

    __tablename__ = "tenxyte_blacklisted_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    token_jti: Mapped[str] = mapped_column(String(191), unique=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True)
    blacklisted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(String(100), default="")


class AuditLogDB(Base):
    """Wave D chunk 4 (z_aud_3 task 10.1) — mirrors the subset of `tenxyte.models.security.
    AuditLog`'s fields that `AuditLogSerializer` actually exposes (its AIRS-context columns —
    `agent_token`/`on_behalf_of`/`prompt_trace_id` — aren't in that serializer's output, so
    they're not replicated here). No Reference_Stack auth flow writes to this table yet — unlike
    `BlacklistedTokenDB`, wiring every Wave A-C endpoint to call `AuditLog.log()`-equivalent
    write paths is out of this chunk's scope (it's an admin-visibility listing endpoint, not an
    audit-logging retrofit of the whole adapter) — `admin/audit-logs/*` correctly serves whatever
    rows exist, which is currently none outside of tests that seed them directly.
    """

    __tablename__ = "tenxyte_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), default="")
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_applications.id", ondelete="SET NULL"), nullable=True
    )
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class LoginAttemptDB(Base):
    """Wave D chunk 4 (z_aud_3 task 10.1) — mirrors `tenxyte.models.operational.LoginAttempt`.
    Same scope note as `AuditLogDB`: no login endpoint writes to this table yet, for the same
    reason (out of this chunk's scope)."""

    __tablename__ = "tenxyte_login_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    identifier: Mapped[str] = mapped_column(String(191), index=True)
    ip_address: Mapped[str] = mapped_column(String(45))
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_applications.id", ondelete="SET NULL"), nullable=True
    )
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrganizationDB(Base):
    """Wave E (z_aud_3 task 11.1) — mirrors `tenxyte.models.organization.Organization`. Uses a
    UUID string primary key like every other table in this file, diverging from Django's
    integer `AutoField` — an established, already-silent convention across this whole port (every
    `*DB` table here uses a UUID pk regardless of Django's own pk type), not new to this wave."""

    __tablename__ = "tenxyte_organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_organizations.id", ondelete="CASCADE"), nullable=True
    )
    org_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_members: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (Index("ix_tenxyte_organizations_parent_active", "parent_id", "is_active"),)


class OrganizationRoleDB(Base):
    """Wave E (z_aud_3 task 11.1) — mirrors `tenxyte.models.organization.OrganizationRole`. Not
    tenant-scoped (global table, like Django's) — `permissions` is a plain JSON list of codes,
    checked with the same wildcard rule as Django's `has_permission()` (`"org.*"` matches every
    `org.` permission, an exact `perm == permission_code` match otherwise)."""

    __tablename__ = "tenxyte_organization_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrganizationMembershipDB(Base):
    """Wave E (z_aud_3 task 11.1) — mirrors `tenxyte.models.organization.OrganizationMembership`,
    the user<->organization<->role relationship table."""

    __tablename__ = "tenxyte_organization_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_organizations.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_organization_roles.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    invited_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
    invited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_tenxyte_org_membership_user_org"),
        Index("ix_tenxyte_org_membership_org_status", "organization_id", "status"),
    )


class OrganizationInvitationDB(Base):
    """Wave E (z_aud_3 task 11.1) — mirrors `tenxyte.models.organization.OrganizationInvitation`.
    No HTTP endpoint accepts/declines an invitation on the Django side either — only
    `invite_member` (creation) is ever registered in `urls.py`, despite the model exposing
    `accept()`/`decline()` methods — so this table's `status` never transitions past `pending` (or
    the `expired` a duplicate invite causes) through any real request path on either adapter."""

    __tablename__ = "tenxyte_organization_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_organizations.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(191))
    role_id: Mapped[str] = mapped_column(ForeignKey("tenxyte_organization_roles.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenxyte_users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_tenxyte_org_invitations_org_status", "organization_id", "status"),)
