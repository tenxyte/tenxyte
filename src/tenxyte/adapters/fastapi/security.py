"""
JWT authentication dependency for the FastAPI_Adapter (spec z_aud_3, Requirement 3.6) — parity
with `tenxyte.decorators.require_jwt`: same `Authorization: Bearer <token>` extraction, same
error codes (`AUTH_REQUIRED`, `TOKEN_INVALID`, `TOKEN_APP_MISMATCH`, `USER_NOT_FOUND`,
`USER_INACTIVE`, `INSUFFICIENT_SCOPE`), same restricted-token-scope semantics (a token carrying a
`scope` claim is only accepted on endpoints that explicitly list that scope; a full-scope token —
no `scope` claim — is accepted everywhere, exactly as before this feature existed).

Used as a FastAPI dependency rather than a decorator, per the framework's own idiom:

    @router.get("/me")
    async def me(auth: AuthContext = Depends(require_jwt())):
        ...

    @router.post("/2fa/confirm")
    async def confirm(auth: AuthContext = Depends(require_jwt(allowed_scopes=["2fa_setup_only"]))):
        ...
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, Request
from tenxyte.adapters.fastapi.deps import get_db_session
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.jwt_service import DecodedToken
from tenxyte.ports.repositories import User


@dataclass
class AuthContext:
    """What a route gets after `require_jwt()` succeeds — the decoded token and the user it
    resolved to, plus the token's scope (`None` for a full-scope token)."""

    user: User
    payload: DecodedToken
    scope: str | None


def require_jwt(
    allowed_scopes: list[str] | None = None,
) -> Callable[..., Coroutine[Any, Any, AuthContext]]:
    allowed = set(allowed_scopes) if allowed_scopes else set()

    async def _dependency(
        request: Request, session: AsyncSession = Depends(get_db_session)  # noqa: B008
    ) -> AuthContext:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise TenxyteAPIError("Authorization header required", code="AUTH_REQUIRED", status_code=401)

        token = auth_header[7:]
        jwt_service = request.app.state.tenxyte_jwt_service
        payload = await jwt_service.decode_token_async(token)

        if not payload or not payload.is_valid:
            raise TenxyteAPIError("Invalid or expired token", code="TOKEN_INVALID", status_code=401)

        scope = (payload.claims or {}).get("scope")

        application = getattr(request.state, "application", None)
        if application is not None and str(application.id) != payload.app_id:
            raise TenxyteAPIError("Token does not match application", code="TOKEN_APP_MISMATCH", status_code=401)

        user_repo = SQLAlchemyAsyncUserRepository(session)
        user = await user_repo.get_by_id(payload.user_id)
        if not user:
            raise TenxyteAPIError("User not found", code="USER_NOT_FOUND", status_code=401)
        if not user.is_active:
            raise TenxyteAPIError("User account is inactive", code="USER_INACTIVE", status_code=401)

        if scope is not None and scope not in allowed:
            raise TenxyteAPIError("Insufficient token scope", code="INSUFFICIENT_SCOPE", status_code=403)

        return AuthContext(user=user, payload=payload, scope=scope)

    return _dependency
