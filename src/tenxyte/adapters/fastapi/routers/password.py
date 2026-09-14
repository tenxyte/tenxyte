"""
Parity_Group B — password management (spec z_aud_3, task 6.1): password/strength,
password/requirements, password/change. Contract extracted from the Django_Adapter's
`views/password_views.py` and `serializers/password_serializers.py`.

Deliberately out of scope for this pass (documented rather than silently skipped), all three
blocked on the same missing prerequisite — the Reference_Stack has no OTP-code storage yet (email/
SMS one-time codes, distinct from `totp_storage.py`'s authenticator-app TOTP secrets); that's Group
C's job (task 7.1: otp/request, otp/verify/*, magic-link/*):

- **`password/reset/request/` and `password/reset/confirm/`** — entirely OTP-driven in Django
  (`OTPService.generate_password_reset_otp`/`verify_password_reset_otp`); no password-reset flow
  is possible without somewhere to store and verify the code.
- **`password/set-initial/`** — mandates a login OTP as proof (no password exists yet to check),
  same missing prerequisite.
- **OTP-based reauth on `password/change/`** — `ReauthService.verify()` accepts `current_password`
  OR `otp_code`; only the `current_password` path is implemented here. A request with only
  `otp_code` and no `current_password` gets `REAUTH_REQUIRED`, same as Django's "neither provided"
  case — an honest signal, not a silent accept, until OTP storage exists.

Also out of scope, matching the Django_Adapter's own actual behavior (not a gap — porting these
would be a parity BREAK, not a fix): password-history/reuse checking (Django defines a
`PasswordHistory` model but never calls it — `PASSWORD_REUSED` is documented but unreachable) and
the `must_change_password`/scope-upgrade branch on a successful change (dead code today: the
feature that would ever issue a `password_change_only` token defaults off — see routers/auth.py's
module docstring).

Password-strength validation (`password_strength.py`) and the breach check (`breach_check.py`) are
each a framework-agnostic *reimplementation*, not a reuse of `tenxyte.validators`/
`tenxyte.services.breach_check_service` — both of those import `tenxyte.conf`, which imports
`django.conf.settings` at module load time, making them unimportable from a Django-less FastAPI
process. Structurally identical contract (score/strength/is_valid/errors/requirements; breach
hard-rejects the same way), English wording rather than Django's French validator strings — no
reasonable API contract requires clients to string-match a validation message, only its shape.
"""

from __future__ import annotations

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends
from tenxyte.adapters.fastapi import breach_check, password_strength
from tenxyte.adapters.fastapi.deps import get_db_session, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.refresh_tokens import revoke_all_for_user
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.schemas import ChangePasswordRequest, PasswordStrengthRequest
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.core.settings import Settings

router = APIRouter()


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

    if body.current_password:
        if not bcrypt.checkpw(body.current_password.encode("utf-8"), user.password_hash.encode("utf-8")):
            raise TenxyteAPIError("Current password is incorrect", code="INVALID_PASSWORD", status_code=400)
    elif body.otp_code:
        # OTP-based reauth isn't implemented yet (no OTP storage in the Reference_Stack — see
        # module docstring) — treated as "no supported proof provided", not silently accepted.
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
