"""
Framework-agnostic OTP-code service for the Reference_Stack (spec z_aud_3, Wave C, task 7.1) — a
from-scratch equivalent of `tenxyte.services.otp_service.OTPService`/
`tenxyte.models.operational.OTPCode`. Unlike `password_strength.py`/`breach_check.py`, this isn't
a "framework-agnostic reimplementation avoiding a Django import" — Django has never extracted OTP
codes to Core (unlike TOTP/MagicLink), so there's no portable original to diverge from; this is a
new implementation of the same algorithm, verified against the Django_Adapter's actual (not
documented) behavior:

- 6-digit codes (`secrets.randbelow`-generated, cryptographically secure, not `random`),
  SHA-256-hashed for storage — the raw code is returned once by `generate_otp` and never
  persisted anywhere.
- Verification uses `hmac.compare_digest` (constant-time) against the stored hash.
- `attempts` is only ever incremented via an atomic conditional `UPDATE` (`WHERE is_used=false AND
  attempts<max_attempts AND expires_at>now`), never a Python-side read-then-write — required to
  avoid a race where concurrent verify calls each observe a stale `attempts` value and
  collectively exceed `max_attempts`.
- `max_attempts` is always 3 (the `OTPCode` model field's default) — Django's `OTP_MAX_ATTEMPTS`
  setting exists but nothing actually reads it (`OTPCode.generate()` doesn't accept a
  `max_attempts` argument), so hardcoding 3 here is genuine parity, not a shortcut.
- Expiry: 15 minutes for `email_verification`/`password_reset`, 10 for `phone_verification` (all
  hardcoded literals in Django's own `OTPService`, despite unused `OTP_EMAIL_VALIDITY`/
  `OTP_PHONE_VALIDITY` settings existing for them — not replicated, since porting dead config
  would be pointless), settings-driven for `login` (`Settings.otp_login_validity_minutes`, the
  one genuinely wired expiry in the Django_Adapter).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import OTPCodeDB
from tenxyte.core.settings import Settings

MAX_ATTEMPTS = 3

# otp_type -> fixed expiry in minutes. "login" is resolved from Settings instead (see generate_otp).
_FIXED_VALIDITY_MINUTES = {
    "email_verification": 15,
    "phone_verification": 10,
    "password_reset": 15,
}

_NOT_FOUND_MESSAGES = {
    "email_verification": "No verification code found",
    "phone_verification": "No verification code found",
    "password_reset": "No reset code found",
    "login": "No login code found",
}

_EXPIRED_OR_LOCKED_MESSAGE = "Code expired or too many attempts. Please request a new code."
_TOO_MANY_ATTEMPTS_MESSAGE = "Too many attempts. Please request a new code."


@dataclass
class OTPVerifyResult:
    success: bool
    error: str = ""


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


async def generate_otp(session: AsyncSession, user_id: str, otp_type: str, settings: Settings) -> tuple[OTPCodeDB, str]:
    """Invalidates any existing unused code of the same type for this user first (same as
    Django's `OTPService`), then creates a new one. Returns `(row, raw_code)` — `raw_code` is
    never stored; this return value is the only place it ever exists in plaintext."""
    await session.execute(
        update(OTPCodeDB)
        .where(OTPCodeDB.user_id == user_id, OTPCodeDB.otp_type == otp_type, OTPCodeDB.is_used == False)
        .values(is_used=True)
        .execution_options(synchronize_session=False)
    )

    validity_minutes = settings.otp_login_validity_minutes if otp_type == "login" else _FIXED_VALIDITY_MINUTES[otp_type]
    raw_code = _generate_code()
    row = OTPCodeDB(
        user_id=user_id,
        code_hash=_hash_code(raw_code),
        otp_type=otp_type,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=validity_minutes),
        max_attempts=MAX_ATTEMPTS,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row, raw_code


async def _latest_unused(session: AsyncSession, user_id: str, otp_type: str) -> OTPCodeDB | None:
    stmt = (
        select(OTPCodeDB)
        .where(OTPCodeDB.user_id == user_id, OTPCodeDB.otp_type == otp_type, OTPCodeDB.is_used == False)
        .order_by(OTPCodeDB.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def _as_aware(dt: datetime) -> datetime:
    """DB-loaded datetimes come back tz-naive from the aiosqlite dev driver, even though we
    always write tz-aware UTC values — normalize before comparing against `datetime.now(tz=...)`."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _is_valid(row: OTPCodeDB) -> bool:
    now = datetime.now(timezone.utc)
    return not row.is_used and now < _as_aware(row.expires_at) and row.attempts < row.max_attempts


async def verify_otp(session: AsyncSession, user_id: str, otp_type: str, code: str) -> OTPVerifyResult:
    """Same control-flow shape as Django's `OTPService.verify_*_otp` family — a lookup miss, an
    already-invalid code, and an over-the-limit concurrent attempt are each reported distinctly,
    matching the exact message set the Django_Adapter produces."""
    row = await _latest_unused(session, user_id, otp_type)
    if row is None:
        return OTPVerifyResult(success=False, error=_NOT_FOUND_MESSAGES[otp_type])

    if not _is_valid(row):
        return OTPVerifyResult(success=False, error=_EXPIRED_OR_LOCKED_MESSAGE)

    result = await session.execute(
        update(OTPCodeDB)
        .where(
            OTPCodeDB.id == row.id,
            OTPCodeDB.is_used == False,
            OTPCodeDB.attempts < OTPCodeDB.max_attempts,
            OTPCodeDB.expires_at > datetime.now(timezone.utc),
        )
        .values(attempts=OTPCodeDB.attempts + 1)
        .execution_options(synchronize_session=False)
    )
    await session.commit()

    if result.rowcount == 0:
        # Lost the race, or expired/used between the read above and this UPDATE.
        return OTPVerifyResult(success=False, error=_EXPIRED_OR_LOCKED_MESSAGE)

    await session.refresh(row)

    if hmac.compare_digest(row.code_hash, _hash_code(code)):
        row.is_used = True
        await session.commit()
        return OTPVerifyResult(success=True)

    if row.attempts >= row.max_attempts:
        return OTPVerifyResult(success=False, error=_TOO_MANY_ATTEMPTS_MESSAGE)
    return OTPVerifyResult(
        success=False, error=f"Invalid code. {row.max_attempts - row.attempts} attempt(s) remaining."
    )
