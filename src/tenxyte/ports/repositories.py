"""
Port interfaces for Tenxyte repositories.

These abstract base classes define the contract between the Core and
any database implementation (Django ORM, SQLAlchemy, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, TypeVar, runtime_checkable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


# ============================================================
# Base Types
# ============================================================

class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class MFAType(str, Enum):
    """Multi-factor authentication type."""
    NONE = "none"
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    SMS = "sms"
    EMAIL = "email"


@dataclass
class User:
    """Agnostic user data structure."""
    id: str
    email: str
    password_hash: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    is_staff: bool = False
    status: UserStatus = UserStatus.ACTIVE
    mfa_type: MFAType = MFAType.NONE
    mfa_secret: Optional[str] = None
    email_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Organization:
    """Agnostic organization data structure."""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = True
    max_members: int = 0
    parent_id: Optional[str] = None
    owner_id: Optional[str] = None
    settings: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


@dataclass
class Role:
    """Agnostic role data structure."""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    permissions: List[str] = None
    is_system: bool = False
    organization_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []


@dataclass
class AuditLog:
    """Agnostic audit log entry."""
    id: str
    user_id: Optional[str] = None
    action: str = ""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    organization_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ============================================================
# Repository Interfaces
# ============================================================

class UserRepository(ABC):
    """
    Abstract base class for user repositories.
    
    Implementations must provide concrete methods for CRUD operations
    on user data, regardless of the underlying database technology.
    """
    
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        pass
    
    @abstractmethod
    def create(self, user: User) -> User:
        """Create a new user."""
        pass
    
    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user."""
        pass
    
    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete a user by ID."""
        pass
    
    @abstractmethod
    def list_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[User]:
        """List users with optional filtering."""
        pass
    
    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count users matching filters."""
        pass
    
    @abstractmethod
    def update_last_login(self, user_id: str, timestamp: datetime) -> bool:
        """Update user's last login timestamp."""
        pass
    
    @abstractmethod
    def set_mfa_secret(self, user_id: str, mfa_type: MFAType, secret: str) -> bool:
        """Set MFA secret for a user."""
        pass
    
    @abstractmethod
    def verify_email(self, user_id: str) -> bool:
        """Mark user's email as verified."""
        pass


class OrganizationRepository(ABC):
    """
    Abstract base class for organization repositories.
    """
    
    @abstractmethod
    def get_by_id(self, org_id: str) -> Optional[Organization]:
        """Get an organization by ID."""
        pass
    
    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get an organization by slug."""
        pass
    
    @abstractmethod
    def create(self, org: Organization) -> Organization:
        """Create a new organization."""
        pass
    
    @abstractmethod
    def update(self, org: Organization) -> Organization:
        """Update an existing organization."""
        pass
    
    @abstractmethod
    def delete(self, org_id: str) -> bool:
        """Delete an organization by ID."""
        pass
    
    @abstractmethod
    def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Organization]:
        """List organizations where user is a member."""
        pass
    
    @abstractmethod
    def get_children(self, org_id: str) -> List[Organization]:
        """Get child organizations."""
        pass
    
    @abstractmethod
    def add_member(self, org_id: str, user_id: str, role_id: str) -> bool:
        """Add a member to an organization."""
        pass
    
    @abstractmethod
    def remove_member(self, org_id: str, user_id: str) -> bool:
        """Remove a member from an organization."""
        pass


class RoleRepository(ABC):
    """
    Abstract base class for role repositories.
    """
    
    @abstractmethod
    def get_by_id(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        pass
    
    @abstractmethod
    def get_by_slug(self, slug: str, org_id: Optional[str] = None) -> Optional[Role]:
        """Get a role by slug within an organization or globally."""
        pass
    
    @abstractmethod
    def create(self, role: Role) -> Role:
        """Create a new role."""
        pass
    
    @abstractmethod
    def update(self, role: Role) -> Role:
        """Update an existing role."""
        pass
    
    @abstractmethod
    def delete(self, role_id: str) -> bool:
        """Delete a role by ID."""
        pass
    
    @abstractmethod
    def list_by_organization(
        self,
        org_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Role]:
        """List roles for an organization or global roles."""
        pass
    
    @abstractmethod
    def get_user_roles(self, user_id: str, org_id: Optional[str] = None) -> List[Role]:
        """Get roles assigned to a user."""
        pass


class AuditLogRepository(ABC):
    """
    Abstract base class for audit log repositories.
    """
    
    @abstractmethod
    def create(self, entry: AuditLog) -> AuditLog:
        """Create a new audit log entry."""
        pass
    
    @abstractmethod
    def get_by_id(self, entry_id: str) -> Optional[AuditLog]:
        """Get an audit log entry by ID."""
        pass
    
    @abstractmethod
    def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """List audit log entries for a user."""
        pass
    
    @abstractmethod
    def list_by_organization(
        self,
        org_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """List audit log entries for an organization."""
        pass
    
    @abstractmethod
    def list_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """List audit log entries for a specific resource."""
        pass
    
    @abstractmethod
    def delete_old_entries(self, before_date: datetime) -> int:
        """Delete audit log entries older than a date. Returns count deleted."""
        pass
    
    @abstractmethod
    def count_by_action(
        self,
        action: str,
        since: Optional[datetime] = None
    ) -> int:
        """Count entries by action type."""
        pass


# ============================================================
# Service Ports
# ============================================================

@runtime_checkable
class EmailService(Protocol):
    """Protocol for email services."""
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """Send an email."""
        ...
    
    def send_magic_link(
        self,
        to_email: str,
        magic_link_url: str,
        expires_in_minutes: int = 15
    ) -> bool:
        """Send a magic link email."""
        ...
    
    def send_2fa_code(
        self,
        to_email: str,
        code: str,
        method: str = "email"
    ) -> bool:
        """Send a 2FA verification code."""
        ...


@runtime_checkable
class CacheService(Protocol):
    """Protocol for cache services."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional timeout in seconds."""
        ...
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...
    
    def add_to_blacklist(self, token_jti: str, expires_in: int) -> bool:
        """Add a token JTI to the blacklist."""
        ...
    
    def is_blacklisted(self, token_jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        ...


# Type variables for generic repositories
T = TypeVar('T')
UserRepo = TypeVar('UserRepo', bound=UserRepository)
OrgRepo = TypeVar('OrgRepo', bound=OrganizationRepository)
RoleRepo = TypeVar('RoleRepo', bound=RoleRepository)
AuditRepo = TypeVar('AuditRepo', bound=AuditLogRepository)
