"""
Async-native WebAuthn/Passkeys service for the Reference_Stack (spec z_aud_3, Wave G, task 12.1).

**Not a thin wrapper around `core.webauthn_service.WebAuthnService`, unlike most of this port's
other "Core already has it" cases** — Core's `WebAuthnService` is genuinely framework-agnostic,
but its `WebAuthnCredentialRepository`/`WebAuthnChallengeRepository` Protocols are sync-only by
design (the docstring on their `Async*` mirrors in `core/webauthn_service.py` says outright: "not
yet consumed by `WebAuthnService`, which stays sync-only in this phase"). Bridging that into this
adapter's async-first SQLAlchemy session would mean either a second, parallel sync DB access path
just for WebAuthn, or wrapping every credential/challenge read in `asyncio.to_thread` — both worse
than just calling the same underlying `webauthn` (py_webauthn) library functions Core calls
directly, with real async repositories. Verified against Core's exact call sites
(`core/webauthn_service.py`) so the challenge/verification semantics match byte-for-byte; only the
storage layer is genuinely new.

**Two real Django bugs found while porting, fixed here rather than replicated — documented, not
silently diverged**:
1. `WebAuthnAuthenticateCompleteView.post` calls `jwt_service.generate_access_token(...)` — which
   returns a 3-tuple `(token, jti, expires_at)` — without unpacking it, so Django's real JSON
   response has `"access"` set to a 3-element array `[token, jti, iso-datetime]`, not a plain JWT
   string. Every other login-shaped endpoint in this adapter (including `magic_link.py`, which hit
   the identical Django-side bug at `magic_link_views.py:320` and was already fixed there without
   this specific note) unpacks the tuple correctly; this file does the same, for the same reason —
   a literal array-valued token would make WebAuthn login non-functional for any real client, and
   the whole point of building this endpoint is for it to work.
2. `generate_refresh_token()` (`core/jwt_service.py`) is literally `return str(uuid.uuid4())` — no
   database write, ever. Django's WebAuthn (and magic-link) login flow hands back a refresh token
   that can never be redeemed by `/refresh/` since no matching row exists anywhere. This adapter
   uses `refresh_tokens.issue_refresh_token` (the Reference_Stack's real, persisted refresh-token
   issuance — already used by `auth.py`/`magic_link.py`) instead, for the same reason as (1).

**Preserved exactly, even though they look like bugs, because they're genuinely reachable/
observable Django behavior with no functional cost to preserving them**:
- `list_credentials`/`delete_credential` have no `webauthn_enabled` gate at all in Core (only
  `begin_registration`/`complete_registration`/`begin_authentication`/`complete_authentication`
  check it) — replicated: `list_credentials_async`/`delete_credential_async` below don't check the
  setting either.
- No duplicate-`credential_id` rejection exists anywhere in Django's real code — it relies solely
  on the DB `unique=True` constraint, and an uncaught `IntegrityError` propagates to a generic 500.
  Not specially caught here either; a UNIQUE-constraint violation on `session.commit()` raises
  `sqlalchemy.exc.IntegrityError`, uncaught, and reaches this adapter's own generic 500 handler —
  the same shape of failure Django has, arrived at the same way (an omission, not a try/except).
- `WEBAUTHN_CHALLENGE_EXPIRY_SECONDS` is a real Django setting that `begin_registration`/
  `begin_authentication` never actually read — both hardcode `expiry_seconds=300` literally.
  Hardcoded here too, for the same reason: no settings property was added for a value nothing
  would consume.

`credential_id`/`public_key` are FIDO2 binary data; `credential_id` is stored as base64url text
(matching the string the browser's WebAuthn API itself sends as `credential.id`/`rawId`, so
authentication-time lookups compare directly against the same representation) via
`webauthn.helpers.bytes_to_base64url`/`base64url_to_bytes`; `public_key` as base64 text (never
round-tripped against a client-supplied string, so any safe binary-to-text encoding works).
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import WebAuthnChallengeDB, WebAuthnCredentialDB
from tenxyte.core.settings import Settings

logger = logging.getLogger(__name__)

_CHALLENGE_EXPIRY_SECONDS = 300


def _get_webauthn():
    """Lazy import, mirroring `core.webauthn_service._get_webauthn` — the `webauthn` package is
    an optional extra (`pip install tenxyte[webauthn]`), not a hard dependency of this adapter."""
    try:
        import webauthn

        return webauthn
    except ImportError as exc:
        raise ImportError(
            "py_webauthn is required for WebAuthn/Passkeys support. Install it with: pip install webauthn"
        ) from exc


def _origin(rp_id: str) -> str:
    """Mirrors `WebAuthnService._get_origin()` exactly."""
    if rp_id == "localhost":
        return "http://localhost"
    return f"https://{rp_id}"


def _is_valid(challenge: WebAuthnChallengeDB) -> bool:
    """Mirrors `WebAuthnChallenge.is_valid()`."""
    if challenge.is_used:
        return False
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < expires_at


async def _consume_challenge_async(session: AsyncSession, challenge: WebAuthnChallengeDB) -> None:
    challenge.is_used = True
    await session.commit()


# ============================================================
# Registration
# ============================================================


async def begin_registration_async(
    session: AsyncSession, settings: Settings, *, user_id: str, email: str, display_name: str = ""
) -> tuple[dict[str, Any] | None, str | None]:
    """Mirrors `WebAuthnService.begin_registration` exactly."""
    if not settings.webauthn_enabled:
        return None, "WebAuthn is not enabled"

    webauthn = _get_webauthn()

    existing_stmt = select(WebAuthnCredentialDB.credential_id).where(WebAuthnCredentialDB.user_id == user_id)
    existing_ids = list((await session.execute(existing_stmt)).scalars().all())

    raw_challenge = secrets.token_urlsafe(32)
    challenge = WebAuthnChallengeDB(
        challenge=raw_challenge,
        operation="register",
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=_CHALLENGE_EXPIRY_SECONDS),
    )
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)

    try:
        options = webauthn.generate_registration_options(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            user_id=user_id.encode(),
            user_name=email,
            user_display_name=display_name or email,
            challenge=raw_challenge.encode(),
            exclude_credentials=[
                webauthn.helpers.structs.PublicKeyCredentialDescriptor(id=webauthn.helpers.base64url_to_bytes(cid))
                for cid in existing_ids
            ],
        )
        return {"challenge_id": challenge.id, "options": webauthn.options_to_json(options)}, None
    except Exception:
        logger.exception("WebAuthn begin_registration error")
        return None, "An unexpected error occurred during WebAuthn registration."


async def complete_registration_async(
    session: AsyncSession,
    settings: Settings,
    *,
    user_id: str,
    credential_data: dict[str, Any],
    challenge_id: str,
    device_name: str = "",
) -> tuple[WebAuthnCredentialDB | None, str | None]:
    """Mirrors `WebAuthnService.complete_registration` exactly."""
    if not settings.webauthn_enabled:
        return None, "WebAuthn is not enabled"

    challenge = await session.get(WebAuthnChallengeDB, challenge_id) if challenge_id else None
    if challenge is None:
        return None, "Invalid or expired challenge"
    if not _is_valid(challenge):
        return None, "Challenge has expired or already been used"
    if challenge.user_id != user_id:
        return None, "Challenge does not match user"

    webauthn = _get_webauthn()

    try:
        verification = webauthn.verify_registration_response(
            credential=credential_data,
            expected_challenge=challenge.challenge.encode(),
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=_origin(settings.webauthn_rp_id),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("WebAuthn registration verification failed: %s", e)
        return None, f"Registration verification failed: {e}"

    await _consume_challenge_async(session, challenge)

    credential = WebAuthnCredentialDB(
        user_id=user_id,
        credential_id=webauthn.helpers.bytes_to_base64url(verification.credential_id),
        public_key=_b64_encode(verification.credential_public_key),
        sign_count=verification.sign_count,
        device_name=device_name or "Passkey",
        aaguid=str(verification.aaguid) if verification.aaguid else "",
    )
    session.add(credential)
    await session.commit()
    await session.refresh(credential)

    return credential, None


def _b64_encode(raw: bytes) -> str:
    import base64

    return base64.b64encode(raw).decode()


def _b64_decode(text: str) -> bytes:
    import base64

    return base64.b64decode(text.encode())


# ============================================================
# Authentication
# ============================================================


async def begin_authentication_async(
    session: AsyncSession, settings: Settings, *, user_id: str | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """Mirrors `WebAuthnService.begin_authentication` exactly — `user_id=None` supports the
    discoverable/usernameless (resident-key) flow."""
    if not settings.webauthn_enabled:
        return None, "WebAuthn is not enabled"

    webauthn = _get_webauthn()

    raw_challenge = secrets.token_urlsafe(32)
    challenge = WebAuthnChallengeDB(
        challenge=raw_challenge,
        operation="authenticate",
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=_CHALLENGE_EXPIRY_SECONDS),
    )
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)

    allow_credentials = []
    if user_id:
        creds_stmt = select(WebAuthnCredentialDB.credential_id).where(WebAuthnCredentialDB.user_id == user_id)
        credential_ids = (await session.execute(creds_stmt)).scalars().all()
        allow_credentials = [
            webauthn.helpers.structs.PublicKeyCredentialDescriptor(id=webauthn.helpers.base64url_to_bytes(cid))
            for cid in credential_ids
        ]

    try:
        options = webauthn.generate_authentication_options(
            rp_id=settings.webauthn_rp_id,
            challenge=raw_challenge.encode(),
            allow_credentials=allow_credentials,
        )
        return {"challenge_id": challenge.id, "options": webauthn.options_to_json(options)}, None
    except Exception:
        logger.exception("WebAuthn begin_authentication error")
        return None, "An unexpected error occurred during WebAuthn authentication."


async def complete_authentication_async(
    session: AsyncSession, settings: Settings, *, credential_data: dict[str, Any], challenge_id: str
) -> tuple[WebAuthnCredentialDB | None, str | None]:
    """Mirrors `WebAuthnService.complete_authentication` exactly — returns the (now sign-count-
    updated) credential row on success, or `(None, error)`."""
    if not settings.webauthn_enabled:
        return None, "WebAuthn is not enabled"

    challenge = await session.get(WebAuthnChallengeDB, challenge_id) if challenge_id else None
    if challenge is None:
        return None, "Invalid or expired challenge"
    if not _is_valid(challenge):
        return None, "Challenge has expired or already been used"

    raw_credential_id = credential_data.get("id", "")
    cred_stmt = select(WebAuthnCredentialDB).where(WebAuthnCredentialDB.credential_id == raw_credential_id)
    stored_credential = (await session.execute(cred_stmt)).scalar_one_or_none()
    if stored_credential is None:
        return None, "Unknown credential"

    webauthn = _get_webauthn()

    try:
        verification = webauthn.verify_authentication_response(
            credential=credential_data,
            expected_challenge=challenge.challenge.encode(),
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=_origin(settings.webauthn_rp_id),
            credential_public_key=_b64_decode(stored_credential.public_key),
            credential_current_sign_count=stored_credential.sign_count,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("WebAuthn authentication verification failed: %s", e)
        return None, f"Authentication verification failed: {e}"

    await _consume_challenge_async(session, challenge)
    stored_credential.sign_count = verification.new_sign_count
    stored_credential.last_used_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(stored_credential)

    return stored_credential, None


# ============================================================
# Credential management — no `webauthn_enabled` gate, matching Core exactly (see module docstring).
# ============================================================


def serialize_credential(credential: WebAuthnCredentialDB) -> dict[str, Any]:
    """Matches `WebAuthnService.list_credentials`'s per-item shape exactly."""
    return {
        "id": credential.id,
        "device_name": credential.device_name,
        "created_at": credential.created_at.isoformat() if credential.created_at else None,
        "last_used_at": credential.last_used_at.isoformat() if credential.last_used_at else None,
        "transports": credential.transports,
    }


async def list_credentials_async(session: AsyncSession, user_id: str) -> list[WebAuthnCredentialDB]:
    stmt = (
        select(WebAuthnCredentialDB)
        .where(WebAuthnCredentialDB.user_id == user_id)
        .order_by(WebAuthnCredentialDB.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def delete_credential_async(
    session: AsyncSession, *, user_id: str, credential_id: str
) -> tuple[bool, str | None]:
    """Mirrors `DjangoWebAuthnStorage.delete` — looked up by database PK `id` (not the FIDO2
    `credential_id` string), scoped to the requesting user."""
    credential = await session.get(WebAuthnCredentialDB, credential_id)
    if credential is None or credential.user_id != user_id:
        return False, "Credential not found"
    await session.delete(credential)
    await session.commit()
    return True, None
