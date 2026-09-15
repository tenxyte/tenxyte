"""
Pydantic request bodies for the Wave A/B/C routers (spec z_aud_3, tasks 5.1/6.1/7.1) — response
bodies are deliberately plain `dict`s built by hand in `routers/*.py`, not `response_model`s: the
Django contract's response shape genuinely varies by branch (bootstrap token vs restricted-scope
token vs normal success), and forcing all three through one Pydantic response model would either
lose fields or require a union type that adds no real validation value over just building the
dict that matches the branch actually taken.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Email-only for now — phone registration is deferred (see routers/auth.py's module
    docstring), so `email` is required here rather than optional-with-a-phone-alternative like
    the Django serializer's `validate()` cross-field rule."""

    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = ""
    last_name: str = ""
    login: bool = False


class LoginEmailRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str = ""


class LoginPhoneRequest(BaseModel):
    phone_country_code: str = Field(max_length=5)
    phone_number: str = Field(max_length=20)
    password: str
    totp_code: str = ""


class RefreshTokenRequest(BaseModel):
    refresh_token: str = ""


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    """`otp_code` is accepted for schema/shape parity with the Django_Adapter's
    `ChangePasswordSerializer` but OTP-based reauth isn't implemented yet (see
    routers/password.py's module docstring) — `current_password` is the only working proof."""

    current_password: str = ""
    new_password: str = Field(min_length=8)
    otp_code: str = ""


class PasswordStrengthRequest(BaseModel):
    password: str = ""
    email: EmailStr | None = None


class RequestOTPRequest(BaseModel):
    otp_type: Literal["email", "phone"]


class VerifyOTPRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class PasswordResetRequestRequest(BaseModel):
    """Named with the doubled `Request` deliberately — mirrors the endpoint
    (`password/reset/request/`), not a typo."""

    email: EmailStr | None = None
    phone_country_code: str | None = None
    phone_number: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    otp_code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)
    email: EmailStr | None = None
    phone_country_code: str | None = None
    phone_number: str | None = None


class SetInitialPasswordRequest(BaseModel):
    otp_code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


class TwoFactorConfirmRequest(BaseModel):
    code: str = ""


class TwoFactorDisableRequest(BaseModel):
    """`otp_code` is accepted for schema/shape parity with the Django_Adapter's reauth gate but
    OTP-based reauth isn't implemented yet (see routers/twofa.py's module docstring) —
    `password` is the only working proof."""

    code: str = ""
    password: str = ""
    otp_code: str = ""


class TwoFactorBackupCodesRequest(BaseModel):
    code: str = ""


class MagicLinkRequestRequest(BaseModel):
    """`email`/`validation_url` default to `""` rather than being Pydantic-required — same
    convention as `PasswordResetRequestRequest` — so a missing field produces the exact
    `EMAIL_REQUIRED`/`VALIDATION_URL_REQUIRED` canonical error the Django_Adapter returns, not a
    generic 422."""

    email: str = ""
    validation_url: str = ""


class LoginOTPRequestRequest(BaseModel):
    phone_country_code: str = Field(default="", max_length=5)
    phone_number: str = Field(default="", max_length=20)


class LoginOTPVerifyRequest(BaseModel):
    phone_country_code: str = Field(default="", max_length=5)
    phone_number: str = Field(default="", max_length=20)
    otp_code: str = ""
    totp_code: str = ""


class AgentTokenCreateRequest(BaseModel):
    """`circuit_breaker`/`dead_mans_switch` stay untyped `dict`s — same as the Django_Adapter's
    own `serializers.DictField()` — since AIRS/1.0 doesn't mandate their exact shape beyond the
    handful of keys `airs_service.create_async` reads out of them."""

    agent_id: str = "unknown"
    expires_in: int | None = None
    permissions: list[str] = Field(default_factory=list)
    organization: str | None = None
    budget_limit_usd: float | None = None
    circuit_breaker: dict | None = None
    dead_mans_switch: dict | None = None


class AgentReportUsageRequest(BaseModel):
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class PendingActionTokenRequest(BaseModel):
    token: str = ""


class PermissionCreateRequest(BaseModel):
    code: str
    name: str
    description: str = ""
    parent_code: str | None = None


class PermissionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_code: str | None = Field(default="__unset__")


class RoleCreateRequest(BaseModel):
    code: str
    name: str
    description: str = ""
    is_default: bool = False
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    permission_codes: list[str] | None = None


class ManageRolePermissionsRequest(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)


class AssignRoleRequest(BaseModel):
    role_code: str = ""


class ApplicationCreateRequest(BaseModel):
    name: str
    description: str = ""
    allowed_origins: list[str] = Field(default_factory=list)


class ApplicationUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    allowed_origins: list[str] | None = None


class ApplicationToggleRequest(BaseModel):
    is_active: bool | None = None


class ApplicationRegenerateRequest(BaseModel):
    confirmation: str = ""


class AdminUserUpdateRequest(BaseModel):
    """Accepts the same fields as Django's `AdminUserUpdateSerializer`, including
    `is_staff`/`is_superuser`/`max_sessions`/`max_devices` — matched for validation-shape parity
    even though `admin_user_service.update_user_async` deliberately drops them, mirroring a real
    Django behavior (see admin_user_service.py's module docstring)."""

    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    is_staff: bool | None = None
    is_superuser: bool | None = None
    max_sessions: int | None = Field(default=None, ge=0)
    max_devices: int | None = Field(default=None, ge=0)
    must_change_password: bool | None = None


class BanUserRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


class LockUserRequest(BaseModel):
    duration_minutes: int = Field(default=30, ge=1, le=43200)
    reason: str = Field(default="", max_length=500)
