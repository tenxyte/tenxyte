"""
Tests for Django Repository Adapters - targeting 100% coverage of
src/tenxyte/adapters/django/repositories.py

All Django ORM calls are mocked so no database is needed.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from tenxyte.adapters.django.repositories import (
    DjangoUserRepository,
    DjangoOrganizationRepository,
    DjangoRoleRepository,
    DjangoAuditLogRepository,
    DjangoMagicLinkRepository,
)
from tenxyte.ports.repositories import (
    User, Organization, Role, AuditLog, UserStatus, MFAType,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _mock_django_user(**overrides):
    """Helper: create a mock Django user model instance."""
    defaults = dict(
        id=1, email="test@example.com", password="hashed_pw",
        first_name="Test", last_name="User",
        is_active=True, is_superuser=False, is_staff=False,
        is_2fa_enabled=False, totp_secret=None,
        is_banned=False, is_locked=False, is_deleted=False,
        is_email_verified=True, email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_login=None,
        phone_country_code=None, phone_number=None,
        google_id=None, backup_codes=None,
        max_sessions=None, max_devices=None,
    )
    defaults.update(overrides)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _mock_django_org(**overrides):
    defaults = dict(
        id=10, name="Acme", slug="acme", description="desc",
        is_active=True, max_members=100, parent_id=None,
        created_by_id=1, metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _mock_django_role(**overrides):
    defaults = dict(
        id=20, name="Admin", code="admin", description="Admin role",
        is_default=False,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    m.permissions = MagicMock()
    m.permissions.values_list.return_value = ["read", "write"]
    return m


def _mock_django_audit(**overrides):
    defaults = dict(
        id=30, user_id=1, action="login",
        ip_address="1.2.3.4", user_agent="UA",
        details={"key": "val"},
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoUserRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoUserRepository:

    @pytest.fixture
    def repo(self):
        return DjangoUserRepository()

    # -- _to_core_user --

    def test_to_core_user_none(self, repo):
        assert repo._to_core_user(None) is None

    def test_to_core_user_active(self, repo):
        du = _mock_django_user()
        u = repo._to_core_user(du)
        assert u.id == "1"
        assert u.email == "test@example.com"
        assert u.status == UserStatus.ACTIVE
        assert u.mfa_type == MFAType.NONE

    def test_to_core_user_totp(self, repo):
        """2FA enabled + totp_secret → TOTP (lines 51-53)."""
        du = _mock_django_user(is_2fa_enabled=True, totp_secret="secret123")
        u = repo._to_core_user(du)
        assert u.mfa_type == MFAType.TOTP

    def test_to_core_user_inactive_banned(self, repo):
        """Inactive + banned → SUSPENDED (lines 57-59)."""
        du = _mock_django_user(is_active=False, is_banned=True)
        u = repo._to_core_user(du)
        assert u.status == UserStatus.SUSPENDED

    def test_to_core_user_inactive_locked(self, repo):
        """Inactive + locked → SUSPENDED (lines 60-61)."""
        du = _mock_django_user(is_active=False, is_locked=True)
        u = repo._to_core_user(du)
        assert u.status == UserStatus.SUSPENDED

    def test_to_core_user_inactive_plain(self, repo):
        """Inactive (not banned, not locked) → INACTIVE (lines 62-63)."""
        du = _mock_django_user(is_active=False, is_banned=False, is_locked=False)
        u = repo._to_core_user(du)
        assert u.status == UserStatus.INACTIVE

    def test_to_core_user_metadata(self, repo):
        """Metadata extraction with phone/google (line 84-101)."""
        du = _mock_django_user(phone_number="+1234567890", google_id="g-123")
        u = repo._to_core_user(du)
        assert u.metadata["phone_number"] == "+1234567890"
        assert u.metadata["google_id"] == "g-123"

    # -- get_by_id --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_get_by_id_found(self, MockUM, repo):
        mock_u = _mock_django_user()
        MockUM.objects.get.return_value = mock_u
        u = repo.get_by_id("1")
        assert u.email == "test@example.com"

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_get_by_id_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.get_by_id("999") is None

    # -- get_by_email --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_get_by_email_found(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        u = repo.get_by_email("test@example.com")
        assert u is not None

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_get_by_email_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.get_by_email("nope@x.com") is None

    # -- create --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_create_basic(self, MockUM, repo):
        mock_created = _mock_django_user()
        MockUM.objects.create_user.return_value = mock_created
        u = User(id="", email="new@x.com", password_hash=None, is_active=True,
                 is_superuser=False, is_staff=False, email_verified=True, mfa_type=MFAType.NONE)
        result = repo.create(u)
        assert result.email == "test@example.com"

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_create_with_password_and_mfa(self, MockUM, repo):
        """Lines 133-141: password_hash and mfa_secret set."""
        mock_created = _mock_django_user()
        MockUM.objects.create_user.return_value = mock_created
        u = User(id="", email="new@x.com", password_hash="hashed", is_active=True,
                 is_superuser=False, is_staff=False, email_verified=True,
                 mfa_type=MFAType.TOTP, mfa_secret="totp_sec")
        result = repo.create(u)
        mock_created.save.assert_called()

    # -- update --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_success(self, MockUM, repo):
        """Lines 147-178: update all fields."""
        mock_u = _mock_django_user()
        MockUM.objects.get.return_value = mock_u
        u = User(id="1", email="updated@x.com", password_hash="bcrypt_hash",
                 first_name="A", last_name="B", is_active=True,
                 is_superuser=False, is_staff=False, email_verified=True,
                 mfa_type=MFAType.TOTP, mfa_secret="sec")
        result = repo.update(u)
        assert result is not None

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_plain_password(self, MockUM, repo):
        """Lines 165-168: non-hash password calls set_password."""
        mock_u = _mock_django_user()
        MockUM.objects.get.return_value = mock_u
        u = User(id="1", email="e@x.com", password_hash="plaintext",
                 is_active=True, is_superuser=False, is_staff=False)
        repo.update(u)
        mock_u.set_password.assert_called_once_with("plaintext")

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_not_found(self, MockUM, repo):
        """Lines 149-150: user not found raises ValueError."""
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        u = User(id="999", email="e@x.com", is_active=True, is_superuser=False, is_staff=False)
        with pytest.raises(ValueError):
            repo.update(u)

    # -- update_user --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_user_success(self, MockUM, repo):
        """Lines 184-200."""
        mock_u = _mock_django_user()
        MockUM.objects.get.return_value = mock_u
        result = repo.update_user("1", {
            "first_name": "New", "last_name": "Name",
            "email": "e@x.com", "is_active": False,
            "is_email_verified": True,
        })
        assert result is not None

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_user_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.update_user("999", {}) is None

    # -- delete / soft_delete --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_delete_success(self, MockUM, repo):
        mock_u = _mock_django_user()
        MockUM.objects.get.return_value = mock_u
        assert repo.delete("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_delete_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.delete("999") is False

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_soft_delete(self, MockUM, repo):
        mock_u = _mock_django_user()
        MockUM.objects.get.return_value = mock_u
        assert repo.soft_delete("1") is True

    # -- ban / unban --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_ban_with_method(self, MockUM, repo):
        mock_u = _mock_django_user()
        mock_u.ban_account = MagicMock()
        MockUM.objects.get.return_value = mock_u
        assert repo.ban("1", "reason") is True
        mock_u.ban_account.assert_called_once()

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_ban_fallback(self, MockUM, repo):
        mock_u = _mock_django_user()
        del mock_u.ban_account  # remove method
        MockUM.objects.get.return_value = mock_u
        assert repo.ban("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_ban_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.ban("999") is False

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unban_with_method(self, MockUM, repo):
        mock_u = _mock_django_user()
        mock_u.unban_account = MagicMock()
        MockUM.objects.get.return_value = mock_u
        assert repo.unban("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unban_fallback(self, MockUM, repo):
        mock_u = _mock_django_user()
        del mock_u.unban_account
        MockUM.objects.get.return_value = mock_u
        assert repo.unban("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unban_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.unban("999") is False

    # -- lock / unlock --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_lock_with_method(self, MockUM, repo):
        mock_u = _mock_django_user()
        mock_u.lock_account = MagicMock()
        MockUM.objects.get.return_value = mock_u
        assert repo.lock("1", 30) is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_lock_fallback(self, MockUM, repo):
        mock_u = _mock_django_user()
        del mock_u.lock_account
        MockUM.objects.get.return_value = mock_u
        assert repo.lock("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_lock_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.lock("999") is False

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unlock_with_method(self, MockUM, repo):
        mock_u = _mock_django_user()
        mock_u.unlock_account = MagicMock()
        MockUM.objects.get.return_value = mock_u
        assert repo.unlock("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unlock_fallback(self, MockUM, repo):
        mock_u = _mock_django_user()
        del mock_u.unlock_account
        MockUM.objects.get.return_value = mock_u
        assert repo.unlock("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unlock_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.unlock("999") is False

    # -- list_all --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_list_all_no_filters(self, MockUM, repo):
        qs = MagicMock()
        qs.__getitem__ = MagicMock(return_value=[_mock_django_user()])
        MockUM.objects.filter.return_value = qs
        result = repo.list_all()
        assert len(result) == 1

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_list_all_with_filters(self, MockUM, repo):
        """Lines 280-287: all filter branches."""
        qs = MagicMock()
        qs.filter.return_value = qs
        qs.__getitem__ = MagicMock(return_value=[])
        MockUM.objects.filter.return_value = qs
        result = repo.list_all(filters={
            "is_active": True, "is_staff": False,
            "is_email_verified": True, "is_2fa_enabled": False,
        })
        assert result == []

    # -- count --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_count_no_filters(self, MockUM, repo):
        qs = MagicMock()
        qs.count.return_value = 5
        MockUM.objects.filter.return_value = qs
        assert repo.count() == 5

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_count_with_filters(self, MockUM, repo):
        qs = MagicMock()
        qs.filter.return_value = qs
        qs.count.return_value = 2
        MockUM.objects.filter.return_value = qs
        assert repo.count(filters={"is_active": True, "is_staff": True}) == 2

    # -- update_last_login --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_last_login_success(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        assert repo.update_last_login("1", datetime.now(timezone.utc)) is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_last_login_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.update_last_login("x", None) is False

    # -- set_mfa_secret --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_set_mfa_secret_success(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        assert repo.set_mfa_secret("1", MFAType.TOTP, "sec") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_set_mfa_secret_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.set_mfa_secret("x", MFAType.NONE, "") is False

    # -- verify_email --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_verify_email_success(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        assert repo.verify_email("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_verify_email_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.verify_email("x") is False

    # -- enable_mfa / disable_mfa --

    def test_enable_mfa_success(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = _mock_django_user()
            assert repo.enable_mfa("1", "totp") is True

    def test_enable_mfa_not_found(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert repo.enable_mfa("x", "totp") is False

    def test_disable_mfa_success(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = _mock_django_user()
            assert repo.disable_mfa("1") is True

    def test_disable_mfa_not_found(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert repo.disable_mfa("x") is False

    # -- get_by_google_id --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_get_by_google_id_found(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        result = repo.get_by_google_id("g-123")
        assert result is not None

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_get_by_google_id_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.get_by_google_id("bad") is None

    # -- check_password / set_password / update_password --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_check_password(self, MockUM, repo):
        mock_u = _mock_django_user()
        mock_u.check_password.return_value = True
        MockUM.objects.get.return_value = mock_u
        assert repo.check_password("1", "pass") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_set_password_success(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        assert repo.set_password("1", "newpass") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_set_password_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.set_password("x", "p") is False

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_update_password(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        assert repo.update_password("1", "p") is True

    # -- is_account_locked --

    def test_is_account_locked_cache_hit(self, repo):
        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = True
            assert repo.is_account_locked("1") is True

    def test_is_account_locked_has_method(self, repo):
        with patch("django.core.cache.cache") as mock_cache, \
             patch("tenxyte.models.get_user_model") as gum:
            mock_cache.get.return_value = None
            MockUM = MagicMock()
            gum.return_value = MockUM
            mock_u = _mock_django_user()
            mock_u.is_account_locked = MagicMock(return_value=True)
            MockUM.objects.get.return_value = mock_u
            assert repo.is_account_locked("1") is True

    def test_is_account_locked_fallback(self, repo):
        """Lines 408-409: fallback to is_locked + locked_until."""
        with patch("django.core.cache.cache") as mock_cache, \
             patch("tenxyte.models.get_user_model") as gum:
            mock_cache.get.return_value = None
            MockUM = MagicMock()
            gum.return_value = MockUM
            mock_u = MagicMock(spec=[])
            mock_u.is_locked = True
            mock_u.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
            MockUM.objects.get.return_value = mock_u
            with patch("django.utils.timezone.now", return_value=datetime.now(timezone.utc)):
                assert repo.is_account_locked("1") is True

    def test_is_account_locked_not_found(self, repo):
        with patch("django.core.cache.cache") as mock_cache, \
             patch("tenxyte.models.get_user_model") as gum:
            mock_cache.get.return_value = None
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert repo.is_account_locked("999") is False

    def test_is_locked_alias(self, repo):
        with patch.object(repo, "is_account_locked", return_value=True):
            assert repo.is_locked("1") is True

    # -- is_active --

    def test_is_active_true(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            mock_u = MagicMock()
            mock_u.is_active = True
            MockUM.objects.get.return_value = mock_u
            assert repo.is_active("1") is True

    def test_is_active_not_found(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert repo.is_active("999") is False

    # -- lock_account / unlock_account --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_lock_account_success(self, MockUM, repo):
        mock_u = _mock_django_user()
        mock_u.lock_account = MagicMock()
        MockUM.objects.get.return_value = mock_u
        assert repo.lock_account("1", 30) is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_lock_account_fail(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.lock_account("x") is False

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unlock_account_success(self, MockUM, repo):
        mock_u = _mock_django_user()
        mock_u.unlock_account = MagicMock()
        MockUM.objects.get.return_value = mock_u
        assert repo.unlock_account("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_unlock_account_fail(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.unlock_account("x") is False

    # -- record_failed_login --

    def test_record_failed_login_below_threshold(self, repo):
        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = 2
            assert repo.record_failed_login("1") is True

    def test_record_failed_login_lock_triggered(self, repo):
        """Line 458: attempts >= 5 triggers lock."""
        with patch("django.core.cache.cache") as mock_cache, \
             patch.object(repo, "lock_account") as mock_lock:
            mock_cache.get.return_value = 4  # 4 + 1 = 5
            assert repo.record_failed_login("1") is True
            mock_lock.assert_called_once()

    def test_record_failed_login_exception(self, repo):
        """Line 461-462: exception returns False."""
        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.side_effect = Exception("redis down")
            assert repo.record_failed_login("1") is False

    # -- hard_delete --

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_hard_delete_success(self, MockUM, repo):
        MockUM.objects.get.return_value = _mock_django_user()
        assert repo.hard_delete("1") is True

    @patch("tenxyte.adapters.django.repositories.UserModel")
    def test_hard_delete_not_found(self, MockUM, repo):
        MockUM.DoesNotExist = Exception
        MockUM.objects.get.side_effect = Exception()
        assert repo.hard_delete("x") is False


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoOrganizationRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoOrganizationRepository:

    @pytest.fixture
    def repo(self):
        return DjangoOrganizationRepository()

    def test_to_core_org_none(self, repo):
        assert repo._to_core_org(None) is None

    def test_to_core_org_full(self, repo):
        do = _mock_django_org()
        org = repo._to_core_org(do)
        assert org.id == "10"
        assert org.slug == "acme"

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_by_id_found(self, MockOM, repo):
        MockOM.objects.get.return_value = _mock_django_org()
        assert repo.get_by_id("10") is not None

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_by_id_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        assert repo.get_by_id("x") is None

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_by_slug_found(self, MockOM, repo):
        MockOM.objects.get.return_value = _mock_django_org()
        assert repo.get_by_slug("acme") is not None

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_by_slug_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        assert repo.get_by_slug("x") is None

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_create(self, MockOM, repo):
        MockOM.objects.create.return_value = _mock_django_org()
        org = Organization(id="", name="New", slug="new", is_active=True, max_members=10)
        result = repo.create(org)
        assert result.name == "Acme"

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_update_success(self, MockOM, repo):
        MockOM.objects.get.return_value = _mock_django_org()
        org = Organization(id="10", name="Updated", slug="acme", description="d",
                           is_active=True, max_members=50, settings={"k": "v"})
        result = repo.update(org)
        assert result is not None

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_update_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        org = Organization(id="x", name="X", slug="x", is_active=True)
        with pytest.raises(ValueError):
            repo.update(org)

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_delete_success(self, MockOM, repo):
        MockOM.objects.get.return_value = _mock_django_org()
        assert repo.delete("10") is True

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_delete_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        assert repo.delete("x") is False

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_list_by_user(self, MockOM, repo):
        with patch("tenxyte.models.get_organization_membership_model") as gmm:
            MockMM = MagicMock()
            gmm.return_value = MockMM
            MockMM.objects.filter.return_value.values_list.return_value = [10]
            qs = MagicMock()
            qs.__getitem__ = MagicMock(return_value=[_mock_django_org()])
            MockOM.objects.filter.return_value = qs
            result = repo.list_by_user("1")
            assert len(result) == 1

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_children(self, MockOM, repo):
        MockOM.objects.filter.return_value = [_mock_django_org()]
        result = repo.get_children("10")
        assert len(result) == 1

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_add_member_new(self, MockOM, repo):
        with patch("tenxyte.models.get_organization_membership_model") as gmm:
            MockMM = MagicMock()
            gmm.return_value = MockMM
            MockMM.objects.get_or_create.return_value = (MagicMock(), True)
            assert repo.add_member("10", "1", "20") is True

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_add_member_existing(self, MockOM, repo):
        """Lines 618-622: existing membership updated."""
        with patch("tenxyte.models.get_organization_membership_model") as gmm:
            MockMM = MagicMock()
            gmm.return_value = MockMM
            existing = MagicMock()
            MockMM.objects.get_or_create.return_value = (existing, False)
            assert repo.add_member("10", "1", "20") is True
            existing.save.assert_called_once()

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_add_member_exception(self, MockOM, repo):
        with patch("tenxyte.models.get_organization_membership_model") as gmm:
            MockMM = MagicMock()
            gmm.return_value = MockMM
            MockMM.objects.get_or_create.side_effect = Exception()
            assert repo.add_member("10", "1", "20") is False

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_remove_member_success(self, MockOM, repo):
        with patch("tenxyte.models.get_organization_membership_model") as gmm:
            MockMM = MagicMock()
            gmm.return_value = MockMM
            MockMM.objects.get.return_value = MagicMock()
            assert repo.remove_member("10", "1") is True

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_remove_member_not_found(self, MockOM, repo):
        with patch("tenxyte.models.get_organization_membership_model") as gmm:
            MockMM = MagicMock()
            gmm.return_value = MockMM
            MockMM.DoesNotExist = Exception
            MockMM.objects.get.side_effect = Exception()
            assert repo.remove_member("10", "1") is False

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_ancestors(self, MockOM, repo):
        mock_org = _mock_django_org()
        mock_org.get_ancestors.return_value = [_mock_django_org(id=5)]
        MockOM.objects.get.return_value = mock_org
        result = repo.get_ancestors("10")
        assert len(result) == 1

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_ancestors_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        assert repo.get_ancestors("x") == []

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_descendants(self, MockOM, repo):
        mock_org = _mock_django_org()
        mock_org.get_descendants.return_value = [_mock_django_org(id=15)]
        MockOM.objects.get.return_value = mock_org
        result = repo.get_descendants("10")
        assert len(result) == 1

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_descendants_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        assert repo.get_descendants("x") == []

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_member_count(self, MockOM, repo):
        mock_org = _mock_django_org()
        mock_org.get_member_count.return_value = 42
        MockOM.objects.get.return_value = mock_org
        assert repo.get_member_count("10") == 42

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_get_member_count_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        assert repo.get_member_count("x") == 0

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_is_at_member_limit(self, MockOM, repo):
        mock_org = _mock_django_org()
        mock_org.is_at_member_limit.return_value = True
        MockOM.objects.get.return_value = mock_org
        assert repo.is_at_member_limit("10") is True

    @patch("tenxyte.adapters.django.repositories.OrganizationModel")
    def test_is_at_member_limit_not_found(self, MockOM, repo):
        MockOM.DoesNotExist = Exception
        MockOM.objects.get.side_effect = Exception()
        assert repo.is_at_member_limit("x") is False


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoRoleRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoRoleRepository:

    @pytest.fixture
    def repo(self):
        return DjangoRoleRepository()

    def test_to_core_role_none(self, repo):
        assert repo._to_core_role(None) is None

    def test_to_core_role_full(self, repo):
        dr = _mock_django_role()
        r = repo._to_core_role(dr)
        assert r.id == "20"
        assert r.slug == "admin"

    def test_get_by_id(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            grm.return_value = MockRM
            MockRM.objects.get.return_value = _mock_django_role()
            assert repo.get_by_id("20") is not None

    def test_get_by_id_not_found(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            MockRM.DoesNotExist = Exception
            grm.return_value = MockRM
            MockRM.objects.get.side_effect = Exception()
            assert repo.get_by_id("x") is None

    def test_get_by_slug(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            grm.return_value = MockRM
            MockRM.objects.get.return_value = _mock_django_role()
            assert repo.get_by_slug("admin") is not None

    def test_get_by_slug_not_found(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            MockRM.DoesNotExist = Exception
            grm.return_value = MockRM
            MockRM.objects.get.side_effect = Exception()
            assert repo.get_by_slug("x") is None

    def test_create(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            grm.return_value = MockRM
            MockRM.objects.create.return_value = _mock_django_role()
            r = Role(id="", name="R", slug="r", permissions=[])
            result = repo.create(r)
            assert result.name == "Admin"

    def test_update_success(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            grm.return_value = MockRM
            MockRM.objects.get.return_value = _mock_django_role()
            r = Role(id="20", name="Updated", slug="admin", permissions=[])
            result = repo.update(r)
            assert result is not None

    def test_update_not_found(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            MockRM.DoesNotExist = Exception
            grm.return_value = MockRM
            MockRM.objects.get.side_effect = Exception()
            r = Role(id="x", name="X", slug="x", permissions=[])
            with pytest.raises(ValueError):
                repo.update(r)

    def test_delete_success(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            grm.return_value = MockRM
            MockRM.objects.get.return_value = MagicMock()
            assert repo.delete("20") is True

    def test_delete_not_found(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            MockRM.DoesNotExist = Exception
            grm.return_value = MockRM
            MockRM.objects.get.side_effect = Exception()
            assert repo.delete("x") is False

    def test_list_by_organization(self, repo):
        with patch("tenxyte.models.get_role_model") as grm:
            MockRM = MagicMock()
            grm.return_value = MockRM
            qs = MagicMock()
            qs.__getitem__ = MagicMock(return_value=[_mock_django_role()])
            MockRM.objects.all.return_value = qs
            result = repo.list_by_organization()
            assert len(result) == 1

    def test_get_user_roles(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            mock_u = MagicMock()
            mock_u.roles.all.return_value = [_mock_django_role()]
            MockUM.objects.prefetch_related.return_value.get.return_value = mock_u
            result = repo.get_user_roles("1")
            assert len(result) == 1

    def test_get_user_roles_not_found(self, repo):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.prefetch_related.return_value.get.side_effect = Exception()
            assert repo.get_user_roles("x") == []


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoAuditLogRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoAuditLogRepository:

    @pytest.fixture
    def repo(self):
        return DjangoAuditLogRepository()

    def test_to_core_audit_none(self, repo):
        assert repo._to_core_audit(None) is None

    def test_to_core_audit_full(self, repo):
        da = _mock_django_audit()
        a = repo._to_core_audit(da)
        assert a.id == "30"
        assert a.action == "login"

    def test_create(self, repo):
        with patch("tenxyte.models.AuditLog") as MockAL:
            MockAL.objects.create.return_value = _mock_django_audit()
            entry = AuditLog(
                id="", user_id="1", action="login",
                ip_address="1.2.3.4", user_agent="UA", metadata={"k": "v"}
            )
            result = repo.create(entry)
            assert result.action == "login"

    def test_get_by_id_found(self, repo):
        with patch("tenxyte.models.AuditLog") as MockAL:
            MockAL.objects.get.return_value = _mock_django_audit()
            assert repo.get_by_id("30") is not None

    def test_get_by_id_not_found(self, repo):
        with patch("tenxyte.models.AuditLog") as MockAL:
            MockAL.DoesNotExist = Exception
            MockAL.objects.get.side_effect = Exception()
            assert repo.get_by_id("x") is None

    def test_list_by_user(self, repo):
        with patch("tenxyte.models.AuditLog") as MockAL:
            qs = MagicMock()
            qs.__getitem__ = MagicMock(return_value=[_mock_django_audit()])
            MockAL.objects.filter.return_value.order_by.return_value = qs
            result = repo.list_by_user("1")
            assert len(result) == 1

    def test_list_by_organization(self, repo):
        assert repo.list_by_organization("10") == []

    def test_list_by_resource(self, repo):
        assert repo.list_by_resource("type", "id") == []

    def test_delete_old_entries(self, repo):
        with patch("tenxyte.models.AuditLog") as MockAL:
            MockAL.objects.filter.return_value.delete.return_value = (5, {})
            assert repo.delete_old_entries(datetime.now(timezone.utc)) == 5

    def test_count_by_action_no_since(self, repo):
        with patch("tenxyte.models.AuditLog") as MockAL:
            MockAL.objects.filter.return_value.count.return_value = 3
            assert repo.count_by_action("login") == 3

    def test_count_by_action_with_since(self, repo):
        with patch("tenxyte.models.AuditLog") as MockAL:
            qs = MagicMock()
            qs.filter.return_value = qs
            qs.count.return_value = 2
            MockAL.objects.filter.return_value = qs
            assert repo.count_by_action("login", since=datetime.now(timezone.utc)) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoMagicLinkRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoMagicLinkRepository:

    @pytest.fixture
    def repo(self):
        return DjangoMagicLinkRepository()

    def test_get_by_token_found(self, repo):
        with patch("tenxyte.models.MagicLinkToken") as MockML:
            mock_token = MagicMock()
            mock_token.id = 100
            mock_token.user_id = 1
            mock_token.user.email = "u@x.com"
            mock_token.application_id = None
            mock_token.ip_address = "1.2.3.4"
            mock_token.user_agent = "UA"
            mock_token.created_at = datetime.now(timezone.utc)
            mock_token.expires_at = datetime.now(timezone.utc)
            mock_token.used_at = None
            mock_token.is_used = False
            MockML.objects.get.return_value = mock_token
            with patch("tenxyte.core.magic_link_service.MagicLinkToken") as CoreMLT:
                CoreMLT.return_value = MagicMock()
                result = repo.get_by_token("abc123")
                assert result is not None

    def test_get_by_token_not_found(self, repo):
        with patch("tenxyte.models.MagicLinkToken") as MockML:
            MockML.DoesNotExist = Exception
            MockML.objects.get.side_effect = Exception()
            assert repo.get_by_token("bad") is None

    def test_create(self, repo):
        with patch("tenxyte.models.MagicLinkToken") as MockML, \
             patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = datetime.now(timezone.utc)
            mock_token = MagicMock()
            mock_token.id = 101
            mock_token.user_id = 1
            mock_token.application_id = 5
            mock_token.ip_address = "1.1.1.1"
            mock_token.user_agent = "UA"
            mock_token.created_at = datetime.now(timezone.utc)
            mock_token.expires_at = datetime.now(timezone.utc)
            mock_token.used_at = None
            mock_token.is_used = False
            MockML.objects.create.return_value = mock_token
            with patch("tenxyte.core.magic_link_service.MagicLinkToken") as CoreMLT:
                CoreMLT.return_value = MagicMock()
                result = repo.create(
                    token_hash="hash", user_id="1", email="u@x.com",
                    application_id="5", ip_address="1.1.1.1", user_agent="UA"
                )
                assert result is not None

    def test_consume_success(self, repo):
        with patch("tenxyte.models.MagicLinkToken") as MockML:
            MockML.objects.get.return_value = MagicMock()
            with patch("django.utils.timezone.now"):
                assert repo.consume("100") is True

    def test_consume_not_found(self, repo):
        with patch("tenxyte.models.MagicLinkToken") as MockML:
            MockML.DoesNotExist = Exception
            MockML.objects.get.side_effect = Exception()
            assert repo.consume("x") is False

    def test_invalidate_user_tokens_no_app(self, repo):
        with patch("tenxyte.models.MagicLinkToken") as MockML, \
             patch("django.utils.timezone.now"):
            MockML.objects.filter.return_value.update.return_value = 3
            assert repo.invalidate_user_tokens("1") == 3

    def test_invalidate_user_tokens_with_app(self, repo):
        """Line 915-916: with application_id filter."""
        with patch("tenxyte.models.MagicLinkToken") as MockML, \
             patch("django.utils.timezone.now"):
            qs = MagicMock()
            qs.filter.return_value = qs
            qs.update.return_value = 2
            MockML.objects.filter.return_value = qs
            assert repo.invalidate_user_tokens("1", application_id="5") == 2
