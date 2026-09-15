"""
Parity_Group G — Social Auth (spec z_aud_3, Wave G chunk 2/4, task 12.1): `POST social/
{provider}/`, `GET social/{provider}/callback/` — 2 of Group G's 17 real endpoints (17/17
cumulative once GDPR user/admin ship). Contract extracted from `views/social_auth_views.py`
(`SocialAuthView.post`, `SocialAuthCallbackView.get`), read in full. See `social_auth_service.py`'s
module docstring for the account-fusion security logic, the JWKS-based id_token verification
replacing `google-auth`, and what's deliberately not wired yet (default-organization creation).

**Response shape genuinely differs between the two endpoints** — `POST social/{provider}/` strips
`device_summary` and adds `message`; `GET social/{provider}/callback/` keeps `device_summary` and
never adds `message`. Both add `provider`. Not an inconsistency to "fix" — Django's own two views
do exactly this, independently, and this router reproduces each view's own post-processing.

Rate limiting (`LoginThrottle`/`LoginHourlyThrottle` on `SocialAuthView` in Django) is not
replicated — no other Wave A-F endpoint in this port implements Django's throttle classes either
(see `throttling.py`'s own scope), so this isn't a new gap specific to Wave G.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import social_auth_service
from tenxyte.adapters.fastapi.deps import get_db_session, get_jwt_service, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.schemas import SocialAuthRequest
from tenxyte.adapters.fastapi.throttling import _get_client_ip
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings
from tenxyte.device_info import build_device_info_from_user_agent

router = APIRouter()

_SUPPORTED_PROVIDERS = list(social_auth_service.SUPPORTED_PROVIDERS)


def _device_info(request: Request, explicit: str = "") -> str:
    if explicit:
        return explicit
    return build_device_info_from_user_agent(request.headers.get("User-Agent", ""))


async def _resolve_user_data(
    provider_name: str,
    *,
    access_token: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    id_token: str,
    settings: Settings,
) -> tuple[dict | None, str | None, str | None]:
    """Mirrors `SocialAuthView.post`'s single if/elif/elif/else branch exactly — order matters
    (`access_token` checked first, then `code`, then `id_token`, else a `MISSING_CREDENTIALS`
    error). Returns `(user_data, error_message, error_code)` — `error_code` is `None` alongside a
    `None` `user_data` for the "could not retrieve user data" case, which the caller maps to
    `PROVIDER_AUTH_FAILED` itself (matching the view, where that 401 is raised outside this
    branch, after it, checking `if not user_data`)."""
    if access_token:
        return await social_auth_service.get_user_info_async(provider_name, access_token, settings), None, None

    if code:
        if not redirect_uri:
            return None, "redirect_uri is required with code", "REDIRECT_URI_REQUIRED"
        tokens = await social_auth_service.exchange_code_async(
            provider_name, code, redirect_uri, code_verifier or None, settings
        )
        if tokens and provider_name == "apple" and tokens.get("id_token"):
            user_data = await social_auth_service.verify_id_token_async(provider_name, tokens["id_token"], settings)
            return user_data, None, None
        if tokens and tokens.get("access_token"):
            user_data = await social_auth_service.get_user_info_async(provider_name, tokens["access_token"], settings)
            return user_data, None, None
        return None, None, None

    if id_token and provider_name in ("google", "apple"):
        return await social_auth_service.verify_id_token_async(provider_name, id_token, settings), None, None

    return (
        None,
        "Provide access_token, code+redirect_uri, or id_token (Google/Apple only).",
        "MISSING_CREDENTIALS",
    )


def _merge_apple_first_auth_payload(user_data: dict, apple_user_payload: dict | None) -> None:
    """Mirrors the view's Apple `First_Auth_User_Payload` merge exactly — only present on the
    very first authorization, never in the id_token itself."""
    if not isinstance(apple_user_payload, dict):
        return
    name = apple_user_payload.get("name") or {}
    if not isinstance(name, dict):
        return
    if name.get("firstName"):
        user_data["first_name"] = name["firstName"]
    if name.get("lastName"):
        user_data["last_name"] = name["lastName"]


@router.post("/social/{provider}/")
async def social_auth(
    provider: str,
    body: SocialAuthRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
):
    provider_name = provider.lower()
    if not social_auth_service.is_provider_supported(provider_name, settings):
        raise TenxyteAPIError(
            f"Provider '{provider_name}' is not supported or not enabled.",
            code="PROVIDER_NOT_SUPPORTED",
            status_code=400,
            extra={"supported_providers": _SUPPORTED_PROVIDERS},
        )

    ip_address = _get_client_ip(request)
    device_info = _device_info(request, body.device_info)

    user_data, resolve_error, resolve_error_code = await _resolve_user_data(
        provider_name,
        access_token=body.access_token,
        code=body.code,
        redirect_uri=body.redirect_uri,
        code_verifier=body.code_verifier,
        id_token=body.id_token,
        settings=settings,
    )
    if resolve_error is not None:
        raise TenxyteAPIError(resolve_error, code=resolve_error_code, status_code=400)
    if not user_data:
        raise TenxyteAPIError(
            f"Could not retrieve user data from {provider_name}.", code="PROVIDER_AUTH_FAILED", status_code=401
        )

    if provider_name == "apple":
        _merge_apple_first_auth_payload(user_data, body.user)

    data, auth_error = await social_auth_service.authenticate_async(
        session,
        provider_name=provider_name,
        user_data=user_data,
        ip_address=ip_address,
        device_info=device_info,
        settings=settings,
        jwt_service=jwt_service,
    )
    if auth_error is not None:
        raise TenxyteAPIError(auth_error, code="SOCIAL_AUTH_FAILED", status_code=401)

    data["provider"] = provider_name
    data["message"] = "Authentication successful"
    data.pop("device_summary", None)
    return data


@router.get("/social/{provider}/callback/")
async def social_auth_callback(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
):
    provider_name = provider.lower()
    if not social_auth_service.is_provider_supported(provider_name, settings):
        raise TenxyteAPIError(
            f"Provider '{provider_name}' is not supported.", code="PROVIDER_NOT_SUPPORTED", status_code=400
        )

    code = request.query_params.get("code")
    redirect_uri = request.query_params.get("redirect_uri")

    if not code:
        raise TenxyteAPIError("Authorization code is required", code="MISSING_CODE", status_code=400)
    if not redirect_uri:
        raise TenxyteAPIError("redirect_uri is required", code="MISSING_REDIRECT_URI", status_code=400)

    tokens = await social_auth_service.exchange_code_async(provider_name, code, redirect_uri, None, settings)
    token_present = tokens and (tokens.get("access_token") or (provider_name == "apple" and tokens.get("id_token")))
    if not token_present:
        raise TenxyteAPIError("Failed to exchange authorization code", code="CODE_EXCHANGE_FAILED", status_code=401)

    if provider_name == "apple":
        user_data = await social_auth_service.verify_id_token_async(provider_name, tokens["id_token"], settings)
    else:
        user_data = await social_auth_service.get_user_info_async(provider_name, tokens["access_token"], settings)
    if not user_data:
        raise TenxyteAPIError(
            f"Could not retrieve user data from {provider_name}", code="PROVIDER_AUTH_FAILED", status_code=401
        )

    ip_address = _get_client_ip(request)
    device_info = _device_info(request)

    data, auth_error = await social_auth_service.authenticate_async(
        session,
        provider_name=provider_name,
        user_data=user_data,
        ip_address=ip_address,
        device_info=device_info,
        settings=settings,
        jwt_service=jwt_service,
    )
    if auth_error is not None:
        raise TenxyteAPIError(auth_error, code="SOCIAL_AUTH_FAILED", status_code=401)

    data["provider"] = provider_name
    return data
