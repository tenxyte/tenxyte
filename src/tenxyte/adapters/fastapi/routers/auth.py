"""
Parity_Group A — basic auth (spec z_aud_3, task 5.1): register, login/email, login/phone,
refresh, logout, logout/all, me (GET/PATCH), me/roles. Contract extracted from the
Django_Adapter's `views/auth_views.py` and `views/user_views.py` (register/login/refresh
anti-enumeration and lockout semantics, the `2fa_setup_only` admin bootstrap, the refresh-token
cookie opt-in).

`login/phone/` resolves users via `UserDB.phone_country_code`/`phone_number` (dedicated indexed
columns added as a Wave A follow-up — see `models_sa.py`), mirrored into the port `User`'s
`metadata` dict on read since the Core dataclass has no dedicated phone fields. `register/` itself
is still email-only: nothing here creates a phone-registered account, so `login/phone/`'s tests
seed one directly through the repository, the same convention already used for 2FA-enabled test
accounts (Group C hasn't shipped 2FA setup either).

Deliberately out of scope for this pass (documented rather than silently skipped):

- **Phone *registration*** — `RegisterRequest` stays email-only; Django's `RegisterSerializer`
  accepts email-or-phone via a cross-field `validate()` rule this port doesn't replicate yet.
- **`must_change_password` / `password_change_only` scope** — this flag lives only on Django's
  `User` model (`DJANGO_ONLY_FIELDS = {"must_change_password"}` in the admin view), is not part
  of the framework-agnostic Core `User` port dataclass, and the feature it drives
  (`FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED`) defaults OFF in Django itself. It's also the
  subject of its own separate spec (`specs/force_password_change_on_first_login/`) that hasn't
  been executed. `logout/all/`'s `require_jwt(allowed_scopes=["password_change_only"])` keeps the
  same allow-list entry as Django for structural parity, even though nothing here currently issues
  such a token.
- **Real RBAC on `me/roles/`** — no roles/permissions tables exist in the Reference_Stack yet
  (Group D, task 10.1); the endpoint enforces the same auth/scope contract as Django but returns
  empty `roles`/`permissions` lists.
- **`RefreshTokenDB` admin listing** — Group D's endpoints (`admin/refresh-tokens/*`), not
  needed for Wave A's own contract.

2FA: the admin-no-mfa-configured *bootstrap* path (`2fa_setup_only`, 15-minute restricted token)
is fully implemented — it only needs `User.mfa_type`/`is_superuser`/`is_staff`, already on the
Core port dataclass. Normal TOTP verification for a user who already has 2FA enabled is also
implemented for real, backed by `SQLAlchemyTOTPStorage` (read-only — see its own docstring);
setting 2FA up in the first place is Group C's job (task 7.1), so no FastAPI-created account can
reach that state yet — only one seeded directly in the database (e.g. by a test) can.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from tenxyte.adapters.fastapi.auth_lookup import SQLAlchemyEmailPasswordLookup, SQLAlchemyPhonePasswordLookup
from tenxyte.adapters.fastapi.deps import (
    get_cache_service,
    get_db_session,
    get_jwt_service,
    get_settings,
    get_totp_service,
)
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.refresh_tokens import issue_refresh_token as _issue_refresh_token
from tenxyte.adapters.fastapi.refresh_tokens import (
    redeem_refresh_token,
    revoke_all_for_user,
    revoke_refresh_token,
    revoke_refresh_token_row,
)
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.schemas import (
    LoginEmailRequest,
    LoginPhoneRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.adapters.fastapi.totp_storage import SQLAlchemyTOTPStorage
from tenxyte.core.auth_service import AuthenticationService
from tenxyte.core.cache_service import CacheService
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings
from tenxyte.core.totp_service import TOTPService
from tenxyte.device_info import build_device_info_from_user_agent, get_device_summary
from tenxyte.ports.repositories import User

router = APIRouter()

_EMAIL_LOGIN_ERROR_MESSAGES = {
    "user_not_found": "Invalid email or password",
    "account_inactive": "Account is inactive",
    "account_banned": "Account has been banned",
    "invalid_password": "Invalid email or password",
}

_PHONE_LOGIN_ERROR_MESSAGES = {
    "user_not_found": "Invalid phone number or password",
    "account_inactive": "Account is inactive",
    "account_banned": "Account has been banned",
    "invalid_password": "Invalid phone number or password",
}


def _serialize_user(user: User) -> dict:
    """Same field names as the Django_Adapter's `UserSerializer` — several (username, phone,
    avatar, bio, timezone, language, custom_fields, roles, permissions) have no Reference_Stack
    storage yet and are stubbed to their empty value rather than omitted, so the response shape
    matches even where the content doesn't yet."""
    return {
        "id": user.id,
        "email": user.email,
        "username": None,
        "phone": None,
        "avatar": None,
        "bio": "",
        "timezone": "",
        "language": "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "is_active": user.is_active,
        "is_email_verified": user.email_verified,
        "is_phone_verified": False,
        "is_2fa_enabled": user.mfa_type.value != "none",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "custom_fields": {},
        "preferences": {"email_notifications": True, "sms_notifications": False, "marketing_emails": False},
        "roles": [],
        "permissions": [],
    }


def _resolved_application_id(request: Request) -> str:
    application = getattr(request.state, "application", None)
    return str(application.id) if application is not None else "default"


def _set_refresh_cookie(response: JSONResponse, settings: Settings, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        max_age=settings.jwt_refresh_token_lifetime,
        httponly=True,
        secure=True,
        samesite=settings.refresh_token_cookie_samesite,
        path=settings.refresh_token_cookie_path,
    )


def _clear_refresh_cookie(response: JSONResponse, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=settings.refresh_token_cookie_path,
        samesite=settings.refresh_token_cookie_samesite,
    )


def _finalize_login_response(data: dict, settings: Settings, status_code: int = 200) -> JSONResponse:
    """Builds the outgoing response, moving `refresh_token` into an HttpOnly cookie and out of
    the JSON body when `TENXYTE_REFRESH_TOKEN_COOKIE_ENABLED` is on — same conditional shape the
    Django_Adapter's `_set_refresh_cookie` produces."""
    refresh_token = data.get("refresh_token")
    if settings.refresh_token_cookie_enabled and refresh_token is not None:
        data = {k: v for k, v in data.items() if k != "refresh_token"}
        response = JSONResponse(status_code=status_code, content=data)
        _set_refresh_cookie(response, settings, refresh_token)
        return response
    return JSONResponse(status_code=status_code, content=data)


@router.post("/register/", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
):
    user_repo = SQLAlchemyAsyncUserRepository(session)
    existing = await user_repo.get_by_email(body.email)

    if existing is not None:
        # Anti-enumeration (Property 3): identical shape/status whether the account existed or
        # not. The Django_Adapter also emails a security alert to the real owner on this path —
        # not replicated here (no email service wired into the Reference_Stack), but that's an
        # invisible side channel to the caller either way, so parity of the *response* holds.
        #
        # Built via the SAME _serialize_user() the real path uses below, not a hand-rolled dict —
        # a prior hand-rolled version silently drifted from _serialize_user()'s shape (missing
        # keys like username/avatar/roles, and phone:"" instead of phone:None), which Hypothesis
        # eventually caught: differing response *shape* between the two branches is exactly the
        # enumeration signal this endpoint exists to prevent, so the two must be built identically.
        now = datetime.now(timezone.utc)
        fake_user = User(
            id=str(uuid4()),
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        return {
            "message": "Registration successful",
            "user": _serialize_user(fake_user),
            "verification_required": {"email": True, "phone": False},
        }

    password_bytes = body.password.encode("utf-8")
    if len(password_bytes) > 72:
        # bcrypt hard-fails past 72 bytes (not characters — a multi-byte-character password well
        # under any character-count limit can still exceed this). Caught here as a clean
        # validation error instead of letting it crash the handler as an unhandled 500.
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"password": ["Password must be at most 72 bytes when UTF-8 encoded"]},
        )

    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("utf-8")
    new_user = User(
        id=str(uuid4()),
        email=body.email,
        password_hash=hashed,
        first_name=body.first_name,
        last_name=body.last_name,
        is_active=True,
    )
    created = await user_repo.create(new_user)

    response_data: dict = {
        "message": "Registration successful",
        "user": _serialize_user(created),
        "verification_required": {"email": True, "phone": False},
    }

    if body.login:
        app_id = _resolved_application_id(request)
        pair = jwt_service.generate_new_token_pair(user_id=created.id, application_id=app_id)
        refresh_token = await _issue_refresh_token(
            session, created.id, lifetime_seconds=settings.jwt_refresh_token_lifetime
        )
        response_data.update(
            {
                "access_token": pair.access_token,
                "refresh_token": refresh_token,
                "token_type": pair.token_type,
                "expires_in": pair.expires_in,
                "refresh_expires_in": settings.jwt_refresh_token_lifetime,
            }
        )

    return response_data


async def _login(
    *,
    request: Request,
    session: AsyncSession,
    settings: Settings,
    jwt_service: JWTService,
    totp_service: TOTPService,
    lookup,
    identifier: object,
    password: str,
    totp_code: str,
    error_messages: dict[str, str],
) -> JSONResponse:
    """Shared by `login_email` and `login_phone` — the Django_Adapter's `LoginEmailView` and
    `LoginPhoneView` differ only in identifier resolution and their anti-enumeration message
    map, never in lockout/2FA-bootstrap/2FA-verify/token-issuance logic."""
    user_repo = lookup.user_repo
    auth_service = AuthenticationService(settings=settings, user_lookup=lookup)

    result = await auth_service.authenticate_async(identifier, password)

    if not result.success:
        if result.failure_reason == "account_locked":
            raise TenxyteAPIError(
                "Account locked",
                code="ACCOUNT_LOCKED",
                status_code=423,
                details=result.error,
                extra={"retry_after": settings.lockout_duration},
            )
        message = error_messages.get(result.failure_reason, result.error)
        raise TenxyteAPIError(message, code="LOGIN_FAILED", status_code=401)

    user = result.user
    app_id = _resolved_application_id(request)
    is_admin = user.is_superuser or user.is_staff
    mfa_type_value = user.mfa_type.value

    if is_admin and mfa_type_value == "none":
        access_token, _jti, _expires_at = jwt_service.generate_access_token(
            user_id=user.id,
            application_id=app_id,
            extra_claims={"scope": "2fa_setup_only"},
            custom_lifetime=timedelta(minutes=15),
        )
        return JSONResponse(
            status_code=200,
            content={
                "access_token": access_token,
                "token_type": "Bearer",
                "token_scope": "2fa_setup_only",
                "requires_2fa_setup": True,
                "expires_in": 900,
            },
        )

    requires_2fa = mfa_type_value != "none"
    if requires_2fa:
        if not totp_code:
            raise TenxyteAPIError(
                "2FA code required", code="2FA_REQUIRED", status_code=401, extra={"requires_2fa": True}
            )
        storage = SQLAlchemyTOTPStorage(user_repo)
        ok, error_message = await totp_service.verify_2fa_async(user.id, totp_code, storage)
        if not ok:
            raise TenxyteAPIError(error_message, code="INVALID_2FA_CODE", status_code=401)

    device_info = request.headers.get("User-Agent", "")
    device_info = build_device_info_from_user_agent(device_info) if device_info else ""

    pair = jwt_service.generate_new_token_pair(
        user_id=user.id, application_id=app_id, extra_claims={"device_info": device_info}
    )
    refresh_token = await _issue_refresh_token(session, user.id, lifetime_seconds=settings.jwt_refresh_token_lifetime)
    await user_repo.update_last_login(user.id, datetime.now(timezone.utc))

    data = {
        "access_token": pair.access_token,
        "refresh_token": refresh_token,
        "token_type": pair.token_type,
        "expires_in": pair.expires_in,
        "refresh_expires_in": settings.jwt_refresh_token_lifetime,
        "device_summary": get_device_summary(device_info) if device_info else "Unknown device",
        "user": _serialize_user(user),
        "requires_2fa": requires_2fa,
        "session_id": None,
        "device_id": None,
        "must_change_password": False,
    }
    return _finalize_login_response(data, settings)


@router.post("/login/email/")
async def login_email(
    body: LoginEmailRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
):
    user_repo = SQLAlchemyAsyncUserRepository(session)
    lookup = SQLAlchemyEmailPasswordLookup(user_repo, cache_service, settings)
    return await _login(
        request=request,
        session=session,
        settings=settings,
        jwt_service=jwt_service,
        totp_service=totp_service,
        lookup=lookup,
        identifier=body.email,
        password=body.password,
        totp_code=body.totp_code,
        error_messages=_EMAIL_LOGIN_ERROR_MESSAGES,
    )


@router.post("/login/phone/")
async def login_phone(
    body: LoginPhoneRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
):
    user_repo = SQLAlchemyAsyncUserRepository(session)
    lookup = SQLAlchemyPhonePasswordLookup(user_repo, cache_service, settings)
    return await _login(
        request=request,
        session=session,
        settings=settings,
        jwt_service=jwt_service,
        totp_service=totp_service,
        lookup=lookup,
        identifier=(body.phone_country_code, body.phone_number),
        password=body.password,
        totp_code=body.totp_code,
        error_messages=_PHONE_LOGIN_ERROR_MESSAGES,
    )


@router.post("/refresh/")
async def refresh_token_view(
    body: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
):
    raw_refresh_token = body.refresh_token
    if not raw_refresh_token and settings.refresh_token_cookie_enabled:
        raw_refresh_token = request.cookies.get(settings.refresh_token_cookie_name, "")

    if not raw_refresh_token:
        raise TenxyteAPIError("refresh_token is required", code="MISSING_REFRESH_TOKEN", status_code=400)

    row = await redeem_refresh_token(session, raw_refresh_token)
    if row is None:
        raise TenxyteAPIError("Invalid or expired refresh token", code="REFRESH_FAILED", status_code=401)

    app_id = _resolved_application_id(request)
    access_token, _jti, expires_at = jwt_service.generate_access_token(user_id=row.user_id, application_id=app_id)
    await revoke_refresh_token_row(session, row)
    new_refresh_token = await _issue_refresh_token(
        session, row.user_id, lifetime_seconds=settings.jwt_refresh_token_lifetime, device_id=row.device_id
    )

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user = await user_repo.get_by_id(row.user_id)

    data = {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "expires_in": int((expires_at - datetime.now(expires_at.tzinfo)).total_seconds()),
        "refresh_expires_in": settings.jwt_refresh_token_lifetime,
        "must_change_password": False,
    }
    if user is not None:
        data["user"] = _serialize_user(user)
    return _finalize_login_response(data, settings)


@router.post("/logout/")
async def logout(
    body: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
):
    if not body.refresh_token:
        raise TenxyteAPIError("refresh_token is required", code="MISSING_REFRESH_TOKEN", status_code=400)

    await revoke_refresh_token(session, body.refresh_token)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
        await jwt_service.blacklist_token_async(access_token, reason="logout")

    response = JSONResponse(status_code=200, content={"message": "Logged out successfully"})
    if settings.refresh_token_cookie_enabled:
        _clear_refresh_cookie(response, settings)
    return response


@router.post("/logout/all/")
async def logout_all(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allowed_scopes=["password_change_only"])),  # noqa: B008
):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
        await jwt_service.blacklist_token_async(access_token, reason="logout_all")

    count = await revoke_all_for_user(session, auth.user.id)
    return {"message": f"Logged out from {count} devices"}


@router.get("/me/")
async def get_me(auth: AuthContext = Depends(require_jwt(allow_any_scope=True))):  # noqa: B008
    # Parity note: Django's MeView authenticates via plain DRF IsAuthenticated, not
    # @require_jwt, so it never inspects the scope claim — a restricted-scope token (e.g. the
    # 2fa_setup_only bootstrap token) is accepted here too, unlike me/roles/ below.
    return _serialize_user(auth.user)


@router.patch("/me/")
async def update_me(
    body: UpdateProfileRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allow_any_scope=True)),  # noqa: B008
):
    user_repo = SQLAlchemyAsyncUserRepository(session)
    updated_fields = body.model_dump(exclude_unset=True)

    email_changed = "email" in updated_fields and updated_fields["email"] != auth.user.email

    current = await user_repo.get_by_id(auth.user.id)
    if current is None:
        raise TenxyteAPIError("User not found", code="NOT_FOUND", status_code=404)

    for field_name, value in updated_fields.items():
        setattr(current, field_name, value)
    if email_changed:
        current.email_verified = False

    saved = await user_repo.update(current)

    return {
        "message": "Profile updated successfully",
        "updated_fields": list(updated_fields.keys()),
        "user": _serialize_user(saved),
        "verification_required": {"email_changed": email_changed, "phone_changed": False},
    }


@router.get("/me/roles/")
async def my_roles(auth: AuthContext = Depends(require_jwt())):  # noqa: B008
    # No RBAC tables in the Reference_Stack yet (Group D, task 10.1) — the auth/scope contract is
    # enforced identically to Django, but the lists themselves are empty until that group ships.
    return {"roles": [], "permissions": []}
