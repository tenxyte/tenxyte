"""
Parity_Group G chunk 3/4 (spec z_aud_3, task 12.1) — GDPR user endpoints: `request-account-
deletion/`, `confirm-account-deletion/`, `cancel-account-deletion/`, `account-deletion-status/`,
`export-user-data/`. Contract extracted from `views/account_deletion_views.py`, read in full — see
`gdpr_service.py`'s module docstring for the two real bugs fixed (export permissions crash, 2FA
gate crash) and the one replicated exactly (login_attempts/applications always empty).

**Auth**: all 4 endpoints except `confirm-account-deletion/` require `IsAuthenticated` only (not
Django's `@require_jwt` decorator, which most other endpoints use) — mirrored here with
`require_jwt(allow_any_scope=True)`, same convention `routers/auth.py`'s `MeView` already
established for the one other Django endpoint that authenticates this way.
`confirm-account-deletion/` has no `@permission_classes` at all in Django (a user confirms via an
emailed link, not necessarily logged in) — no auth dependency here either.

**Every failure response here is `{"error": <message>}` with no `code` field**, except the
`REAUTH_REQUIRED` pre-check (done in this router, before calling the service, exactly where
Django's view does it) and `export-user-data/`'s reauth failure (which does carry
`reauth.error_code`) — see `gdpr_service.py`'s module docstring for why these two are different
from every other failure path here.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import gdpr_service
from tenxyte.adapters.fastapi.deps import get_db_session, get_settings, get_totp_service
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.schemas import (
    CancelAccountDeletionRequest,
    ConfirmAccountDeletionRequest,
    ExportUserDataRequest,
    RequestAccountDeletionRequest,
)
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.adapters.fastapi.throttling import _get_client_ip
from tenxyte.core.settings import Settings
from tenxyte.core.totp_service import TOTPService

router = APIRouter()


@router.post("/request-account-deletion/", status_code=201)
async def request_account_deletion(
    body: RequestAccountDeletionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    totp_service: TOTPService = Depends(get_totp_service),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allow_any_scope=True)),  # noqa: B008
):
    if not body.password and not body.reauth_otp_code:
        raise TenxyteAPIError(
            "Current password or a valid OTP code is required", code="REAUTH_REQUIRED", status_code=400
        )

    success, data, error = await gdpr_service.request_deletion_async(
        session,
        auth.user,
        password=body.password,
        otp_code=body.otp_code,
        reauth_otp_code=body.reauth_otp_code,
        reason=body.reason,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent", ""),
        settings=settings,
        totp_service=totp_service,
    )
    if not success:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return data


@router.post("/confirm-account-deletion/")
async def confirm_account_deletion(
    body: ConfirmAccountDeletionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    success, data, error = await gdpr_service.confirm_deletion_async(
        session, token=body.token, ip_address=_get_client_ip(request), settings=settings
    )
    if not success:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return data


@router.post("/cancel-account-deletion/")
async def cancel_account_deletion(
    body: CancelAccountDeletionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allow_any_scope=True)),  # noqa: B008
):
    if not body.password and not body.otp_code:
        raise TenxyteAPIError(
            "Current password or a valid OTP code is required", code="REAUTH_REQUIRED", status_code=400
        )

    success, data, error = await gdpr_service.cancel_deletion_async(
        session, auth.user, password=body.password, otp_code=body.otp_code, ip_address=_get_client_ip(request)
    )
    if not success:
        raise TenxyteAPIError(error, code=None, status_code=400)
    return data


@router.get("/account-deletion-status/")
async def account_deletion_status(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allow_any_scope=True)),  # noqa: B008
):
    return await gdpr_service.get_user_requests_async(session, auth.user.id)


@router.post("/export-user-data/")
async def export_user_data(
    body: ExportUserDataRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt(allow_any_scope=True)),  # noqa: B008
):
    if not body.password and not body.otp_code:
        raise TenxyteAPIError(
            "Current password or a valid OTP code is required", code="REAUTH_REQUIRED", status_code=400
        )

    reauth = await gdpr_service.verify_reauth_async(auth.user, password=body.password, otp_code=body.otp_code)
    if not reauth.ok:
        raise TenxyteAPIError(reauth.error_message, code=reauth.error_code, status_code=400)

    data = await gdpr_service.export_user_data_async(session, auth.user, ip_address=_get_client_ip(request))
    return data
