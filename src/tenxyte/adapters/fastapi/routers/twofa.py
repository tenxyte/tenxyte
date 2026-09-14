"""
Parity_Group C — 2FA enrollment (spec z_aud_3, task 7.1): 2fa/status, 2fa/setup, 2fa/confirm,
2fa/disable, 2fa/backup-codes. Contract extracted from the Django_Adapter's `views/twofa_views.py`.
Distinct from the login-time 2FA verification already ported in Wave A (`routers/auth.py`'s
`_login()`, which calls `TOTPService.verify_2fa_async`) — these endpoints manage *enrollment*
itself (turning 2FA on/off, rotating backup codes).

Django writes both `User.is_2fa_enabled` (via `TOTPStorage.enable_2fa`/`disable_2fa`) and
`User.mfa_type` (via a separate `user_repo.enable_mfa`/`disable_mfa` call) on confirm/disable —
two flags kept in sync by two write paths. The Reference_Stack only has one signal, `mfa_type`
(`none` vs `totp`), so `SQLAlchemyTOTPStorage.enable_2fa_async`/`disable_2fa_async` already call
`SQLAlchemyAsyncUserRepository.enable_mfa`/`disable_mfa` internally (see `totp_storage.py`) — no
second write is needed here, unlike Django's two-call sequence.

**Reauth on `2fa/disable/`** is password-only here — Django's `ReauthService.verify()` also
accepts a `login`-type OTP code, but (same reasoning as `password/change/`, see
`routers/password.py`'s module docstring) plumbing that through would mean issuing login OTPs
outside the login flow itself. An `otp_code`-only request gets `REAUTH_REQUIRED`, not a silent
accept.
"""

from __future__ import annotations

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi.deps import get_db_session, get_jwt_service, get_totp_service
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.schemas import (
    TwoFactorBackupCodesRequest,
    TwoFactorConfirmRequest,
    TwoFactorDisableRequest,
)
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.adapters.fastapi.totp_storage import SQLAlchemyTOTPStorage
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.totp_service import TOTPService

router = APIRouter()


@router.get("/2fa/status/")
async def twofa_status(auth: AuthContext = Depends(require_jwt())):  # noqa: B008
    user = auth.user
    backup_codes = list((user.metadata or {}).get("backup_codes", []))
    return {"is_enabled": user.mfa_type.value != "none", "backup_codes_remaining": len(backup_codes)}


@router.post("/2fa/setup/")
async def twofa_setup(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allowed_scopes=["2fa_setup_only"])),  # noqa: B008
):
    user = auth.user
    if user.mfa_type.value != "none":
        raise TenxyteAPIError("2FA is already enabled", code="2FA_ALREADY_ENABLED", status_code=400)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    storage = SQLAlchemyTOTPStorage(user_repo)
    setup_result = await totp_service.setup_2fa_async(user_id=user.id, email=user.email or user.id, storage=storage)

    return {
        "message": "Scan the QR code with your authenticator app, then confirm with a code.",
        "secret": setup_result.secret,
        "qr_code": setup_result.qr_code,
        "provisioning_uri": setup_result.provisioning_uri,
        "backup_codes": setup_result.backup_codes,
        "warning": "Save the backup codes securely. They will not be shown again.",
    }


def _resolved_application_id(request: Request) -> str:
    application = getattr(request.state, "application", None)
    return str(application.id) if application is not None else "default"


@router.post("/2fa/confirm/")
async def twofa_confirm(
    body: TwoFactorConfirmRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allowed_scopes=["2fa_setup_only"])),  # noqa: B008
):
    if not body.code:
        raise TenxyteAPIError("Code is required", code="CODE_REQUIRED", status_code=400)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    storage = SQLAlchemyTOTPStorage(user_repo)
    is_valid, error_message = await totp_service.confirm_2fa_setup_async(
        user_id=auth.user.id, code=body.code, storage=storage
    )
    if not is_valid:
        raise TenxyteAPIError(error_message or "Invalid TOTP code", code="INVALID_CODE", status_code=400)

    response_data: dict = {"message": "2FA enabled successfully", "is_enabled": True}

    if auth.scope == "2fa_setup_only":
        app_id = _resolved_application_id(request)
        pair = jwt_service.generate_new_token_pair(user_id=auth.user.id, application_id=app_id)
        response_data.update(
            {
                "access_token": pair.access_token,
                "refresh_token": pair.refresh_token,
                "token_type": "Bearer",
                "expires_in": pair.expires_in,
            }
        )
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            await jwt_service.blacklist_token_async(
                auth_header[7:], user_id=auth.user.id, reason="2fa_bootstrap_completed"
            )

    return response_data


@router.post("/2fa/disable/")
async def twofa_disable(
    body: TwoFactorDisableRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    if not body.code:
        raise TenxyteAPIError("Code is required", code="CODE_REQUIRED", status_code=400)

    if body.password:
        if not auth.user.password_hash or not bcrypt.checkpw(
            body.password.encode("utf-8"), auth.user.password_hash.encode("utf-8")
        ):
            raise TenxyteAPIError("Current password is incorrect", code="INVALID_PASSWORD", status_code=400)
    elif body.otp_code:
        # OTP-based reauth isn't implemented yet (see module docstring) — treated as "no
        # supported proof provided", not silently accepted.
        raise TenxyteAPIError(
            "Current password or a valid OTP code is required", code="REAUTH_REQUIRED", status_code=400
        )
    else:
        raise TenxyteAPIError(
            "Current password or a valid OTP code is required", code="REAUTH_REQUIRED", status_code=400
        )

    user_repo = SQLAlchemyAsyncUserRepository(session)
    storage = SQLAlchemyTOTPStorage(user_repo)
    is_valid, error_message = await totp_service.disable_2fa_async(
        user_id=auth.user.id, code=body.code, storage=storage
    )
    if not is_valid:
        raise TenxyteAPIError(error_message or "Invalid code", code="INVALID_CODE", status_code=400)

    return {"message": "2FA disabled successfully", "is_enabled": False}


@router.post("/2fa/backup-codes/")
async def twofa_backup_codes(
    body: TwoFactorBackupCodesRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    if not body.code:
        raise TenxyteAPIError("TOTP code is required", code="CODE_REQUIRED", status_code=400)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    storage = SQLAlchemyTOTPStorage(user_repo)
    is_valid, plain_codes, error_message = await totp_service.regenerate_backup_codes_async(
        user_id=auth.user.id, code=body.code, storage=storage
    )
    if not is_valid:
        raise TenxyteAPIError(error_message or "Invalid TOTP code", code="INVALID_CODE", status_code=400)

    return {
        "message": "Backup codes regenerated",
        "backup_codes": plain_codes,
        "warning": "Save these codes securely. They will not be shown again.",
    }
