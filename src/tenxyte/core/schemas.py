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
        extra='ignore',
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
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
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
    last_login: Optional[datetime] = None
    mfa_type: MFAType = MFAType.NONE
    mfa_enabled: bool = False
    
    # Computed properties
    full_name: Optional[str] = None
    
    @field_validator('full_name', mode='before')
    @classmethod
    def compute_full_name(cls, v, values) -> str:
        """Compute full name from first and last name."""
        data = values.data
        first = data.get('first_name', '')
        last = data.get('last_name', '')
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
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class ChangePasswordRequest(BaseSchema):
    """Change password request schema."""
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
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

class RoleBase(BaseSchema):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: List[str] = Field(default_factory=list)
    is_system: bool = False


class RoleCreate(RoleBase):
    """Schema for creating a role."""
    organization_id: Optional[str] = None


class RoleResponse(RoleBase, TimestampMixin):
    """Schema for role response."""
    id: str
    organization_id: Optional[str] = None


# ============================================================
# Audit Log Schemas
# ============================================================

class AuditLogEntry(BaseSchema):
    """Audit log entry schema."""
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    organization_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
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
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Pagination Schema
# ============================================================

class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool
