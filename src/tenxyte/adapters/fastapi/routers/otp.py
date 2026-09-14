"""
Parity_Group C — OTP verification (spec z_aud_3, task 7.1): otp/request, otp/verify/email,
otp/verify/phone. Contract extracted from the Django_Adapter's `views/otp_views.py`. These three
prove out the Reference_Stack's new OTP-code storage (`otp_service.py`/`OTPCodeDB`) — the same
infrastructure `login/otp/*`, `magic-link/*` (separate mechanism, see routers/magic_link.py), and
Wave B's `password/reset/*`/`password/set-initial/` all build on.

Delivery (`send_email_otp`/`send_phone_otp` in Django) is fire-and-forget there too — the view
never checks whether sending actually succeeded, it always returns 200 once the code is generated.
This port keeps that contract but has no real email/SMS backend wired in (none exists in the
Reference_Stack yet); delivery is a logged no-op, which is observably identical to the Django
behavior from the caller's perspective (both return 200 regardless of whether delivery worked).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends
from tenxyte.adapters.fastapi import otp_service
from tenxyte.adapters.fastapi.deps import get_db_session, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.schemas import RequestOTPRequest, VerifyOTPRequest
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.core.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not local:
        return email
    return f"{local[0]}{'*' * max(len(local) - 1, 0)}@{domain}"


def _mask_phone(phone_number: str) -> str:
    if len(phone_number) <= 4:
        return "*" * len(phone_number)
    return "*" * (len(phone_number) - 4) + phone_number[-4:]


@router.post("/otp/request/")
async def request_otp(
    body: RequestOTPRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    user = auth.user
    if body.otp_type == "email":
        if not user.email:
            raise TenxyteAPIError("No email address on account", code="NO_EMAIL", status_code=400)
        row, raw_code = await otp_service.generate_otp(session, user.id, "email_verification", settings)
        logger.info("OTP delivery (no real backend wired in): email code=%s to=%s", raw_code, user.email)
        masked_recipient = _mask_email(user.email)
    else:
        phone_number = (user.metadata or {}).get("phone_number")
        if not phone_number:
            raise TenxyteAPIError("No phone number on account", code="NO_PHONE", status_code=400)
        row, raw_code = await otp_service.generate_otp(session, user.id, "phone_verification", settings)
        logger.info("OTP delivery (no real backend wired in): sms code=%s to=%s", raw_code, phone_number)
        masked_recipient = _mask_phone(phone_number)

    return {
        "message": "OTP sent",
        "otp_id": row.id,
        "expires_at": row.expires_at.isoformat(),
        "channel": body.otp_type,
        "masked_recipient": masked_recipient,
    }


@router.post("/otp/verify/email/")
async def verify_email_otp(
    body: VerifyOTPRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    result = await otp_service.verify_otp(session, auth.user.id, "email_verification", body.code)
    if not result.success:
        raise TenxyteAPIError(result.error, code="OTP_VERIFICATION_FAILED", status_code=400)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    await user_repo.verify_email(auth.user.id)

    return {
        "message": "Email verified successfully",
        "email_verified": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/otp/verify/phone/")
async def verify_phone_otp(
    body: VerifyOTPRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    result = await otp_service.verify_otp(session, auth.user.id, "phone_verification", body.code)
    if not result.success:
        raise TenxyteAPIError(result.error, code="OTP_VERIFICATION_FAILED", status_code=400)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    await user_repo.verify_phone(auth.user.id)

    metadata = auth.user.metadata or {}
    phone_country_code = metadata.get("phone_country_code")
    phone_number = metadata.get("phone_number")

    return {
        "message": "Phone verified successfully",
        "phone_verified": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "phone_number": f"+{phone_country_code}{phone_number}" if phone_country_code else phone_number,
    }
