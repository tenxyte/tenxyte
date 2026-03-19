"""
Django Repository Adapters for Tenxyte Core.

Implements the Repository ports using Django ORM.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from tenxyte.ports.repositories import (
    UserRepository,
    OrganizationRepository,
    RoleRepository,
    AuditLogRepository,
    User,
    Organization,
    Role,
    AuditLog,
    UserStatus,
    MFAType,
)
from tenxyte.models import get_user_model, get_organization_model

UserModel = get_user_model()
OrganizationModel = get_organization_model()


class DjangoUserRepository(UserRepository):
    """
    Django ORM implementation of UserRepository.

    Adapts between the Core's User dataclass and Django's User model.

    Example:
        from tenxyte.adapters.django.repositories import DjangoUserRepository

        repo = DjangoUserRepository()
        user = repo.get_by_email("user@example.com")
        if user:
            print(user.id, user.email)
    """

    def _to_core_user(self, django_user) -> Optional[User]:
        """Convert Django User model to Core User dataclass."""
        if django_user is None:
            return None

        # Determine MFA type
        mfa_type = MFAType.NONE
        if getattr(django_user, "is_2fa_enabled", False):
            if getattr(django_user, "totp_secret", None):
                mfa_type = MFAType.TOTP

        # Determine status
        status = UserStatus.ACTIVE
        if not django_user.is_active:
            if getattr(django_user, "is_banned", False):
                status = UserStatus.SUSPENDED
            elif getattr(django_user, "is_locked", False):
                status = UserStatus.SUSPENDED
            else:
                status = UserStatus.INACTIVE

        return User(
            id=str(django_user.id),
            email=django_user.email,
            password_hash=django_user.password,
            first_name=getattr(django_user, "first_name", None),
            last_name=getattr(django_user, "last_name", None),
            is_active=django_user.is_active and not getattr(django_user, "is_deleted", False),
            is_superuser=django_user.is_superuser,
            is_staff=django_user.is_staff,
            status=status,
            mfa_type=mfa_type,
            mfa_secret=getattr(django_user, "totp_secret", None),
            email_verified=getattr(django_user, "email_verified", False),
            created_at=getattr(django_user, "created_at", None),
            updated_at=getattr(django_user, "updated_at", None),
            last_login=getattr(django_user, "last_login", None),
            metadata=self._extract_metadata(django_user),
        )

    def _extract_metadata(self, django_user) -> Dict[str, Any]:
        """Extract additional metadata from Django user."""
        metadata = {}

        # Add optional fields if they exist
        optional_fields = [
            "phone_country_code",
            "phone_number",
            "username",
            "bio",
            "timezone",
            "language",
            "custom_fields",
            "google_id",
            "backup_codes",
            "is_banned",
            "is_locked",
            "is_deleted",
            "max_sessions",
            "max_devices",
        ]

        for field in optional_fields:
            if hasattr(django_user, field):
                value = getattr(django_user, field)
                if value is not None:
                    metadata[field] = value

        return metadata

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            return self._to_core_user(django_user)
        except UserModel.DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        try:
            django_user = UserModel.objects.get(email__iexact=email, is_deleted=False)
            return self._to_core_user(django_user)
        except UserModel.DoesNotExist:
            return None

    def create(self, user: User) -> User:
        """Create a new user."""
        django_user = UserModel.objects.create_user(
            email=user.email,
            password=None,  # Set separately via set_password
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_staff=user.is_staff,
            is_email_verified=user.email_verified,
        )

        # Set password if provided
        if user.password_hash:
            django_user.password = user.password_hash
            django_user.save(update_fields=["password"])

        # Set MFA if provided
        if user.mfa_secret:
            django_user.totp_secret = user.mfa_secret
            django_user.is_2fa_enabled = user.mfa_type != MFAType.NONE
            django_user.save(update_fields=["totp_secret", "is_2fa_enabled"])

        return self._to_core_user(django_user)

    def update(self, user: User) -> User:
        """Update an existing user."""
        try:
            django_user = UserModel.objects.get(id=user.id)
        except UserModel.DoesNotExist:
            raise ValueError(f"User with ID {user.id} not found")

        # Update fields
        if user.email:
            django_user.email = user.email
        if user.first_name is not None:
            django_user.first_name = user.first_name
        if user.last_name is not None:
            django_user.last_name = user.last_name
        if user.is_active is not None:
            django_user.is_active = user.is_active
        if user.email_verified is not None:
            django_user.is_email_verified = user.email_verified

        # Update password if changed (and it's not already a hash)
        if user.password_hash and not user.password_hash.startswith(("bcrypt", "pbkdf2", "argon2", "sha256")):
            django_user.set_password(user.password_hash)
        elif user.password_hash:
            django_user.password = user.password_hash

        # Update MFA
        if user.mfa_secret is not None:
            django_user.totp_secret = user.mfa_secret
            django_user.is_2fa_enabled = user.mfa_type != MFAType.NONE and bool(user.mfa_secret)

        django_user.save()
        return self._to_core_user(django_user)

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[User]:
        """Update user by ID with data dict (for view compatibility)."""
        try:
            django_user = UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            return None

        # Update fields from data dict
        if "first_name" in user_data:
            django_user.first_name = user_data["first_name"]
        if "last_name" in user_data:
            django_user.last_name = user_data["last_name"]
        if "email" in user_data:
            django_user.email = user_data["email"]
        if "is_active" in user_data:
            django_user.is_active = user_data["is_active"]
        if "is_email_verified" in user_data:
            django_user.is_email_verified = user_data["is_email_verified"]
        if "phone_country_code" in user_data:
            django_user.phone_country_code = user_data["phone_country_code"]
        if "phone_number" in user_data:
            django_user.phone_number = user_data["phone_number"]
        if "is_phone_verified" in user_data:
            django_user.is_phone_verified = user_data["is_phone_verified"]
        if "username" in user_data:
            django_user.username = user_data["username"]
        if "bio" in user_data:
            django_user.bio = user_data["bio"]
        if "timezone" in user_data:
            django_user.timezone = user_data["timezone"]
        if "language" in user_data:
            django_user.language = user_data["language"]
        if "custom_fields" in user_data:
            django_user.custom_fields = user_data["custom_fields"]

        django_user.save()
        return self._to_core_user(django_user)

    def delete(self, user_id: str) -> bool:
        """Soft delete a user."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.soft_delete()
            return True
        except UserModel.DoesNotExist:
            return False

    def soft_delete(self, user_id: str) -> bool:
        """Alias for delete()."""
        return self.delete(user_id)

    def ban(self, user_id: str, reason: str = "") -> bool:
        """Ban user account."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            if hasattr(django_user, "ban_account"):
                django_user.ban_account(reason)
            else:
                django_user.is_active = False
                django_user.is_banned = True
                django_user.save(update_fields=["is_active", "is_banned"])
            return True
        except UserModel.DoesNotExist:
            return False

    def unban(self, user_id: str) -> bool:
        """Unban user account."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            if hasattr(django_user, "unban_account"):
                django_user.unban_account()
            else:
                django_user.is_active = True
                django_user.is_banned = False
                django_user.save(update_fields=["is_active", "is_banned"])
            return True
        except UserModel.DoesNotExist:
            return False

    def lock(self, user_id: str, duration_minutes: int = 30, reason: str = "") -> bool:
        """Lock user account."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            if hasattr(django_user, "lock_account"):
                django_user.lock_account(duration_minutes)
            else:
                django_user.is_locked = True
                # we don't track locked_until if the method doesn't exist, this is a fallback
                django_user.save(update_fields=["is_locked"])
            return True
        except UserModel.DoesNotExist:
            return False

    def unlock(self, user_id: str) -> bool:
        """Unlock user account."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            if hasattr(django_user, "unlock_account"):
                django_user.unlock_account()
            else:
                django_user.is_locked = False
                django_user.save(update_fields=["is_locked"])
            return True
        except UserModel.DoesNotExist:
            return False

    def list_all(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        """List users with optional filtering."""
        queryset = UserModel.objects.filter(is_deleted=False)

        if filters:
            if "is_active" in filters:
                queryset = queryset.filter(is_active=filters["is_active"])
            if "is_staff" in filters:
                queryset = queryset.filter(is_staff=filters["is_staff"])
            if "is_email_verified" in filters:
                queryset = queryset.filter(is_email_verified=filters["is_email_verified"])
            if "is_2fa_enabled" in filters:
                queryset = queryset.filter(is_2fa_enabled=filters["is_2fa_enabled"])

        users = queryset[skip : skip + limit]
        return [self._to_core_user(u) for u in users]

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count users matching filters."""
        queryset = UserModel.objects.filter(is_deleted=False)

        if filters:
            if "is_active" in filters:
                queryset = queryset.filter(is_active=filters["is_active"])
            if "is_staff" in filters:
                queryset = queryset.filter(is_staff=filters["is_staff"])

        return queryset.count()

    def update_last_login(self, user_id: str, timestamp: Any) -> bool:
        """Update user's last login timestamp."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.last_login = timestamp
            django_user.save(update_fields=["last_login"])
            return True
        except UserModel.DoesNotExist:
            return False

    def set_mfa_secret(self, user_id: str, mfa_type: MFAType, secret: str) -> bool:
        """Set MFA secret for a user."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.totp_secret = secret
            django_user.is_2fa_enabled = mfa_type != MFAType.NONE and bool(secret)
            django_user.save(update_fields=["totp_secret", "is_2fa_enabled"])
            return True
        except UserModel.DoesNotExist:
            return False

    def verify_email(self, user_id: str) -> bool:
        """Mark user's email as verified."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.is_email_verified = True
            django_user.save(update_fields=["is_email_verified"])
            return True
        except UserModel.DoesNotExist:
            return False

    def enable_mfa(self, user_id: str, mfa_type: str) -> bool:
        """Enable MFA for user."""
        from tenxyte.models import get_user_model

        UserModel = get_user_model()

        try:
            user = UserModel.objects.get(id=user_id)
            user.is_2fa_enabled = True
            user.save(update_fields=["is_2fa_enabled"])
            return True
        except UserModel.DoesNotExist:
            return False

    def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for user."""
        from tenxyte.models import get_user_model

        UserModel = get_user_model()

        try:
            user = UserModel.objects.get(id=user_id)
            user.is_2fa_enabled = False
            user.totp_secret = None
            user.backup_codes = []
            user.save(update_fields=["is_2fa_enabled", "totp_secret", "backup_codes"])
            return True
        except UserModel.DoesNotExist:
            return False

    # Django-specific extensions

    def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID (Django-specific extension)."""
        try:
            django_user = UserModel.objects.get(google_id=google_id, is_deleted=False)
            return self._to_core_user(django_user)
        except (UserModel.DoesNotExist, AttributeError):
            return None

    def check_password(self, user_id: str, password: str) -> bool:
        """Check if password is correct for user."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            return django_user.check_password(password)
        except UserModel.DoesNotExist:
            return False

    def set_password(self, user_id: str, password: str) -> bool:
        """Set new password for user."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.set_password(password)
            django_user.save(update_fields=["password"])
            return True
        except UserModel.DoesNotExist:
            return False

    def update_password(self, user_id: str, password: str) -> bool:
        """Update password for user (alias for set_password)."""
        return self.set_password(user_id, password)

    def is_account_locked(self, user_id: str) -> bool:
        """Check if account is temporarily locked due to failed attempts."""
        from django.core.cache import cache

        cache_key = f"account_locked:{user_id}"
        if cache.get(cache_key):
            return True

        from tenxyte.models import get_user_model

        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(id=user_id)
            if hasattr(user, "is_account_locked"):
                return user.is_account_locked()
            from django.utils import timezone

            return (
                getattr(user, "is_locked", False)
                and getattr(user, "locked_until", None)
                and user.locked_until > timezone.now()
            )
        except UserModel.DoesNotExist:
            return False

    def is_locked(self, user_id: str) -> bool:
        """Alias for is_account_locked - used by Core MagicLinkService."""
        return self.is_account_locked(user_id)

    def is_active(self, user_id: str) -> bool:
        """Check if user account is active."""
        from tenxyte.models import get_user_model

        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(id=user_id)
            return user.is_active
        except UserModel.DoesNotExist:
            return False

    def lock_account(self, user_id: str, duration_minutes: int = 30) -> bool:
        """Lock user account."""
        # ... (rest of the code remains the same)
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.lock_account(duration_minutes)
            return True
        except (UserModel.DoesNotExist, AttributeError):
            return False

    def unlock_account(self, user_id: str) -> bool:
        """Unlock user account."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.unlock_account()
            return True
        except (UserModel.DoesNotExist, AttributeError):
            return False

    def record_failed_login(self, user_id: str) -> bool:
        """Record a failed login attempt and potentially lock the account."""
        try:
            from django.core.cache import cache

            # Use cache to track failed attempts
            cache_key = f"failed_login_{user_id}"
            attempts = cache.get(cache_key, 0) + 1
            cache.set(cache_key, attempts, timeout=1800)  # 30 minutes

            # Lock account after 5 failed attempts
            if attempts >= 5:
                self.lock_account(user_id, duration_minutes=30)

            return True
        except Exception:
            return False

    def hard_delete(self, user_id: str) -> bool:
        """Permanently delete user (GDPR right to erasure)."""
        try:
            django_user = UserModel.objects.get(id=user_id)
            django_user.delete(hard=True)
            return True
        except UserModel.DoesNotExist:
            return False


class DjangoOrganizationRepository(OrganizationRepository):
    """
    Django ORM implementation of OrganizationRepository.

    Adapts between the Core's Organization dataclass and Django's Organization model.

    Example:
        from tenxyte.adapters.django.repositories import DjangoOrganizationRepository

        repo = DjangoOrganizationRepository()
        org = repo.get_by_slug("acme-corp")
        if org:
            print(org.id, org.name)
    """

    def _to_core_org(self, django_org) -> Optional[Organization]:
        """Convert Django Organization model to Core Organization dataclass."""
        if django_org is None:
            return None

        return Organization(
            id=str(django_org.id),
            name=django_org.name,
            slug=django_org.slug,
            description=django_org.description or None,
            is_active=django_org.is_active,
            max_members=django_org.max_members,
            parent_id=str(django_org.parent_id) if django_org.parent_id else None,
            owner_id=str(django_org.created_by_id) if django_org.created_by_id else None,
            settings=django_org.metadata or {},
            created_at=getattr(django_org, "created_at", None),
            updated_at=getattr(django_org, "updated_at", None),
        )

    def get_by_id(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID."""
        try:
            django_org = OrganizationModel.objects.get(id=org_id)
            return self._to_core_org(django_org)
        except OrganizationModel.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        try:
            django_org = OrganizationModel.objects.get(slug=slug, is_active=True)
            return self._to_core_org(django_org)
        except OrganizationModel.DoesNotExist:
            return None

    def create(self, org: Organization) -> Organization:
        """Create a new organization."""
        django_org = OrganizationModel.objects.create(
            name=org.name,
            slug=org.slug,
            description=org.description or "",
            is_active=org.is_active,
            max_members=org.max_members,
            parent_id=org.parent_id,
            created_by_id=org.owner_id,
            metadata=org.settings or {},
        )
        return self._to_core_org(django_org)

    def update(self, org: Organization) -> Organization:
        """Update an existing organization."""
        try:
            django_org = OrganizationModel.objects.get(id=org.id)
        except OrganizationModel.DoesNotExist:
            raise ValueError(f"Organization with ID {org.id} not found")

        # Update fields
        if org.name:
            django_org.name = org.name
        if org.description is not None:
            django_org.description = org.description
        if org.is_active is not None:
            django_org.is_active = org.is_active
        if org.max_members is not None:
            django_org.max_members = org.max_members
        if org.settings is not None:
            django_org.metadata = org.settings

        django_org.save()
        return self._to_core_org(django_org)

    def delete(self, org_id: str) -> bool:
        """Soft delete an organization (mark as inactive)."""
        try:
            django_org = OrganizationModel.objects.get(id=org_id)
            django_org.is_active = False
            django_org.save(update_fields=["is_active"])
            return True
        except OrganizationModel.DoesNotExist:
            return False

    def list_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Organization]:
        """List organizations where user is an active member."""
        from tenxyte.models import get_organization_membership_model

        MembershipModel = get_organization_membership_model()

        # Get organization IDs where user is active member
        org_ids = MembershipModel.objects.filter(user_id=user_id, status="active").values_list(
            "organization_id", flat=True
        )

        # Get organizations
        orgs = OrganizationModel.objects.filter(id__in=org_ids, is_active=True)[skip : skip + limit]

        return [self._to_core_org(o) for o in orgs]

    def get_children(self, org_id: str) -> List[Organization]:
        """Get child organizations."""
        children = OrganizationModel.objects.filter(parent_id=org_id, is_active=True)
        return [self._to_core_org(o) for o in children]

    def add_member(self, org_id: str, user_id: str, role_id: str) -> bool:
        """Add a member to an organization."""
        from tenxyte.models import get_organization_membership_model

        MembershipModel = get_organization_membership_model()

        try:
            membership, created = MembershipModel.objects.get_or_create(
                organization_id=org_id, user_id=user_id, defaults={"role_id": role_id, "status": "active"}
            )
            if not created:
                # Update role if already exists
                membership.role_id = role_id
                membership.status = "active"
                membership.save()
            return True
        except Exception:
            return False

    def remove_member(self, org_id: str, user_id: str) -> bool:
        """Remove a member from an organization."""
        from tenxyte.models import get_organization_membership_model

        MembershipModel = get_organization_membership_model()

        try:
            membership = MembershipModel.objects.get(organization_id=org_id, user_id=user_id)
            membership.delete()
            return True
        except MembershipModel.DoesNotExist:
            return False

    # Django-specific extensions

    def get_ancestors(self, org_id: str) -> List[Organization]:
        """Get all ancestor organizations up to the root."""
        try:
            django_org = OrganizationModel.objects.get(id=org_id)
            ancestors = django_org.get_ancestors()
            return [self._to_core_org(a) for a in ancestors]
        except OrganizationModel.DoesNotExist:
            return []

    def get_descendants(self, org_id: str) -> List[Organization]:
        """Get all descendant organizations (recursive)."""
        try:
            django_org = OrganizationModel.objects.get(id=org_id)
            descendants = django_org.get_descendants()
            return [self._to_core_org(d) for d in descendants]
        except OrganizationModel.DoesNotExist:
            return []

    def get_member_count(self, org_id: str) -> int:
        """Get the number of active members in an organization."""
        try:
            django_org = OrganizationModel.objects.get(id=org_id)
            return django_org.get_member_count()
        except OrganizationModel.DoesNotExist:
            return 0

    def is_at_member_limit(self, org_id: str) -> bool:
        """Check if the organization is at its member limit."""
        try:
            django_org = OrganizationModel.objects.get(id=org_id)
            return django_org.is_at_member_limit()
        except OrganizationModel.DoesNotExist:
            return False


class DjangoRoleRepository(RoleRepository):
    """
    Django ORM implementation of RoleRepository.
    """

    def _to_core_role(self, django_role) -> Optional[Role]:
        if django_role is None:
            return None

        permissions = list(django_role.permissions.values_list("code", flat=True))

        return Role(
            id=str(django_role.id),
            name=django_role.name,
            slug=django_role.code,
            description=django_role.description,
            permissions=permissions,
            is_system=getattr(django_role, "is_default", False),
            created_at=getattr(django_role, "created_at", None),
        )

    def get_by_id(self, role_id: str) -> Optional[Role]:
        from tenxyte.models import get_role_model

        RoleModel = get_role_model()
        try:
            return self._to_core_role(RoleModel.objects.get(id=role_id))
        except RoleModel.DoesNotExist:
            return None

    def get_by_slug(self, slug: str, org_id: Optional[str] = None) -> Optional[Role]:
        from tenxyte.models import get_role_model

        RoleModel = get_role_model()
        try:
            return self._to_core_role(RoleModel.objects.get(code=slug))
        except RoleModel.DoesNotExist:
            return None

    def create(self, role: Role) -> Role:
        from tenxyte.models import get_role_model

        RoleModel = get_role_model()
        django_role = RoleModel.objects.create(
            code=role.slug, name=role.name, description=role.description or "", is_default=role.is_system
        )
        return self._to_core_role(django_role)

    def update(self, role: Role) -> Role:
        from tenxyte.models import get_role_model

        RoleModel = get_role_model()
        try:
            django_role = RoleModel.objects.get(id=role.id)
            django_role.name = role.name
            django_role.description = role.description or ""
            django_role.save()
            return self._to_core_role(django_role)
        except RoleModel.DoesNotExist:
            raise ValueError("Role not found")

    def delete(self, role_id: str) -> bool:
        from tenxyte.models import get_role_model

        RoleModel = get_role_model()
        try:
            RoleModel.objects.get(id=role_id).delete()
            return True
        except RoleModel.DoesNotExist:
            return False

    def list_by_organization(self, org_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Role]:
        from tenxyte.models import get_role_model

        RoleModel = get_role_model()
        roles = RoleModel.objects.all()[skip : skip + limit]
        return [self._to_core_role(r) for r in roles]

    def get_user_roles(self, user_id: str, org_id: Optional[str] = None) -> List[Role]:
        from tenxyte.models import get_user_model

        UserModel = get_user_model()
        try:
            user = UserModel.objects.prefetch_related("roles").get(id=user_id)
            return [self._to_core_role(r) for r in user.roles.all()]
        except (UserModel.DoesNotExist, AttributeError):
            return []


class DjangoAuditLogRepository(AuditLogRepository):
    """
    Django ORM implementation of AuditLogRepository.
    """

    def _to_core_audit(self, django_audit) -> Optional[AuditLog]:
        if django_audit is None:
            return None

        return AuditLog(
            id=str(django_audit.id),
            user_id=str(django_audit.user_id) if django_audit.user_id else None,
            action=django_audit.action,
            ip_address=django_audit.ip_address,
            user_agent=django_audit.user_agent,
            metadata=django_audit.details,
            created_at=django_audit.created_at,
        )

    def create(self, entry: AuditLog) -> AuditLog:
        from tenxyte.models import AuditLog as AuditLogModel

        django_audit = AuditLogModel.objects.create(
            user_id=entry.user_id,
            action=entry.action,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent or "",
            details=entry.metadata or {},
        )
        return self._to_core_audit(django_audit)

    def get_by_id(self, entry_id: str) -> Optional[AuditLog]:
        from tenxyte.models import AuditLog as AuditLogModel

        try:
            return self._to_core_audit(AuditLogModel.objects.get(id=entry_id))
        except AuditLogModel.DoesNotExist:
            return None

    def list_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        from tenxyte.models import AuditLog as AuditLogModel

        logs = AuditLogModel.objects.filter(user_id=user_id).order_by("-created_at")[skip : skip + limit]
        return [self._to_core_audit(log) for log in logs]

    def list_by_organization(self, org_id: str, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        # Implementation depends on how orgs are linked to audit logs
        return []

    def list_by_resource(self, resource_type: str, resource_id: str, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        return []

    def delete_old_entries(self, before_date: datetime) -> int:
        from tenxyte.models import AuditLog as AuditLogModel

        count, _ = AuditLogModel.objects.filter(created_at__lt=before_date).delete()
        return count

    def count_by_action(self, action: str, since: Optional[datetime] = None) -> int:
        from tenxyte.models import AuditLog as AuditLogModel

        qs = AuditLogModel.objects.filter(action=action)
        if since:
            qs = qs.filter(created_at__gte=since)
        return qs.count()


class DjangoMagicLinkRepository:
    """Django ORM implementation of MagicLink repository."""

    def get_by_token(self, token: str):
        """Get a valid magic link token by its token string."""
        from django.utils import timezone
        from tenxyte.models import MagicLinkToken
        import hashlib

        # Hash the token (Django stores SHA-256 hashes)
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        try:
            token_obj = MagicLinkToken.objects.get(token=hashed_token, is_used=False, expires_at__gt=timezone.now())
            from tenxyte.core.magic_link_service import MagicLinkToken as CoreMagicLinkToken

            return CoreMagicLinkToken(
                id=str(token_obj.id),
                token="",
                user_id=str(token_obj.user_id),
                email=token_obj.user.email,
                application_id=str(token_obj.application_id) if token_obj.application_id else None,
                ip_address=token_obj.ip_address,
                user_agent=token_obj.user_agent,
                created_at=token_obj.created_at,
                expires_at=token_obj.expires_at,
                used_at=token_obj.used_at,
                is_used=token_obj.is_used,
            )
        except MagicLinkToken.DoesNotExist:
            return None

    def create(
        self,
        token_hash: str,
        user_id: str,
        email: str,
        application_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expiry_minutes: int = 15,
    ):
        """Save a magic link token and return a CoreMagicLinkToken."""
        from tenxyte.models import MagicLinkToken
        from django.utils import timezone
        from datetime import timedelta
        from tenxyte.core.magic_link_service import MagicLinkToken as CoreMagicLinkToken

        token_obj = MagicLinkToken.objects.create(
            user_id=user_id,
            token=token_hash,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            ip_address=ip_address,
            user_agent=user_agent,
            application_id=application_id,
        )
        return CoreMagicLinkToken(
            id=str(token_obj.id),
            token="",
            user_id=str(token_obj.user_id),
            email=email,
            application_id=str(token_obj.application_id) if token_obj.application_id else None,
            ip_address=token_obj.ip_address,
            user_agent=token_obj.user_agent,
            created_at=token_obj.created_at,
            expires_at=token_obj.expires_at,
            used_at=token_obj.used_at,
            is_used=token_obj.is_used,
        )

    def consume(self, token_id: str) -> bool:
        """Mark a token as consumed."""
        from tenxyte.models import MagicLinkToken
        from django.utils import timezone

        try:
            token = MagicLinkToken.objects.get(id=token_id)
            token.is_used = True
            token.used_at = timezone.now()
            token.save(update_fields=["is_used", "used_at"])
            return True
        except MagicLinkToken.DoesNotExist:
            return False

    def invalidate_user_tokens(self, user_id: str, application_id: Optional[str] = None) -> int:
        """Invalidate all non-consumed tokens for a user."""
        from tenxyte.models import MagicLinkToken
        from django.utils import timezone

        query = MagicLinkToken.objects.filter(user_id=user_id, is_used=False)
        if application_id:
            query = query.filter(application_id=application_id)

        count = query.update(is_used=True, used_at=timezone.now())
        return count


__all__ = [
    "DjangoUserRepository",
    "DjangoOrganizationRepository",
    "DjangoRoleRepository",
    "DjangoAuditLogRepository",
    "DjangoMagicLinkRepository",
]
