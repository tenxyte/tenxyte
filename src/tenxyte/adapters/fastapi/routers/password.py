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

Also out of scope, matching the Django_Adapter's own actual behavior (not a gap — porting these
would be a parity BREAK, not a fix): password-history/reuse checking (Django defines a
`PasswordHistory` model but never calls it — `PASSWORD_REUSED` is documented but unreachable) and
the `must_change_password`/scope-upgrade branch on a successful change/reset (dead code today: the
feature that would ever issue a `password_change_only` token defaults off — see routers/auth.py's
module docstring).

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

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Response
from tenxyte.adapters.fastapi import breach_check, otp_service, password_strength
from tenxyte.adapters.fastapi.deps import get_db_session, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
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
from tenxyte.core.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter()


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
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
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
        if not bcrypt.checkpw(body.current_password.encode("utf-8"), user.password_hash.encode("utf-8")):
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
    hashed = bcrypt.hashpw(body.new_password.encode("utf-8"), bcrypt.gensalt(rounds=settings.bcrypt_rounds))
    user.password_hash = hashed.decode("utf-8")
    await user_repo.update(user)

    # The current access token itself isn't blacklisted here — matching the Django_Adapter's
    # ChangePasswordView, which only revokes refresh tokens, not the token the request used.
    sessions_revoked = await revoke_all_for_user(session, user.id)

    return {
        "message": "Password changed successfully",
        "password_strength": strength_result.strength,
        "sessions_revoked": sessions_revoked,
    }


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

    hashed = bcrypt.hashpw(body.new_password.encode("utf-8"), bcrypt.gensalt(rounds=settings.bcrypt_rounds))
    user.password_hash = hashed.decode("utf-8")
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
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
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
    hashed = bcrypt.hashpw(body.new_password.encode("utf-8"), bcrypt.gensalt(rounds=settings.bcrypt_rounds))
    user.password_hash = hashed.decode("utf-8")
    await user_repo.update(user)

    return {"message": "Password set successfully"}
