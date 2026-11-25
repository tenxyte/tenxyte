"""
Parity_Group C — passwordless login via SMS OTP (spec z_aud_3, task 7.1): login/otp/request,
login/otp/verify. Contract extracted from the Django_Adapter's `views/login_otp_views.py`, which
itself explicitly replicates `LoginPhoneView`'s security controls and response shape (lockout,
banned/inactive checks, the `2fa_setup_only` admin bootstrap, normal 2FA verification) without
ever requiring a password.

Feature-gated by `Settings.otp_login_enabled` (default **off**, matching
`auth_settings.OTP_LOGIN_ENABLED`) — both endpoints reject with a uniform `404 FEATURE_DISABLED`
before doing anything else when disabled, exactly like Django: no code is generated, sent,
verified, or consumed, and nothing about the feature's existence leaks either way.

`login/otp/request/`'s anti-enumeration branch (unknown phone number, or found but
`otp_login_auto_register` is off) returns a response with the exact same shape/keys as the
real-account branch, using non-exploitable substitute values (`uuid4()`, a locally-computed fake
`expires_at`) — no code is ever generated or sent on that path.

Deliberately out of scope, matching the same already-documented decisions Wave A's
`routers/auth.py` made for `LoginPhoneView` itself (see that module's docstring): real RBAC. The
`2fa_setup_only` admin bootstrap, normal per-login TOTP verification, and the
`must_change_password`/`password_change_only` scope-upgrade (feature
`force_password_change_on_first_login`) ARE fully implemented here, identically to
`routers/auth.py`'s `_login()` — `resolve_forced_password_change_scope` is imported from
`.auth` rather than duplicated, since it's a pure function with no router-local state.

**Verified, pre-existing Django finding (not a porting bug, not "fixed" here — see
`test_verify_unknown_account_and_wrong_code_both_401_otp_invalid`):** `verify/`'s anti-enumeration
only holds at the status-code/`code`-field level, not the `error` message text. An unregistered
number always gets the literal `"Invalid or expired code"`; a *registered* number with no
outstanding code gets `"No login code found"`; one with an active code and a wrong guess gets
`"Invalid code. N attempt(s) remaining."` — three different strings for what a client-observing
caller experiences as "my code didn't work". This is `LoginOTPVerifyView`'s real, current behavior
in the Django_Adapter (traced directly from `otp_service.verify_login_otp`'s return values, not
from its docstrings), so it's replicated here rather than silently improved — silently closing it
would be a parity break, not a fix, and is out of this spec's scope.

`login/otp/verify/`'s `otp_code` isn't length-validated the way `otp/verify/*`'s `VerifyOTPRequest`
is (`Field(min_length=6, max_length=6)`) — Django's `LoginOTPVerifySerializer` does enforce exactly
6 characters and would 400 first with `VALIDATION_ERROR` before ever touching `OTPService`. Here a
wrong-length code just falls through to the normal verify path and comes back `401 OTP_INVALID`
(via the "no matching hash" branch) instead of `400 VALIDATION_ERROR` — same eventual rejection,
different status code on that one edge case. Not replicated because doing so would mean giving
`otp_code` a strict Pydantic length constraint, which (like `email`/`validation_url` on
`magic-link/request/` — see `routers/magic_link.py`) would make FastAPI raise its own generic 422
instead of the canonical `{error, code, details}` shape on a missing/malformed field.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi.auth_lookup import _locked_key
from tenxyte.adapters.fastapi.deps import (
    get_cache_service,
    get_db_session,
    get_jwt_service,
    get_settings,
    get_totp_service,
)
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.login_response import finalize_login_response as _finalize_login_response
from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.adapters.fastapi.otp_service import generate_otp, verify_otp
from tenxyte.adapters.fastapi.refresh_tokens import issue_refresh_token as _issue_refresh_token
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.routers.auth import resolve_forced_password_change_scope
from tenxyte.adapters.fastapi.schemas import LoginOTPRequestRequest, LoginOTPVerifyRequest
from tenxyte.adapters.fastapi.serialization import serialize_user
from tenxyte.adapters.fastapi.throttling import _get_client_ip
from tenxyte.adapters.fastapi.totp_storage import SQLAlchemyTOTPStorage
from tenxyte.core.cache_service import CacheService
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings
from tenxyte.core.totp_service import TOTPService
from tenxyte.device_info import build_device_info_from_user_agent, get_device_summary
from tenxyte.ports.repositories import User

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolved_application_id(request: Request) -> str:
    application = getattr(request.state, "application", None)
    return str(application.id) if application is not None else "default"


def _otp_response_payload(otp_id: str, expires_at: datetime) -> dict:
    """Same shape shared by the existing-account, auto-register, and anti-enumeration paths —
    same keys, same types (spec z_aud_3, Property 3)."""
    return {"message": "OTP sent", "otp_id": otp_id, "expires_at": expires_at.isoformat(), "channel": "sms"}


@router.post("/login/otp/request/")
async def login_otp_request(
    body: LoginOTPRequestRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    if not settings.otp_login_enabled:
        raise TenxyteAPIError("This feature is not enabled", code="FEATURE_DISABLED", status_code=404)

    if not body.phone_country_code or not body.phone_number:
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={
                k: ["This field is required."]
                for k in (["phone_country_code"] if not body.phone_country_code else [])
                + (["phone_number"] if not body.phone_number else [])
            },
        )

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user = await user_repo.get_by_phone(body.phone_country_code, body.phone_number)

    if user is None and settings.otp_login_auto_register:
        # Passwordless account: a random, never-shown password — nobody, including the account's
        # own owner, authenticates with it; only OTP codes do.
        password_hash = bcrypt.hashpw(
            secrets.token_urlsafe(32).encode("utf-8"), bcrypt.gensalt(rounds=settings.bcrypt_rounds)
        ).decode("utf-8")
        new_user = User(
            id=str(uuid.uuid4()),
            email=f"{uuid.uuid4()}@passwordless.invalid",
            password_hash=password_hash,
            is_active=True,
            metadata={"phone_country_code": body.phone_country_code, "phone_number": body.phone_number},
        )
        user = await user_repo.create(new_user)

    if user is not None:
        row, raw_code = await generate_otp(session, user.id, "login", settings)
        logger.info("OTP delivery (no real backend wired in): sms code=%s to=%s", raw_code, body.phone_number)
        return _otp_response_payload(row.id, row.expires_at)

    # Anti-enumeration: no account, and auto-register is off. Identical response shape, no side
    # effects, no code generated or sent.
    fake_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_login_validity_minutes)
    return _otp_response_payload(str(uuid.uuid4()), fake_expires_at)


@router.post("/login/otp/verify/")
async def login_otp_verify(
    body: LoginOTPVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
):
    if not settings.otp_login_enabled:
        raise TenxyteAPIError("This feature is not enabled", code="FEATURE_DISABLED", status_code=404)

    # Anti-enumeration: an absent account must yield exactly the same response as an existing
    # account with a wrong/expired code.
    invalid_code_error = TenxyteAPIError("Invalid or expired code", code="OTP_INVALID", status_code=401)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user = await user_repo.get_by_phone(body.phone_country_code, body.phone_number)
    if user is None:
        raise invalid_code_error

    # Pre-check 2FA BEFORE consuming the OTP: verify_otp() is destructive (marks the code used as
    # soon as it's valid). If we consumed it here and then returned 2FA_REQUIRED, a second pass
    # (OTP + TOTP together) would fail because the OTP would already be spent — so a 2FA-enabled
    # account must prove it has a totp_code ready before the OTP is ever touched.
    pre_mfa = user.mfa_type.value
    if pre_mfa != "none" and not body.totp_code.strip():
        raise TenxyteAPIError("2FA code required", code="2FA_REQUIRED", status_code=401, extra={"requires_2fa": True})

    result = await verify_otp(session, user.id, "login", body.otp_code)
    if not result.success:
        code = "OTP_EXPIRED" if "expired" in result.error.lower() else "OTP_INVALID"
        raise TenxyteAPIError(result.error, code=code, status_code=401)

    if await cache_service.exists_async(_locked_key(user.id)):
        raise TenxyteAPIError(
            "Account has been locked due to too many failed login attempts",
            code="ACCOUNT_LOCKED",
            status_code=423,
            extra={"retry_after": settings.lockout_duration},
        )

    if (user.metadata or {}).get("is_banned"):
        raise TenxyteAPIError("Account has been banned", code="ACCOUNT_BANNED", status_code=401)

    if not user.is_active:
        raise TenxyteAPIError("Account is inactive", code="ACCOUNT_INACTIVE", status_code=401)

    # Login OTP proves possession of the phone number.
    await user_repo.verify_phone(user.id)

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
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "token_scope": "2fa_setup_only",
            "requires_2fa_setup": True,
            "expires_in": 900,
        }

    if mfa_type_value != "none":
        totp_code = body.totp_code.strip()
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
        user_id=user.id,
        application_id=app_id,
        extra_claims={"email": user.email, "device_info": device_info, "ip_address": _get_client_ip(request)},
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
        "user": serialize_user(user),
        "requires_2fa": mfa_type_value != "none",
        "session_id": None,
        "device_id": None,
        "must_change_password": False,
    }

    # Force password change gating (feature: force_password_change_on_first_login). Precedence:
    # the 2fa_setup_only admin bootstrap is already returned earlier, unconditionally ahead of
    # this check — mirrors auth_views.py's own precedence rule exactly.
    user_db = await session.get(UserDB, user.id)
    forced_scope = resolve_forced_password_change_scope(settings, user_db)
    if forced_scope == "password_change_only":
        restricted_token, _jti, _expires_at = jwt_service.generate_access_token(
            user_id=user.id, application_id=app_id, extra_claims={"scope": "password_change_only"}
        )
        data["access_token"] = restricted_token
        data["token_scope"] = "password_change_only"
        data["must_change_password"] = True

    return _finalize_login_response(data, settings)
