"""
FastAPI (SQLAlchemy) implementation of Tenxyte repositories.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from tenxyte.ports.repositories import UserRepository, User, MFAType
from tenxyte.adapters.fastapi.models import UserDB


class FastAPIUserRepository(UserRepository):
    """SQLAlchemy implementation of the UserRepository."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(UserDB).where(UserDB.id == user_id)
        db_user = self.session.execute(stmt).scalar_one_or_none()
        return db_user.to_port_model() if db_user else None

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserDB).where(UserDB.email == email)
        db_user = self.session.execute(stmt).scalar_one_or_none()
        return db_user.to_port_model() if db_user else None

    def create(self, user: User) -> User:
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
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            user_metadata=user.metadata,
        )
        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user.to_port_model()

    def update(self, user: User) -> User:
        stmt = select(UserDB).where(UserDB.id == user.id)
        db_user = self.session.execute(stmt).scalar_one_or_none()
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
        db_user.updated_at = datetime.utcnow()
        db_user.last_login = user.last_login
        db_user.user_metadata = user.metadata

        self.session.commit()
        self.session.refresh(db_user)
        return db_user.to_port_model()

    def delete(self, user_id: str) -> bool:
        stmt = select(UserDB).where(UserDB.id == user_id)
        db_user = self.session.execute(stmt).scalar_one_or_none()
        if db_user:
            self.session.delete(db_user)
            self.session.commit()
            return True
        return False

    def list_all(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        stmt = select(UserDB)
        if filters:
            if "is_active" in filters:
                stmt = stmt.where(UserDB.is_active == filters["is_active"])
            if "status" in filters:
                stmt = stmt.where(UserDB.status == filters["status"])
            if "email" in filters:
                stmt = stmt.where(UserDB.email == filters["email"])

        stmt = stmt.offset(skip).limit(limit)
        db_users = self.session.execute(stmt).scalars().all()
        return [user.to_port_model() for user in db_users]

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        stmt = select(func.count(UserDB.id))
        if filters:
            if "is_active" in filters:
                stmt = stmt.where(UserDB.is_active == filters["is_active"])
            if "status" in filters:
                stmt = stmt.where(UserDB.status == filters["status"])
            if "email" in filters:
                stmt = stmt.where(UserDB.email == filters["email"])
        return self.session.execute(stmt).scalar_one()

    def update_last_login(self, user_id: str, timestamp: datetime) -> bool:
        stmt = select(UserDB).where(UserDB.id == user_id)
        db_user = self.session.execute(stmt).scalar_one_or_none()
        if db_user:
            db_user.last_login = timestamp
            self.session.commit()
            return True
        return False

    def set_mfa_secret(self, user_id: str, mfa_type: MFAType, secret: str) -> bool:
        stmt = select(UserDB).where(UserDB.id == user_id)
        db_user = self.session.execute(stmt).scalar_one_or_none()
        if db_user:
            db_user.mfa_type = mfa_type
            db_user.mfa_secret = secret
            self.session.commit()
            return True
        return False

    def verify_email(self, user_id: str) -> bool:
        stmt = select(UserDB).where(UserDB.id == user_id)
        db_user = self.session.execute(stmt).scalar_one_or_none()
        if db_user:
            db_user.email_verified = True
            self.session.commit()
            return True
        return False
