"""
Parity_Group B — password management (spec z_aud_3, tasks 6.1 + Wave C follow-up): all 6
endpoints. Contract extracted from the Django_Adapter's `views/password_views.py` and
`serializers/password_serializers.py`. `password/reset/request/`, `password/reset/confirm/`, and
`password/set-initial/` were initially deferred (blocked on OTP-code storage, which didn't exist
in the Reference_Stack) and completed once Wave C's `otp_service.py`/`OTPCodeDB` landed.

**OTP-based reauth on `password/change/`** stays partial: `ReauthService.verify()` accepts
`current_password` OR `otp_code`, but the `otp_code` path reuses a `login`-type OTP in Django —
plumbing that through here would mean issuing login OTPs outside the login flow itself, which is
more than this endpoint's own scope warrants. A request with only `otp_code` and no
`current_password` gets `REAUTH_REQUIRED`, same as Django's "neither provided" case — an honest
signal, not a silent accept.

Also out of scope, matching the Django_Adapter's own actual behavior (not a gap — porting it
would be a parity BREAK, not a fix): password-history/reuse checking (Django defines a
`PasswordHistory` model but never calls it — `PASSWORD_REUSED` is documented but unreachable).

`change_password`/`set_initial_password` DO implement the `must_change_password`/scope-upgrade
branch (feature `force_password_change_on_first_login`, mirroring `password_views.py`'s
`ChangePasswordView`/`SetInitialPasswordView` exactly): on success, if the user's raw `must_change_
password` flag is set, it's cleared and — only if the request was made with a `Restricted_Password_
Token` (`auth.scope == "password_change_only"`) — a fresh full-scope token pair is issued in the
response, same "clear flag, upgrade only if the caller actually needed it" pattern
`routers/twofa.py`'s `twofa_confirm` already uses for the `2fa_setup_only` bootstrap. `auth.user`
(the Core `User` port dataclass from `AuthContext`) has no `must_change_password` field — same
architectural choice Django makes — so both views re-fetch the raw `UserDB` row via `session.get`
and reuse `admin_user_service.update_user_async` to persist the clear, the same helper the admin
`PATCH /admin/users/<id>/` endpoint already uses to *set* the flag.

Password-strength validation (`password_strength.py`) and the breach check (`breach_check.py`) are
each a framework-agnostic *reimplementation*, not a reuse of `tenxyte.validators`/
`tenxyte.services.breach_check_service` — both of those import `tenxyte.conf`, which imports
`django.conf.settings` at module load time, making them unimportable from a Django-less FastAPI
process. Structurally identical contract (score/strength/is_valid/errors/requirements; breach
hard-rejects the same way), English wording rather than Django's French validator strings — no
reasonable API contract requires clients to string-match a validation message, only its shape.

**`password/reset/confirm/`'s breach check is deliberately non-blocking** (sets `password_safe:
false` in the response but still resets the password) — this is Django's real, verified behavior,
not a gap: unlike `password/change/`/`password/set-initial/`, `PasswordResetConfirmView` never
hard-rejects a breached password.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request, Response
from tenxyte.adapters.fastapi import breach_check, otp_service, password_strength
from tenxyte.adapters.fastapi.admin_user_service import update_user_async
from tenxyte.adapters.fastapi.deps import get_db_session, get_jwt_service, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.adapters.fastapi.refresh_tokens import revoke_all_for_user
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.schemas import (
    ChangePasswordRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequestRequest,
    PasswordStrengthRequest,
    SetInitialPasswordRequest,
)
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.core.auth_service import hash_password, verify_password
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolved_application_id(request: Request) -> str:
    application = getattr(request.state, "application", None)
    return str(application.id) if application is not None else "default"


def _raise_if_weak(new_password: str, settings: Settings) -> None:
    result = password_strength.validate(new_password, settings)
    if not result.is_valid:
        raise TenxyteAPIError(
            "Validation error", code="VALIDATION_ERROR", status_code=400, details={"new_password": result.errors}
        )


@router.post("/password/strength/")
async def password_strength_view(
    body: PasswordStrengthRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    result = password_strength.validate(body.password, settings)
    return {
        "score": result.score,
        "strength": result.strength,
        "is_valid": result.is_valid,
        "errors": [] if result.is_valid else result.errors,
        "requirements": password_strength.get_requirements(settings),
    }


@router.get("/password/requirements/")
async def password_requirements_view(settings: Settings = Depends(get_settings)):  # noqa: B008
    return {
        "requirements": password_strength.get_requirements(settings),
        "min_length": settings.password_min_length,
        "max_length": 128,
    }


@router.post("/password/change/")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allowed_scopes=["password_change_only"])),  # noqa: B008
):
    user = auth.user
    if not user.password_hash:
        raise TenxyteAPIError(
            "Passwordless accounts must set their first password via the dedicated endpoint",
            code="PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD",
            status_code=400,
        )

    _raise_if_weak(body.new_password, settings)

    if body.current_password:
        if not verify_password(body.current_password, user.password_hash):
            raise TenxyteAPIError("Current password is incorrect", code="INVALID_PASSWORD", status_code=400)
    elif body.otp_code:
        # OTP-based reauth isn't implemented yet (reuses a login-type OTP in Django, out of this
        # endpoint's own scope — see module docstring) — treated as "no supported proof
        # provided", not silently accepted.
        raise TenxyteAPIError(
            "Current password or a valid OTP code is required", code="REAUTH_REQUIRED", status_code=400
        )
    else:
        raise TenxyteAPIError(
            "Current password or a valid OTP code is required", code="REAUTH_REQUIRED", status_code=400
        )

    breach_ok, breach_error = await breach_check.check_password_async(body.new_password, settings)
    if not breach_ok:
        raise TenxyteAPIError(breach_error, code="PASSWORD_BREACHED", status_code=400)

    strength_result = password_strength.validate(body.new_password, settings)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user.password_hash = hash_password(body.new_password, rounds=settings.bcrypt_rounds)
    await user_repo.update(user)

    # The current access token itself isn't blacklisted here — matching the Django_Adapter's
    # ChangePasswordView, which only revokes refresh tokens, not the token the request used.
    sessions_revoked = await revoke_all_for_user(session, user.id)

    response_data = {
        "message": "Password changed successfully",
        "password_strength": strength_result.strength,
        "sessions_revoked": sessions_revoked,
    }

    # Force password change: clear the flag and issue a full-scope token pair
    # (feature: force_password_change_on_first_login) — mirrors ChangePasswordView.
    user_db = await session.get(UserDB, user.id)
    if user_db is not None and user_db.must_change_password:
        await update_user_async(session, user_db, {"must_change_password": False})
        # Upgrade to full-scope only if the caller actually needed to (i.e. presented a
        # Restricted_Password_Token), exactly as TwoFactorConfirmView does after the 2FA bootstrap.
        if auth.scope == "password_change_only":
            app_id = _resolved_application_id(request)
            token_pair = jwt_service.generate_new_token_pair(user_id=user.id, application_id=app_id)
            response_data["access_token"] = token_pair.access_token
            response_data["refresh_token"] = token_pair.refresh_token
            response_data["token_type"] = "Bearer"
            response_data["expires_in"] = token_pair.expires_in

    return response_data


async def _lookup_by_email_or_phone(
    user_repo: SQLAlchemyAsyncUserRepository,
    email: str | None,
    phone_country_code: str | None,
    phone_number: str | None,
):
    if email:
        return await user_repo.get_by_email(email)
    if phone_country_code and phone_number:
        return await user_repo.get_by_phone(phone_country_code, phone_number)
    return None


@router.post("/password/reset/request/")
async def password_reset_request(
    body: PasswordResetRequestRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    if not body.email and not (body.phone_country_code and body.phone_number):
        raise TenxyteAPIError(
            "Validation error",
            code="VALIDATION_ERROR",
            status_code=400,
            details={"non_field_errors": ["Email or phone number is required"]},
        )

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user = await _lookup_by_email_or_phone(user_repo, body.email, body.phone_country_code, body.phone_number)

    if user is None:
        # Anti-enumeration: Django returns a genuinely empty 200 body (no JSON) here — not
        # `{"message": ...}` — so the two cases aren't byte-identical, only status-code-identical
        # and equally silent about whether the account exists.
        return Response(status_code=200)

    channel = "email" if user.email else "sms"
    row, raw_code = await otp_service.generate_otp(session, user.id, "password_reset", settings)
    logger.info("OTP delivery (no real backend wired in): %s code=%s user_id=%s", channel, raw_code, user.id)

    return {
        "message": "Password reset code sent",
        "otp_id": row.id,
        "expires_at": row.expires_at.isoformat(),
        "channel": channel,
    }


@router.post("/password/reset/confirm/")
async def password_reset_confirm(
    body: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    _raise_if_weak(body.new_password, settings)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user = await _lookup_by_email_or_phone(user_repo, body.email, body.phone_country_code, body.phone_number)
    if user is None:
        # Same RESET_FAILED code as a bad/expired OTP below — a nonexistent account and a wrong
        # code are indistinguishable to the caller, matching Django's real (if accidental)
        # anti-enumeration-adjacent behavior here.
        raise TenxyteAPIError("Invalid reset request", code="RESET_FAILED", status_code=400)

    result = await otp_service.verify_otp(session, user.id, "password_reset", body.otp_code)
    if not result.success:
        raise TenxyteAPIError(result.error, code="RESET_FAILED", status_code=400)

    # Deliberately non-blocking (see module docstring) — Django's PasswordResetConfirmView never
    # hard-rejects a breached password here, only flags it in the response.
    breach_ok, _breach_error = await breach_check.check_password_async(body.new_password, settings)

    user.password_hash = hash_password(body.new_password, rounds=settings.bcrypt_rounds)
    await user_repo.update(user)

    tokens_revoked = await revoke_all_for_user(session, user.id)

    return {
        "message": "Password reset successful",
        "tokens_revoked": tokens_revoked,
        "password_safe": breach_ok,
    }


@router.post("/password/set-initial/")
async def set_initial_password(
    body: SetInitialPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allowed_scopes=["password_change_only"])),  # noqa: B008
):
    user = auth.user
    if user.password_hash:
        raise TenxyteAPIError(
            "Account already has a usable password. Use /password/change/ instead.",
            code="ALREADY_HAS_PASSWORD",
            status_code=400,
        )

    _raise_if_weak(body.new_password, settings)

    result = await otp_service.verify_otp(session, user.id, "login", body.otp_code)
    if not result.success:
        code = "OTP_REQUIRED" if result.error == "No login code found" else "OTP_INVALID"
        raise TenxyteAPIError(result.error, code=code, status_code=400)

    breach_ok, breach_error = await breach_check.check_password_async(body.new_password, settings)
    if not breach_ok:
        raise TenxyteAPIError(breach_error, code="PASSWORD_BREACHED", status_code=400)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user.password_hash = hash_password(body.new_password, rounds=settings.bcrypt_rounds)
    await user_repo.update(user)

    response_data = {"message": "Password set successfully"}

    # Force password change: clear the flag and issue a full-scope token pair
    # (feature: force_password_change_on_first_login) — mirrors SetInitialPasswordView.
    user_db = await session.get(UserDB, user.id)
    if user_db is not None and user_db.must_change_password:
        await update_user_async(session, user_db, {"must_change_password": False})
        if auth.scope == "password_change_only":
            app_id = _resolved_application_id(request)
            token_pair = jwt_service.generate_new_token_pair(user_id=user.id, application_id=app_id)
            response_data["access_token"] = token_pair.access_token
            response_data["refresh_token"] = token_pair.refresh_token
            response_data["token_type"] = "Bearer"
            response_data["expires_in"] = token_pair.expires_in

    return response_data
