"""
SQLAlchemy models for Tenxyte FastAPI adapter.
"""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Enum, JSON
from sqlalchemy.orm import declarative_base

from tenxyte.ports.repositories import MFAType, UserStatus

Base = declarative_base()

def generate_uuid() -> str:
    """Generate a string UUID."""
    return str(uuid.uuid4())

class UserDB(Base):
    """
    SQLAlchemy data model for users in the FastAPI adapter.
    This corresponds to the abstract `tenxyte.ports.repositories.User`.
    """
    __tablename__ = "tenxyte_users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_staff = Column(Boolean, default=False)
    
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    mfa_type = Column(Enum(MFAType), default=MFAType.NONE)
    mfa_secret = Column(String(255), nullable=True)
    
    email_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Store agnostic metadata
    user_metadata = Column("metadata", JSON, default=dict)

    def to_port_model(self):
        """Convert SQLAlchemy model to agnostic core User."""
        from tenxyte.ports.repositories import User
        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            first_name=self.first_name,
            last_name=self.last_name,
            is_active=self.is_active,
            is_superuser=self.is_superuser,
            is_staff=self.is_staff,
            status=self.status,
            mfa_type=self.mfa_type,
            mfa_secret=self.mfa_secret,
            email_verified=self.email_verified,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_login=self.last_login,
            metadata=self.user_metadata or {}
        )
