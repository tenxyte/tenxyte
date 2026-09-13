"""
`TOTPStorage` for the Reference_Stack (spec z_aud_3, Wave A) — read path only. Wave A's login
router needs to verify a TOTP code for a user who already has 2FA enabled (`load_user_data`), but
setting up/disabling 2FA or issuing backup codes is Group C's endpoint group (task 7.1, OTP/2FA):
those write paths raise `NotImplementedError` here rather than being silently half-implemented.

`UserDB` has no `backup_codes` column yet (that arrives with Group C's storage), so
`TOTPUserData.backup_codes` is always `[]` here — `TOTPService.verify_2fa_async`'s backup-code
fallback simply never matches, which is correct: no FastAPI-created account can have backup codes
yet, since nothing in this adapter issues them.
"""

from __future__ import annotations

from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.totp_service import TOTPUserData


class SQLAlchemyTOTPStorage:
    def __init__(self, user_repo: SQLAlchemyAsyncUserRepository):
        self.user_repo = user_repo

    async def load_user_data_async(self, user_id: str) -> TOTPUserData | None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            return None
        return TOTPUserData(
            id=user.id,
            email=user.email,
            totp_secret=user.mfa_secret,
            is_2fa_enabled=user.mfa_type.value != "none",
            backup_codes=[],
        )

    def load_user_data(self, user_id: str) -> TOTPUserData | None:
        raise NotImplementedError(
            "SQLAlchemyTOTPStorage is async-only in the Reference_Stack; use load_user_data_async."
        )

    def save_totp_secret(self, user_id: str, encrypted_secret: str) -> bool:
        raise NotImplementedError("2FA setup is Group C (z_aud_3 task 7.1), not yet ported to the Reference_Stack.")

    def save_backup_codes(self, user_id: str, hashed_codes: list[str]) -> bool:
        raise NotImplementedError("2FA backup codes are Group C (z_aud_3 task 7.1), not yet ported.")

    def enable_2fa(self, user_id: str) -> bool:
        raise NotImplementedError("2FA setup is Group C (z_aud_3 task 7.1), not yet ported to the Reference_Stack.")

    def disable_2fa(self, user_id: str) -> bool:
        raise NotImplementedError("2FA disable is Group C (z_aud_3 task 7.1), not yet ported to the Reference_Stack.")
