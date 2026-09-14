"""
Async implementations of the Async_Ports for the FastAPI Reference_Stack (spec z_aud_3,
Requirement 3.2) — SQLAlchemy 2.0 async, no `asyncio.to_thread` bridge needed since every query
here is genuinely non-blocking via `AsyncSession`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tenxyte.adapters.fastapi.models_sa import UserDB
from tenxyte.ports.async_repositories import AsyncUserRepository
from tenxyte.ports.repositories import MFAType, User


class SQLAlchemyAsyncUserRepository(AsyncUserRepository):
    """The Reference_Stack's `AsyncUserRepository`: SQLAlchemy 2.0 async over `models_sa.UserDB`."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        db_user = await self.session.get(UserDB, user_id)
        return db_user.to_port_model() if db_user else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserDB).where(UserDB.email == email)
        db_user = (await self.session.execute(stmt)).scalar_one_or_none()
        return db_user.to_port_model() if db_user else None

    async def get_by_phone(self, phone_country_code: str, phone_number: str) -> User | None:
        """Not part of the `AsyncUserRepository` port ABC — phone isn't a Core concept (the port
        `User` dataclass has no dedicated phone fields), so this is a Reference_Stack-only
        extension used by `SQLAlchemyPhonePasswordLookup` (Wave A follow-up, login/phone)."""
        stmt = select(UserDB).where(
            UserDB.phone_country_code == phone_country_code, UserDB.phone_number == phone_number
        )
        db_user = (await self.session.execute(stmt)).scalar_one_or_none()
        return db_user.to_port_model() if db_user else None

    async def create(self, user: User) -> User:
        metadata = user.metadata or {}
        db_user = UserDB(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_staff=user.is_staff,
            status=user.status,
            mfa_type=user.mfa_type,
            mfa_secret=user.mfa_secret,
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            user_metadata=metadata,
            # Wave A follow-up (login/phone): phone_country_code/phone_number are stored as
            # dedicated indexed columns, mirrored in from Core's generic metadata dict — the port
            # dataclass itself has no dedicated phone fields (see models_sa.py's docstring).
            phone_country_code=metadata.get("phone_country_code"),
            phone_number=metadata.get("phone_number"),
        )
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user.to_port_model()

    async def update(self, user: User) -> User:
        db_user = await self.session.get(UserDB, user.id)
        if not db_user:
            raise ValueError(f"User with ID {user.id} not found")

        db_user.email = user.email
        db_user.password_hash = user.password_hash
        db_user.first_name = user.first_name
        db_user.last_name = user.last_name
        db_user.is_active = user.is_active
        db_user.is_superuser = user.is_superuser
        db_user.is_staff = user.is_staff
        db_user.status = user.status
        db_user.mfa_type = user.mfa_type
        db_user.mfa_secret = user.mfa_secret
        db_user.email_verified = user.email_verified
        db_user.phone_verified = user.phone_verified
        db_user.last_login = user.last_login
        db_user.user_metadata = user.metadata

        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user.to_port_model()

    async def delete(self, user_id: str) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        await self.session.delete(db_user)
        await self.session.commit()
        return True

    async def list_all(self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None) -> list[User]:
        stmt = select(UserDB)
        if filters:
            if "is_active" in filters:
                stmt = stmt.where(UserDB.is_active == filters["is_active"])
            if "status" in filters:
                stmt = stmt.where(UserDB.status == filters["status"])
            if "email" in filters:
                stmt = stmt.where(UserDB.email == filters["email"])
        stmt = stmt.offset(skip).limit(limit)
        db_users = (await self.session.execute(stmt)).scalars().all()
        return [u.to_port_model() for u in db_users]

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        stmt = select(func.count(UserDB.id))
        if filters:
            if "is_active" in filters:
                stmt = stmt.where(UserDB.is_active == filters["is_active"])
            if "status" in filters:
                stmt = stmt.where(UserDB.status == filters["status"])
            if "email" in filters:
                stmt = stmt.where(UserDB.email == filters["email"])
        return (await self.session.execute(stmt)).scalar_one()

    async def update_last_login(self, user_id: str, timestamp: datetime) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.last_login = timestamp
        await self.session.commit()
        return True

    async def set_mfa_secret(self, user_id: str, mfa_type: MFAType, secret: str) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.mfa_type = mfa_type
        db_user.mfa_secret = secret
        await self.session.commit()
        return True

    async def verify_email(self, user_id: str) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.email_verified = True
        await self.session.commit()
        return True

    # -- Reference_Stack-only extensions (not part of the AsyncUserRepository port ABC) --
    # Wave C (z_aud_3 task 7.1): phone verification and 2FA enrollment writes, mirroring
    # DjangoUserRepository's equivalents (verify_phone, enable_mfa, disable_mfa) and feeding
    # SQLAlchemyTOTPStorage's write methods for the secret/backup-codes columns.

    async def verify_phone(self, user_id: str) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.phone_verified = True
        await self.session.commit()
        return True

    async def save_totp_secret(self, user_id: str, encrypted_secret: str) -> bool:
        """Only the secret — 2FA isn't enabled yet at Setup time; `enable_mfa` is the separate
        confirmation step, matching Django's split between `storage.save_totp_secret` (Setup) and
        `storage.enable_2fa` + `user_repo.enable_mfa` (Confirm)."""
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.mfa_secret = encrypted_secret
        await self.session.commit()
        return True

    async def save_backup_codes(self, user_id: str, hashed_codes: list[str]) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.backup_codes = hashed_codes
        await self.session.commit()
        return True

    async def enable_mfa(self, user_id: str, mfa_type: MFAType = MFAType.TOTP) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.mfa_type = mfa_type
        await self.session.commit()
        return True

    async def disable_mfa(self, user_id: str) -> bool:
        db_user = await self.session.get(UserDB, user_id)
        if not db_user:
            return False
        db_user.mfa_type = MFAType.NONE
        db_user.mfa_secret = None
        db_user.backup_codes = []
        await self.session.commit()
        return True
