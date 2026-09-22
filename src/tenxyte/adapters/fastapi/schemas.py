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
    the Django serializer's `validate()` cross-field rule.

    `must_change_password`: if True, the account is created with must_change_password=True
    (feature: force_password_change_on_first_login) — the next login issues a restricted
    password_change_only token instead of a full-scope one, as long as
    TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED is on server-side. Mirrors the Django
    RegisterSerializer's own must_change_password field."""

    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = ""
    last_name: str = ""
    login: bool = False
    must_change_password: bool = False


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


class OrganizationCreateRequest(BaseModel):
    """`parent_id` is a UUID string here, not the `IntegerField` Django's
    `CreateOrganizationSerializer` uses — this port's `OrganizationDB.id` is a UUID string like
    every other table (see `models_sa.py`'s `OrganizationDB` docstring), so the FK it references
    is one too."""

    name: str = Field(max_length=200)
    slug: str = ""
    description: str = ""
    parent_id: str | None = None
    metadata: dict = Field(default_factory=dict)
    max_members: int = Field(default=0, ge=0)


class OrganizationUpdateRequest(BaseModel):
    """Only `name`/`description`/`metadata`/`max_members` — matches
    `UpdateOrganizationSerializer` exactly (no `slug`/`parent_id`/`is_active`, see
    `org_service.py`'s module docstring)."""

    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    metadata: dict | None = None
    max_members: int | None = Field(default=None, ge=0)


class OrganizationAddMemberRequest(BaseModel):
    """`user_id` is a UUID string here, not the `IntegerField` Django's `AddMemberSerializer`
    uses — same reason as `OrganizationCreateRequest.parent_id`."""

    user_id: str
    role_code: str = Field(max_length=50)


class OrganizationUpdateMemberRoleRequest(BaseModel):
    role_code: str = Field(max_length=50)


class OrganizationInviteMemberRequest(BaseModel):
    email: EmailStr
    role_code: str = Field(max_length=50)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class WebAuthnRegisterCompleteRequest(BaseModel):
    """`credential` stays an untyped `dict` — same convention as `AgentTokenCreateRequest`'s
    `circuit_breaker`/`dead_mans_switch` — since it's the raw `PublicKeyCredential` JSON the
    browser's WebAuthn API produces, whose exact shape `py_webauthn`'s own parser validates, not
    this adapter."""

    credential: dict = Field(default_factory=dict)
    device_name: str = ""
    challenge_id: str = ""


class WebAuthnAuthenticateBeginRequest(BaseModel):
    email: str = ""


class WebAuthnAuthenticateCompleteRequest(BaseModel):
    credential: dict = Field(default_factory=dict)
    challenge_id: str = ""
    device_info: str = ""


class SocialAuthRequest(BaseModel):
    """Accepts `access_token`, `code`+`redirect_uri` (+`code_verifier`, PKCE), or `id_token`
    (Google/Apple only) — same three-way branch `SocialAuthView.post` reads, all optional at the
    schema level since exactly which combination is required depends on which one was actually
    sent (validated in `routers/social.py`, matching Django's own `request.data.get(...)` style
    rather than a Pydantic-level `oneOf`)."""

    access_token: str = ""
    code: str = ""
    redirect_uri: str = ""
    code_verifier: str = ""
    id_token: str = ""
    user: dict | None = None
    device_info: str = ""


class RequestAccountDeletionRequest(BaseModel):
    """`otp_code` gates a real 2FA check here (spec z_aud_3, Wave G chunk 3/4) — unlike
    `password/change/`'s `otp_code`, which is genuinely unimplemented reauth (see
    `routers/password.py`'s module docstring), this one verifies a live TOTP code the same way
    login does (`gdpr_service.py`'s module docstring documents why — Django's own equivalent gate
    crashes with `AttributeError` for every 2FA-enabled user, a bug this port fixes rather than
    replicates). `reauth_otp_code` (Login_OTP_Code-based reauth) stays unimplemented, same as
    every other Sensitive_Password_Action in this port — a request with only `reauth_otp_code`
    and no `password` gets `REAUTH_REQUIRED`."""

    password: str = ""
    reauth_otp_code: str = ""
    otp_code: str = ""
    reason: str = ""


class ConfirmAccountDeletionRequest(BaseModel):
    token: str


class CancelAccountDeletionRequest(BaseModel):
    """`otp_code` here is `reauth_otp_code`-equivalent reauth (not the 2FA gate) — Django's
    `cancel_deletion` only ever calls `ReauthService.verify`, never the 2FA/OTPService branch
    `request_deletion` does. Stays unimplemented, same reasoning as `password/change/`."""

    password: str = ""
    otp_code: str = ""


class ExportUserDataRequest(BaseModel):
    password: str = ""
    otp_code: str = ""


class ProcessDeletionRequest(BaseModel):
    confirmation: str = ""
    admin_notes: str = Field(default="", max_length=1000)
