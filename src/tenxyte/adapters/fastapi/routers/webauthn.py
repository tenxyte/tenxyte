"""
Parity_Group G — WebAuthn/Passkeys (spec z_aud_3, Wave G, task 12.1): register/begin,
register/complete, authenticate/begin, authenticate/complete, credentials (list), credentials/
{id} (delete). Contract extracted from `views/webauthn_views.py`. See `webauthn_service.py`'s
module docstring for the two real Django bugs fixed rather than replicated (the `access` token
tuple bug, the never-persisted refresh token) and the behaviors preserved exactly despite looking
like bugs (no `webauthn_enabled` gate on credential list/delete, no duplicate-credential
rejection, the dead `WEBAUTHN_CHALLENGE_EXPIRY_SECONDS` setting).

Unlike Organizations, these routes are **unconditionally registered** (see `app.py`) — Django's
own `urls.py` registers `webauthn/*` unconditionally too; `WEBAUTHN_ENABLED` is checked at the
service-call level inside `begin_registration`/`complete_registration`/`begin_authentication`/
`complete_authentication` (each returns a `"WebAuthn is not enabled"` error, mapped to the same
`400 WEBAUTHN_ERROR` shape as any other failure there — there's no separate feature-disabled
shape the way Organizations has one).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import webauthn_service
from tenxyte.adapters.fastapi.deps import get_db_session, get_jwt_service, get_settings
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.refresh_tokens import issue_refresh_token
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.adapters.fastapi.schemas import (
    WebAuthnAuthenticateBeginRequest,
    WebAuthnAuthenticateCompleteRequest,
    WebAuthnRegisterCompleteRequest,
)
from tenxyte.adapters.fastapi.security import AuthContext, require_jwt
from tenxyte.adapters.fastapi.serialization import serialize_user
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings

router = APIRouter()


def _resolved_application_id(request: Request) -> str:
    application = getattr(request.state, "application", None)
    return str(application.id) if application is not None else "default"


@router.post("/webauthn/register/begin/")
async def webauthn_register_begin(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    options, error = await webauthn_service.begin_registration_async(
        session,
        settings,
        user_id=auth.user.id,
        email=auth.user.email or auth.user.id,
        display_name=auth.user.email or auth.user.id,
    )
    if error is not None:
        raise TenxyteAPIError(error, code="WEBAUTHN_ERROR", status_code=400)
    return options


@router.post("/webauthn/register/complete/")
async def webauthn_register_complete(
    body: WebAuthnRegisterCompleteRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    if not body.credential:
        raise TenxyteAPIError("credential is required", code="MISSING_FIELDS", status_code=400)

    credential, error = await webauthn_service.complete_registration_async(
        session,
        settings,
        user_id=auth.user.id,
        credential_data=body.credential,
        challenge_id=body.challenge_id,
        device_name=body.device_name,
    )
    if error is not None:
        raise TenxyteAPIError(error, code="REGISTRATION_FAILED", status_code=400)

    return {
        "message": "Passkey registered successfully",
        "credential": {
            "id": credential.id,
            "device_name": credential.device_name,
            "created_at": credential.created_at.isoformat() if credential.created_at else None,
        },
    }


@router.post("/webauthn/authenticate/begin/")
async def webauthn_authenticate_begin(
    body: WebAuthnAuthenticateBeginRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    user_id = None
    email = body.email.strip().lower()
    if email:
        user_repo = SQLAlchemyAsyncUserRepository(session)
        user = await user_repo.get_by_email(email)
        if user is not None and user.is_active:
            user_id = user.id

    options, error = await webauthn_service.begin_authentication_async(session, settings, user_id=user_id)
    if error is not None:
        raise TenxyteAPIError(error, code="WEBAUTHN_ERROR", status_code=400)
    return options


@router.post("/webauthn/authenticate/complete/")
async def webauthn_authenticate_complete(
    body: WebAuthnAuthenticateCompleteRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    jwt_service: JWTService = Depends(get_jwt_service),  # noqa: B008
):
    if not body.credential:
        raise TenxyteAPIError("credential is required", code="MISSING_FIELDS", status_code=400)

    # Django accepts `device_info`/derives it from User-Agent, but only ever threads it into the
    # never-persisted `generate_refresh_token()` call (see webauthn_service.py's module docstring)
    # — an opaque claim on a token nothing can look up again. Since this port issues a real,
    # persisted refresh token instead (via `issue_refresh_token`, whose own `device_id` parameter
    # is a distinct identifier-for-lookup concept, not a free-text description — same distinction
    # already documented on `RefreshTokenDB.device_id` vs `device_info` in models_sa.py), there's
    # nowhere meaningful for this value to go; not computed here for that reason.

    credential, error = await webauthn_service.complete_authentication_async(
        session, settings, credential_data=body.credential, challenge_id=body.challenge_id
    )
    if error is not None:
        raise TenxyteAPIError(error, code="WEBAUTHN_AUTH_FAILED", status_code=401)

    app_id = _resolved_application_id(request)
    access_token, _jti, _expires_at = jwt_service.generate_access_token(credential.user_id, application_id=app_id)
    refresh_token = await issue_refresh_token(
        session, credential.user_id, lifetime_seconds=settings.jwt_refresh_token_lifetime
    )

    user_repo = SQLAlchemyAsyncUserRepository(session)
    user = await user_repo.get_by_id(credential.user_id)

    return {
        # Deliberately `access`/`refresh`, not `access_token`/`refresh_token` — see
        # webauthn_service.py's module docstring.
        "access": access_token,
        "refresh": refresh_token,
        "user": serialize_user(user) if user is not None else {"id": credential.user_id},
        "message": "Authentication successful",
        "credential_used": credential.credential_id,
    }


@router.get("/webauthn/credentials/")
async def webauthn_credential_list(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    credentials = await webauthn_service.list_credentials_async(session, auth.user.id)
    items = [webauthn_service.serialize_credential(c) for c in credentials]
    return {"credentials": items, "count": len(items)}


@router.delete("/webauthn/credentials/{credential_id}/", status_code=204)
async def webauthn_credential_delete(
    credential_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_jwt()),  # noqa: B008
):
    success, error = await webauthn_service.delete_credential_async(
        session, user_id=auth.user.id, credential_id=credential_id
    )
    if not success:
        raise TenxyteAPIError(error, code="CREDENTIAL_NOT_FOUND", status_code=404)
