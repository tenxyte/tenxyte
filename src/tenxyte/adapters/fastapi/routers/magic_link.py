"""
Parity_Group C — magic-link (passwordless email) authentication (spec z_aud_3, task 7.1):
magic-link/request, magic-link/verify. Contract extracted from the Django_Adapter's
`views/magic_link_views.py`.

Unlike `otp/*`/`login/otp/*` (both built from scratch — no Django Core equivalent existed, see
`otp_service.py`'s module docstring), `core.magic_link_service.MagicLinkService` already existed
and was confirmed 100% framework-agnostic and async-complete (no Django imports anywhere in the
file) — this only needed a Reference_Stack repository (`magic_link_repo.py`) plumbed in.

Two behaviors intentionally preserved exactly as Django's real (not just documented) code, even
where they look like inconsistencies:
- **`verify/`'s response uses `access`/`refresh` field names**, not `access_token`/`refresh_token`
  like every other login-shaped endpoint in this adapter — `MagicLinkVerifyView.get` genuinely
  returns those names; this is a real quirk in the Django_Adapter itself, not a typo to "fix" here.
- **`application_id` is never passed** to either `request_magic_link`/`verify_magic_link` by the
  Django view, despite `MagicLinkService` accepting one — tokens are always created and verified
  with `application_id=None`, so the service's own app-mismatch check is dead code in practice.
  Replicated as-is rather than "improved".

`Settings.magic_link_enabled` defaults `True` (unlike `login/otp`'s default-off
`otp_login_enabled`) — matches `MagicLinkService.__init__`'s own `getattr(..., True)` default.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from tenxyte.adapters.fastapi.deps import (
    get_cache_service,
    get_db_session,
    get_email_service,
    get_jwt_service,
    get_settings,
)
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.magic_link_repo import SQLAlchemyMagicLinkRepository, SQLAlchemyUserLookup
from tenxyte.adapters.fastapi.refresh_tokens import issue_refresh_token as _issue_refresh_token
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.schemas import MagicLinkRequestRequest
from tenxyte.adapters.fastapi.serialization import serialize_user
from tenxyte.adapters.fastapi.throttling import _get_client_ip
from tenxyte.core.cache_service import CacheService
from tenxyte.core.email_service import ConsoleEmailService, EmailService
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.magic_link_service import MagicLinkService
from tenxyte.core.settings import Settings
from tenxyte.device_info import build_device_info_from_user_agent

router = APIRouter()


def _device_info(request: Request) -> str:
    user_agent = request.headers.get("User-Agent", "")
    return build_device_info_from_user_agent(user_agent) if user_agent else ""


@router.post("/magic-link/request/")
async def magic_link_request(
    body: MagicLinkRequestRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
    email_service: EmailService = Depends(get_email_service),  # noqa: B008
):
    email = body.email.strip().lower()
    validation_url = body.validation_url.strip()

    if not email:
        raise TenxyteAPIError("Email is required", code="EMAIL_REQUIRED", status_code=400)
    if not validation_url:
        raise TenxyteAPIError("Validation URL is required", code="VALIDATION_URL_REQUIRED", status_code=400)

    user_lookup = SQLAlchemyUserLookup(session, cache_service)
    magic_link_repo = SQLAlchemyMagicLinkRepository(session)
    service = MagicLinkService(
        settings=settings, repo=magic_link_repo, user_lookup=user_lookup, email_service=email_service
    )

    success, _error = await service.request_magic_link_async(
        email=email,
        validation_url=validation_url,
        ip_address=_get_client_ip(request),
        device_info=_device_info(request),
    )

    if not success:
        raise TenxyteAPIError("Service unavailable", code="SERVICE_UNAVAILABLE", status_code=503)

    # Always 200 even when the email doesn't exist (anti-enumeration) — same as the
    # Django_Adapter.
    return {"message": "If this email is registered, a magic link has been sent."}


@router.get("/magic-link/verify/")
async def magic_link_verify(
    request: Request,
    token: str = "",
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    cache_service: CacheService = Depends(get_cache_service),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
):
    token = token.strip()
    if not token:
        raise TenxyteAPIError("Token is required", code="TOKEN_REQUIRED", status_code=400)

    user_lookup = SQLAlchemyUserLookup(session, cache_service)
    magic_link_repo = SQLAlchemyMagicLinkRepository(session)
    # email_service is never used on this path (only request/ sends anything) — MagicLinkService's
    # constructor requires one regardless, so a bare ConsoleEmailService is the cheapest valid
    # instance rather than threading the real dependency through for no reason.
    service = MagicLinkService(
        settings=settings, repo=magic_link_repo, user_lookup=user_lookup, email_service=ConsoleEmailService()
    )

    auth_result = await service.verify_magic_link_async(
        token=token, ip_address=_get_client_ip(request), device_info=_device_info(request)
    )

    if not auth_result.success:
        raise TenxyteAPIError(auth_result.error, code="MAGIC_LINK_INVALID", status_code=401)

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user = await user_repo.get_by_id(auth_result.user_id)

    app_id = "default"
    access_token, _jti, _expires_at = jwt_service.generate_access_token(auth_result.user_id, application_id=app_id)
    refresh_token = await _issue_refresh_token(
        session, auth_result.user_id, lifetime_seconds=settings.jwt_refresh_token_lifetime
    )
    if user is not None:
        await user_repo.update_last_login(auth_result.user_id, datetime.now(timezone.utc))

    response_data = {
        # Deliberately `access`/`refresh`, not `access_token`/`refresh_token` — see module
        # docstring.
        "access": access_token,
        "refresh": refresh_token,
        "user": serialize_user(user) if user is not None else {"id": auth_result.user_id},
        "message": "Magic link verified successfully",
        "session_id": None,
        "device_id": None,
    }
    response = JSONResponse(status_code=200, content=response_data)
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
