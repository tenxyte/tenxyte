"""
Async-native Social Login (OAuth2 multi-provider) service for the Reference_Stack (spec z_aud_3,
Wave G chunk 2/4, task 12.1) — google/github/microsoft/facebook/apple. Django never extracted this
to Core — this is a new implementation verified against the real
`services/social_auth_service.py` (read in full: `AbstractOAuthProvider` and all 5 concrete
providers, `SocialAuthService.authenticate`, `get_provider`).

**`httpx.AsyncClient` instead of Django's blocking `requests`** — this port's Async_Purity rule
forbids blocking HTTP calls in async code (`scripts/check_async_purity.py` explicitly names
`requests.<verb>()` as a violation), so every provider call here is a real, awaited HTTP request.
`httpx` is consequently a genuine runtime dependency of the `fastapi` extra as of this chunk (see
`pyproject.toml`), not just a test-only one.

**Testing without mocks, extended to HTTP this time**: every real OAuth provider is, obviously,
unreachable from a test suite. Consistent with `webauthn_service.py`'s real (if synthetic) FIDO2
authenticator rather than a mocked crypto function, HTTP calls here go through a single
`httpx.AsyncClient` factory (`_client()`) whose `transport` a test can override module-globally
(`_test_transport`) with a real `httpx.MockTransport`/`httpx.ASGITransport` — routing every
provider call to a real local fake OAuth server (genuine HTTP request/response objects, real JSON
serialization) instead of the actual internet. No `unittest.mock` anywhere in this module or its
tests.

**Google/Apple id_token verification without `google-auth`/`google-auth-oauthlib`** (Django-only
extras, not part of the `fastapi` extra): Django's `GoogleOAuthProvider.verify_id_token` calls
`google.oauth2.id_token.verify_oauth2_token`, which is really just "fetch Google's JWKS, verify an
RS256 signature, check `iss`/`aud`/expiry" — exactly what `AppleOAuthProvider.verify_id_token`
already does by hand with `PyJWT` (already a dependency, via Apple's own client-secret-JWT need).
`_verify_id_token_via_jwks_async` below does the same generic JWKS-based RS256 verification for
*both* providers, fetching the JWKS via `httpx.AsyncClient` (async) and handing the matched key to
`PyJWT`'s pure/sync `jwt.decode()` (no I/O, safe to call directly) — verified against Google's
real, public JWKS endpoint and issuer/audience rules, not assumed.

**Account-fusion security logic replicated exactly (Django's own "F-03"/"R-05" fixes)**: a social
login whose email matches an existing local account is only linked automatically if (a) the
provider marked that email verified, AND (b) `social_auto_merge_accounts` is `True` (default
`False`) — otherwise refused outright, asking the caller to log in with email/password first. Both
checks are refusals with no silent fallback, in that order, matching the real service exactly.

**`must_change_password` / `password_change_only` scope (spec `force_password_change_on_first_login`)**:
`resolve_forced_password_change_scope` is called right before returning, on every successful
authenticate (new account or existing) — this path previously issued a full-scope token
unconditionally, bypassing the gating entirely, which meant an account provisioned with
`must_change_password=True` specifically to force setting a real password after a social signup
(so the user isn't permanently locked to that provider) had no effect if the user simply logged in
via social auth instead of a password endpoint. Fixed alongside the same gap on the magic-link
`verify/` path (`routers/magic_link.py`).

**Response shape genuinely differs between the two endpoints, not a port inconsistency**:
`POST social/<provider>/` strips `device_summary` from the response (`data.pop("device_summary",
None)` in the real view) and adds `message`; `GET social/<provider>/callback/` keeps
`device_summary` and never adds `message`. Both add `provider`. Replicated exactly in
`routers/social.py` — the raw dict this service returns includes `device_summary` unconditionally,
the two routes diverge only in what they do with it afterward, mirroring Django's own split
exactly (a shared service, two view-level response shapes).

**`token_pair` fields have no `token_type`/`expires_in`, unlike password/email login** — verified
by reading the real dict `SocialAuthService.authenticate` returns: exactly `access_token`,
`refresh_token`, `device_summary`, `user`, `is_new_user`. The `@extend_schema` docs claim
`token_type`/`expires_in` too; the real code never adds them. Not added here either.

**Not wired in this chunk, documented rather than half-built**: Django's `authenticate()` also
auto-creates a default Organization for a brand-new user when both `ORGANIZATIONS_ENABLED` and
`CREATE_DEFAULT_ORGANIZATION` are true (best-effort, swallows its own exceptions). Since
`organizations_enabled` defaults `False` on both adapters and `CREATE_DEFAULT_ORGANIZATION` has no
Reference_Stack settings property yet, this cross-feature integration (Wave E's `org_service.py`
already has everything `create_organization_async` needs) is left for a follow-up rather than
folded into an already-large chunk — new users are created without a default organization here
regardless of the `organizations_enabled` setting.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx
import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi import rbac_service
from tenxyte.adapters.fastapi.models_sa import SocialConnectionDB, UserDB
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings

_HTTP_TIMEOUT = 10.0

SUPPORTED_PROVIDERS = ("google", "github", "microsoft", "facebook", "apple")

# Overridable by tests (spec z_aud_3, Wave G chunk 2/4) — a real `httpx.AsyncBaseTransport`
# (`httpx.MockTransport`/`httpx.ASGITransport` over a real fake-provider ASGI app), never a mocked
# function. Production leaves this `None`, which makes `httpx.AsyncClient` use its real network
# transport; tests set it once (module-level) to route every provider call to a real local fake
# instead of the actual internet — no `unittest.mock` involved anywhere in this module or its
# tests, consistent with this port's no-mocks policy.
_test_transport: httpx.AsyncBaseTransport | None = None


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=_HTTP_TIMEOUT, transport=_test_transport)


# ============================================================
# Generic HTTP helpers — mirror AbstractOAuthProvider._get/_post exactly (same swallow-and-log
# posture: any failure, HTTP or network, returns None rather than raising).
# ============================================================


async def _get_async(url: str, access_token: str, *, params: dict | None = None) -> dict[str, Any] | None:
    try:
        async with _client() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:  # noqa: BLE001
        return None


async def _post_async(url: str, data: dict, *, headers: dict | None = None) -> dict[str, Any] | None:
    try:
        async with _client() as client:
            resp = await client.post(url, data=data, headers=headers or {})
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:  # noqa: BLE001
        return None


async def _verify_id_token_via_jwks_async(
    id_token: str, *, jwks_url: str, issuer: str | tuple[str, ...], audience: str
) -> dict[str, Any] | None:
    """Fetches the provider's JWKS over HTTP (async), then does the actual RS256 signature/claims
    verification synchronously via `PyJWT` (pure computation, no I/O — safe to call directly).
    Fail-closed: any error (unreachable JWKS, unknown `kid`, bad signature, wrong issuer/audience,
    expired token) returns `None`, never a partially-trusted decode."""
    try:
        async with _client() as client:
            jwks_resp = await client.get(jwks_url)
        jwks_resp.raise_for_status()
        jwks = jwks_resp.json()

        header = pyjwt.get_unverified_header(id_token)
        kid = header.get("kid")
        matching_jwk = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
        if matching_jwk is None:
            return None

        public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(matching_jwk)
        claims = pyjwt.decode(id_token, key=public_key, algorithms=["RS256"], audience=audience, issuer=issuer)
        return claims
    except Exception:  # noqa: BLE001
        return None


# ============================================================
# Google
# ============================================================

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


def _normalize_google(data: dict) -> dict[str, Any]:
    return {
        "provider_user_id": data.get("sub", ""),
        "email": data.get("email"),
        "email_verified": bool(data.get("email_verified", False)),
        "first_name": data.get("given_name", ""),
        "last_name": data.get("family_name", ""),
        "avatar_url": data.get("picture", ""),
    }


async def _google_get_user_info_async(access_token: str, settings: Settings) -> dict[str, Any] | None:
    data = await _get_async(GOOGLE_USERINFO_URL, access_token)
    return _normalize_google(data) if data else None


async def _google_exchange_code_async(
    code: str, redirect_uri: str, code_verifier: str | None, settings: Settings
) -> dict[str, Any] | None:
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": settings.social_google_scopes,
    }
    if code_verifier:
        data["code_verifier"] = code_verifier
    return await _post_async(GOOGLE_TOKEN_URL, data)


async def _google_verify_id_token_async(id_token: str, settings: Settings) -> dict[str, Any] | None:
    claims = await _verify_id_token_via_jwks_async(
        id_token, jwks_url=GOOGLE_JWKS_URL, issuer=GOOGLE_ISSUERS, audience=settings.google_client_id
    )
    return _normalize_google(claims) if claims else None


# ============================================================
# GitHub
# ============================================================

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


async def _github_get_user_info_async(access_token: str, settings: Settings) -> dict[str, Any] | None:
    data = await _get_async(GITHUB_USERINFO_URL, access_token)
    if not data:
        return None

    email = data.get("email")
    email_verified = False
    if not email:
        emails_data = await _get_async(GITHUB_EMAILS_URL, access_token)
        if emails_data:
            primary = next((e for e in emails_data if e.get("primary") and e.get("verified")), None)
            if primary:
                email = primary["email"]
                email_verified = bool(primary.get("verified", False))
    else:
        email_verified = True

    name_parts = (data.get("name") or "").split(" ", 1)
    return {
        "provider_user_id": str(data["id"]),
        "email": email,
        "email_verified": email_verified,
        "first_name": name_parts[0] if name_parts else "",
        "last_name": name_parts[1] if len(name_parts) > 1 else "",
        "avatar_url": data.get("avatar_url", ""),
    }


async def _github_exchange_code_async(
    code: str, redirect_uri: str, code_verifier: str | None, settings: Settings
) -> dict[str, Any] | None:
    data = {
        "code": code,
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "redirect_uri": redirect_uri,
        "scope": settings.social_github_scopes,
    }
    if code_verifier:
        data["code_verifier"] = code_verifier
    return await _post_async(GITHUB_TOKEN_URL, data, headers={"Accept": "application/json"})


# ============================================================
# Microsoft
# ============================================================

MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"


async def _microsoft_get_user_info_async(access_token: str, settings: Settings) -> dict[str, Any] | None:
    data = await _get_async(MICROSOFT_USERINFO_URL, access_token)
    if not data:
        return None
    email = data.get("mail") or data.get("userPrincipalName", "")
    return {
        "provider_user_id": data.get("id", ""),
        "email": email if "@" in email else None,
        "email_verified": True,  # Microsoft verifies emails
        "first_name": data.get("givenName", ""),
        "last_name": data.get("surname", ""),
        "avatar_url": "",
    }


async def _microsoft_exchange_code_async(
    code: str, redirect_uri: str, code_verifier: str | None, settings: Settings
) -> dict[str, Any] | None:
    data = {
        "code": code,
        "client_id": settings.microsoft_client_id,
        "client_secret": settings.microsoft_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": settings.social_microsoft_scopes,
    }
    if code_verifier:
        data["code_verifier"] = code_verifier
    return await _post_async(MICROSOFT_TOKEN_URL, data)


# ============================================================
# Facebook
# ============================================================

FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_USERINFO_URL = "https://graph.facebook.com/me"


async def _facebook_get_user_info_async(access_token: str, settings: Settings) -> dict[str, Any] | None:
    data = await _get_async(
        FACEBOOK_USERINFO_URL, access_token, params={"fields": "id,email,first_name,last_name,picture"}
    )
    if not data:
        return None
    return {
        "provider_user_id": data.get("id", ""),
        "email": data.get("email"),
        "email_verified": True,  # Facebook verifies emails
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "avatar_url": data.get("picture", {}).get("data", {}).get("url", ""),
    }


async def _facebook_exchange_code_async(
    code: str, redirect_uri: str, code_verifier: str | None, settings: Settings
) -> dict[str, Any] | None:
    data = {
        "code": code,
        "client_id": settings.facebook_app_id,
        "client_secret": settings.facebook_app_secret,
        "redirect_uri": redirect_uri,
        "scope": settings.social_facebook_scopes,
    }
    if code_verifier:
        data["code_verifier"] = code_verifier
    return await _post_async(FACEBOOK_TOKEN_URL, data)


# ============================================================
# Apple
# ============================================================

APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
_APPLE_CLIENT_SECRET_MAX_LIFETIME_SECONDS = 15777000  # Apple's own 6-month cap


def _apple_generate_client_secret(settings: Settings) -> str | None:
    """Mirrors `AppleOAuthProvider._generate_client_secret` exactly — a fresh ES256 JWT signed
    with the `.p8` private key, generated per call, never persisted."""
    if not (
        settings.apple_team_id and settings.apple_client_id and settings.apple_key_id and settings.apple_private_key
    ):
        return None

    now = int(time.time())
    payload = {
        "iss": settings.apple_team_id,
        "iat": now,
        "exp": now + _APPLE_CLIENT_SECRET_MAX_LIFETIME_SECONDS,
        "aud": APPLE_ISSUER,
        "sub": settings.apple_client_id,
    }
    try:
        key_bytes = settings.apple_private_key.encode("utf-8")
        private_key = serialization.load_pem_private_key(key_bytes, password=None)
        return pyjwt.encode(payload, private_key, algorithm="ES256", headers={"kid": settings.apple_key_id})
    except Exception:  # noqa: BLE001
        return None


async def _apple_exchange_code_async(
    code: str, redirect_uri: str, code_verifier: str | None, settings: Settings
) -> dict[str, Any] | None:
    client_secret = _apple_generate_client_secret(settings)
    if not client_secret:
        return None
    data = {
        "client_id": settings.apple_client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    return await _post_async(APPLE_TOKEN_URL, data)


def _normalize_apple(claims: dict) -> dict[str, Any]:
    email_verified = claims.get("email_verified", False)
    if isinstance(email_verified, str):
        email_verified = email_verified.strip().lower() == "true"
    else:
        email_verified = bool(email_verified)
    return {
        "provider_user_id": claims.get("sub", ""),
        "email": claims.get("email"),
        "email_verified": email_verified,
        "first_name": "",
        "last_name": "",
        "avatar_url": "",
    }


async def _apple_verify_id_token_async(id_token: str, settings: Settings) -> dict[str, Any] | None:
    claims = await _verify_id_token_via_jwks_async(
        id_token, jwks_url=APPLE_JWKS_URL, issuer=APPLE_ISSUER, audience=settings.apple_client_id
    )
    return _normalize_apple(claims) if claims else None


# ============================================================
# Provider dispatch
# ============================================================

_GET_USER_INFO = {
    "google": _google_get_user_info_async,
    "github": _github_get_user_info_async,
    "microsoft": _microsoft_get_user_info_async,
    "facebook": _facebook_get_user_info_async,
    # Apple has no userinfo endpoint — see AppleOAuthProvider.get_user_info's own docstring.
    # There's no dispatch entry for it here; routers/social.py never calls get_user_info for apple.
}

_EXCHANGE_CODE = {
    "google": _google_exchange_code_async,
    "github": _github_exchange_code_async,
    "microsoft": _microsoft_exchange_code_async,
    "facebook": _facebook_exchange_code_async,
    "apple": _apple_exchange_code_async,
}

_VERIFY_ID_TOKEN = {
    "google": _google_verify_id_token_async,
    "apple": _apple_verify_id_token_async,
}


def is_provider_supported(provider_name: str, settings: Settings) -> bool:
    """Mirrors `get_provider()` — enabled providers come from `settings.social_providers`
    (default: all five), intersected with the actual registry (always all five here)."""
    return provider_name in settings.social_providers and provider_name in SUPPORTED_PROVIDERS


async def get_user_info_async(provider_name: str, access_token: str, settings: Settings) -> dict[str, Any] | None:
    handler = _GET_USER_INFO.get(provider_name)
    return await handler(access_token, settings) if handler else None


async def exchange_code_async(
    provider_name: str, code: str, redirect_uri: str, code_verifier: str | None, settings: Settings
) -> dict[str, Any] | None:
    handler = _EXCHANGE_CODE.get(provider_name)
    return await handler(code, redirect_uri, code_verifier, settings) if handler else None


async def verify_id_token_async(provider_name: str, id_token: str, settings: Settings) -> dict[str, Any] | None:
    handler = _VERIFY_ID_TOKEN.get(provider_name)
    return await handler(id_token, settings) if handler else None


# ============================================================
# Orchestrator — mirrors SocialAuthService.authenticate exactly.
# ============================================================


async def authenticate_async(
    session: AsyncSession,
    *,
    provider_name: str,
    user_data: dict[str, Any],
    ip_address: str,
    device_info: str,
    settings: Settings,
    jwt_service: JWTService,
) -> tuple[dict[str, Any] | None, str | None]:
    """Returns `(data, error)`. `data` (on success) always includes `device_summary` — the two
    real HTTP views diverge only in what they do with that key afterward, see module docstring."""
    provider_user_id = user_data.get("provider_user_id", "")
    email = user_data.get("email")

    if not provider_user_id:
        return None, f"Invalid {provider_name} data: missing user ID"

    connection_stmt = select(SocialConnectionDB).where(
        SocialConnectionDB.provider == provider_name, SocialConnectionDB.provider_user_id == provider_user_id
    )
    connection = (await session.execute(connection_stmt)).scalar_one_or_none()

    user: UserDB | None
    if connection is not None:
        user = await session.get(UserDB, connection.user_id)
    elif email:
        is_verified = bool(user_data.get("email_verified", False))
        if not is_verified:
            return None, (
                f"Email from {provider_name} is not verified. "
                "Authentication and account fusion rejected for security."
            )

        user_stmt = select(UserDB).where(UserDB.email == email.lower())
        user = (await session.execute(user_stmt)).scalar_one_or_none()

        if user is not None and not settings.social_auto_merge_accounts:
            return None, (
                f"An account with this email already exists. Please login with your email and "
                f"password to link your {provider_name} account."
            )
    else:
        user = None

    is_new_user = False
    if user is None:
        is_new_user = True
        user = UserDB(
            email=email.lower() if email else None,
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            email_verified=bool(user_data.get("email_verified", False)),
            password_hash=None,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        default_role = await rbac_service.get_default_role_async(session)
        if default_role is not None:
            await rbac_service.assign_role_async(session, user.id, default_role.code)

        # Default-organization auto-creation is deliberately not wired here — see module docstring.
    else:
        if email and user_data.get("email_verified") and not user.email_verified:
            user.email_verified = True
            await session.commit()

    if not user.is_active:
        return None, "Account is disabled"
    if user.is_locked:
        return None, "Account is locked"

    if connection is None:
        connection = SocialConnectionDB(
            user_id=user.id,
            provider=provider_name,
            provider_user_id=provider_user_id,
        )
        session.add(connection)
    connection.email = email or ""
    connection.first_name = user_data.get("first_name", "")
    connection.last_name = user_data.get("last_name", "")
    connection.avatar_url = user_data.get("avatar_url", "")
    await session.commit()

    user.last_login = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)

    from tenxyte.adapters.fastapi.refresh_tokens import issue_refresh_token
    from tenxyte.device_info import get_device_summary

    app_id = "default"
    access_token, _jti, _expires_at = jwt_service.generate_access_token(user.id, application_id=app_id)
    refresh_token = await issue_refresh_token(
        session, user.id, lifetime_seconds=settings.jwt_refresh_token_lifetime, ip_address=ip_address or None
    )

    device_summary = get_device_summary(device_info) if device_info else None

    response_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_summary": device_summary,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_email_verified": user.email_verified,
            "is_phone_verified": user.phone_verified,
            "is_2fa_enabled": user.mfa_type.value != "none",
            "roles": await rbac_service.get_all_role_codes_async(session, user.id),
            "permissions": await rbac_service.effective_permission_codes_async(session, user.id),
        },
        "is_new_user": is_new_user,
    }

    # Force password change gating (feature: force_password_change_on_first_login). Social login
    # previously bypassed this entirely — an account provisioned with must_change_password=True
    # (e.g. to force setting a real password after a social signup, so the user isn't permanently
    # locked to that provider) must be restricted here too, exactly like login_email/login_phone.
    from tenxyte.adapters.fastapi.routers.auth import resolve_forced_password_change_scope

    forced_scope = resolve_forced_password_change_scope(settings, user)
    if forced_scope == "password_change_only":
        restricted_token, _jti, _expires_at = jwt_service.generate_access_token(
            user.id, application_id=app_id, extra_claims={"scope": "password_change_only"}
        )
        response_data["access_token"] = restricted_token
        response_data["token_scope"] = "password_change_only"
        response_data["must_change_password"] = True

    return (response_data, None)
