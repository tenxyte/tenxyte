"""
Pydantic validation schemas for Tenxyte Core.

This module provides Pydantic models for data validation that work
independently of Django or DRF serializers.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

# ============================================================
# Enums
# ============================================================


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class MFAType(str, Enum):
    """Multi-factor authentication type."""

    NONE = "none"
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    SMS = "sms"
    EMAIL = "email"


# ============================================================
# Base Schemas
# ============================================================


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class TimestampMixin(BaseSchema):
    """Mixin for timestamp fields."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================
# User Schemas
# ============================================================


class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=150)
    last_name: Optional[str] = Field(None, max_length=150)
    is_active: bool = True
    is_superuser: bool = False
    is_staff: bool = False
    status: UserStatus = UserStatus.ACTIVE
    email_verified: bool = False


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, max_length=150)
    last_name: Optional[str] = Field(None, max_length=150)
    is_active: Optional[bool] = None
    status: Optional[UserStatus] = None
    email_verified: Optional[bool] = None


class UserResponse(UserBase, TimestampMixin):
    """Schema for user response (no sensitive data)."""

    id: str
    username: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    is_active: bool = True
    is_email_verified: bool = False
    is_phone_verified: bool = False
    is_2fa_enabled: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    custom_fields: Optional[Dict[str, Any]] = None
    preferences: Dict[str, bool] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=list, description="Flat list of assigned role codes")
    permissions: List[str] = Field(default_factory=list, description="Flat list of permission codes")

    # Computed/Deprecated properties for backward compatibility
    mfa_type: MFAType = MFAType.NONE
    mfa_enabled: bool = False
    full_name: Optional[str] = None

    @field_validator("full_name", mode="before")
    @classmethod
    def compute_full_name(cls, v, values) -> str:
        """Compute full name from first and last name."""
        data = values.data
        first = data.get("first_name", "")
        last = data.get("last_name", "")
        if first and last:
            return f"{first} {last}"
        return first or last or ""


class UserInDB(UserResponse):
    """Schema for user with internal fields (for DB operations)."""

    password_hash: Optional[str] = None
    mfa_secret: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Authentication Schemas
# ============================================================


class LoginRequest(BaseSchema):
    """Login request schema."""

    email: EmailStr
    password: str
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=6)
    remember_me: bool = False


class TokenResponse(BaseSchema):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    refresh_expires_in: int = Field(..., description="Refresh token lifetime in seconds")
    device_summary: Optional[str] = None


class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema."""

    refresh_token: str


class PasswordResetRequest(BaseSchema):
    """Password reset request schema."""

    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    """Password reset confirmation schema."""

    token: str
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class ChangePasswordRequest(BaseSchema):
    """Change password request schema."""

    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


# ============================================================
# 2FA Schemas
# ============================================================


class TOTPSetupResponse(BaseSchema):
    """TOTP setup response schema."""

    secret: str
    qr_code_uri: str
    backup_codes: List[str]


class TOTPVerifyRequest(BaseSchema):
    """TOTP verification request schema."""

    code: str = Field(..., min_length=6, max_length=6)


class MFAStatusResponse(BaseSchema):
    """MFA status response schema."""

    enabled: bool
    type: MFAType
    methods_available: List[MFAType]


# ============================================================
# Organization Schemas
# ============================================================


class OrganizationBase(BaseSchema):
    """Base organization schema."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: bool = True
    max_members: int = Field(0, ge=0)


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""

    owner_id: Optional[str] = None


class OrganizationUpdate(BaseSchema):
    """Schema for updating an organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    max_members: Optional[int] = Field(None, ge=0)


class OrganizationResponse(OrganizationBase, TimestampMixin):
    """Schema for organization response."""

    id: str
    owner_id: Optional[str] = None
    parent_id: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    member_count: int = 0


# ============================================================
# Role & Permission Schemas
# ============================================================


class PermissionResponse(TimestampMixin):
    """Schema for permission response."""

    id: str
    code: str
    name: str
    description: Optional[str] = None
    parent: Optional[Dict[str, str]] = None
    children: List[Dict[str, str]] = Field(default_factory=list)


class RoleBase(BaseSchema):
    """Base role schema."""

    code: str = Field(..., min_length=1, max_length=100, description="Unique role code")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: bool = Field(False, description="Whether this is a default role assigned to new users")


class RoleCreate(BaseSchema):
    """Schema for creating a role."""

    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permission_codes: List[str] = Field(default_factory=list, description="List of permission codes to assign")
    is_default: bool = False
    organization_id: Optional[str] = None


class RoleResponse(RoleBase, TimestampMixin):
    """Schema for role response."""

    id: str
    permissions: List[PermissionResponse] = Field(default_factory=list, description="Full permission objects with hierarchy")
    organization_id: Optional[str] = None


# ============================================================
# Audit Log Schemas
# ============================================================


class AuditLogEntry(BaseSchema):
    """Audit log entry schema."""

    id: str
    user: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    application: Optional[str] = None
    application_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


# ============================================================
# Magic Link Schemas
# ============================================================


class MagicLinkRequest(BaseSchema):
    """Magic link request schema."""

    email: EmailStr


class MagicLinkResponse(BaseSchema):
    """Magic link response (for admin/debug only)."""

    token: str
    expires_at: datetime


# ============================================================
# Error Response Schemas
# ============================================================


class ErrorDetail(BaseSchema):
    """Error detail schema."""

    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseSchema):
    """Standard error response schema."""

    error: str
    code: str
    details: Optional[Dict[str, List[str]]] = None


# ============================================================
# Pagination Schema
# ============================================================


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""

    count: int
    page: int
    page_size: int
    total_pages: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[Any]

# ============================================================
# Security Schemas (Session, Device, Attempts)
# ============================================================

class SessionResponse(BaseSchema):
    """Schema for user session."""
    
    id: str
    user_id: str
    device_info: Dict[str, Any] = Field(default_factory=dict)
    ip_address: str
    user_agent: str
    is_current: bool
    created_at: datetime
    last_activity: datetime
    expires_at: datetime

class DeviceResponse(BaseSchema):
    """Schema for tracked user devices."""
    
    id: str
    user_id: str
    device_fingerprint: str
    device_name: str
    device_type: str
    platform: str
    browser: str
    is_trusted: bool
    last_seen: datetime
    created_at: datetime

class LoginAttemptResponse(BaseSchema):
    """Schema for login attempts."""

    id: str
    identifier: str
    ip_address: str
    application: Optional[str] = None
    success: bool
    failure_reason: Optional[str] = None
    created_at: datetime

class BlacklistedTokenResponse(BaseSchema):
    """Schema for revoked tokens."""

    id: str
    token_jti: str
    user: Optional[str] = None
    user_email: Optional[str] = None
    blacklisted_at: datetime
    expires_at: datetime
    reason: str
    is_expired: bool
