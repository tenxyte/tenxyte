"""
`TOTPStorage` for the Reference_Stack (spec z_aud_3, Wave C, task 7.1) — full read/write, backing
the 2FA-enrollment router (`routers/twofa.py`: setup, confirm, disable, backup-codes). Backed by
`SQLAlchemyAsyncUserRepository`'s Reference_Stack-only extensions (`save_totp_secret`,
`save_backup_codes`, `enable_mfa`, `disable_mfa`), which live on the user repo rather than here
since they all operate on `UserDB` columns, the same table `load_user_data_async` already reads.
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
            backup_codes=list(user.metadata.get("backup_codes", [])) if user.metadata else [],
        )

    def load_user_data(self, user_id: str) -> TOTPUserData | None:
        raise NotImplementedError(
            "SQLAlchemyTOTPStorage is async-only in the Reference_Stack; use load_user_data_async."
        )

    async def save_totp_secret_async(self, user_id: str, encrypted_secret: str) -> bool:
        return await self.user_repo.save_totp_secret(user_id, encrypted_secret)

    def save_totp_secret(self, user_id: str, encrypted_secret: str) -> bool:
        raise NotImplementedError(
            "SQLAlchemyTOTPStorage is async-only in the Reference_Stack; use save_totp_secret_async."
        )

    async def save_backup_codes_async(self, user_id: str, hashed_codes: list[str]) -> bool:
        return await self.user_repo.save_backup_codes(user_id, hashed_codes)

    def save_backup_codes(self, user_id: str, hashed_codes: list[str]) -> bool:
        raise NotImplementedError(
            "SQLAlchemyTOTPStorage is async-only in the Reference_Stack; use save_backup_codes_async."
        )

    async def enable_2fa_async(self, user_id: str) -> bool:
        return await self.user_repo.enable_mfa(user_id)

    def enable_2fa(self, user_id: str) -> bool:
        raise NotImplementedError("SQLAlchemyTOTPStorage is async-only in the Reference_Stack; use enable_2fa_async.")

    async def disable_2fa_async(self, user_id: str) -> bool:
        return await self.user_repo.disable_mfa(user_id)

    def disable_2fa(self, user_id: str) -> bool:
        raise NotImplementedError("SQLAlchemyTOTPStorage is async-only in the Reference_Stack; use disable_2fa_async.")
