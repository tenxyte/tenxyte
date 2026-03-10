"""
Tests multi-DB: opérations CRUD sur les modèles.

Vérifie que tous les modèles Tenxyte fonctionnent correctement
quel que soit le backend de base de données (SQLite, PostgreSQL, MySQL, MongoDB).
"""
import pytest
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

_is_mongodb = 'mongodb' in settings.DATABASES.get('default', {}).get('ENGINE', '')

from tenxyte.models import (
    User, Application, Permission, Role,
    RefreshToken, OTPCode, LoginAttempt,
    BlacklistedToken, AuditLog, PasswordHistory,
)


@pytest.mark.django_db
class TestUserCRUD:
    """CRUD complet sur le modèle User."""

    def test_create_user(self):
        user = User.objects.create_user(
            email='multidb@test.com',
            password='TestP@ss123!'
        )
        assert user.pk is not None
        assert user.email == 'multidb@test.com'
        assert user.is_active is True
        assert user.check_password('TestP@ss123!')

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@multidb.test',
            password='AdminP@ss123!'
        )
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_read_user(self):
        User.objects.create_user(email='read@test.com', password='P@ss123!')
        user = User.objects.get(email='read@test.com')
        assert user.email == 'read@test.com'

    def test_update_user(self):
        user = User.objects.create_user(email='update@test.com', password='P@ss123!')
        user.first_name = 'Updated'
        user.save()

        user.refresh_from_db()
        assert user.first_name == 'Updated'

    def test_delete_user(self):
        user = User.objects.create_user(email='delete@test.com', password='P@ss123!')
        user_id = user.pk
        user.delete()
        assert not User.objects.filter(pk=user_id).exists()

    def test_user_with_phone(self):
        user = User.objects.create_user(
            email='phone@test.com',
            password='P@ss123!',
            phone_country_code='33',
            phone_number='612345678'
        )
        assert user.full_phone == '+33612345678'

    def test_user_lock_unlock(self):
        user = User.objects.create_user(email='lock@test.com', password='P@ss123!')
        user.lock_account(duration_minutes=30)
        user.refresh_from_db()
        assert user.is_locked is True
        assert user.is_account_locked() is True

        user.unlock_account()
        user.refresh_from_db()
        assert user.is_locked is False
        assert user.is_account_locked() is False

    def test_user_email_unique(self):
        User.objects.create_user(email='unique@test.com', password='P@ss123!')
        with pytest.raises(Exception):
            User.objects.create_user(email='unique@test.com', password='Other123!')

    def test_user_queryset_filter(self):
        User.objects.create_user(email='active1@test.com', password='P@ss123!')
        User.objects.create_user(email='active2@test.com', password='P@ss123!')
        u3 = User.objects.create_user(email='inactive@test.com', password='P@ss123!')
        u3.is_active = False
        u3.save()

        active = User.objects.filter(is_active=True, email__endswith='@test.com')
        assert active.count() >= 2


@pytest.mark.django_db
class TestApplicationCRUD:
    """CRUD complet sur le modèle Application."""

    def test_create_application_factory(self):
        app, raw_secret = Application.create_application(
            name='MultiDB App',
            description='Test multi-DB'
        )
        assert app.pk is not None
        assert app.name == 'MultiDB App'
        assert raw_secret is not None
        assert app.verify_secret(raw_secret) is True

    def test_create_application_direct(self):
        import secrets
        app = Application.objects.create(
            name='Direct App',
            access_key=secrets.token_hex(32),
            access_secret='hashed_secret'
        )
        assert app.pk is not None
        assert app.is_active is True

    def test_update_application(self):
        app, _ = Application.create_application(name='Before')
        app.name = 'After'
        app.save()
        app.refresh_from_db()
        assert app.name == 'After'

    def test_deactivate_application(self):
        app, _ = Application.create_application(name='Deactivate')
        app.is_active = False
        app.save()
        app.refresh_from_db()
        assert app.is_active is False

    def test_application_access_key_unique(self):
        app1, _ = Application.create_application(name='App1')
        with pytest.raises(Exception):
            Application.objects.create(
                name='App2',
                access_key=app1.access_key,
                access_secret='other_secret'
            )

    def test_application_queryset(self):
        Application.create_application(name='Active1')
        Application.create_application(name='Active2')
        app3, _ = Application.create_application(name='Inactive')
        app3.is_active = False
        app3.save()

        active = Application.objects.filter(is_active=True)
        assert active.count() >= 2


@pytest.mark.django_db
class TestPermissionRoleCRUD:
    """CRUD sur Permission et Role + relations M2M."""

    def test_create_permission(self):
        perm = Permission.objects.create(code='db.test', name='DB Test')
        assert perm.pk is not None
        assert perm.code == 'db.test'

    def test_create_role(self):
        role = Role.objects.create(code='db_role', name='DB Role')
        assert role.pk is not None

    def test_role_permissions_m2m(self):
        perm1 = Permission.objects.create(code='m2m.read', name='Read')
        perm2 = Permission.objects.create(code='m2m.write', name='Write')
        role = Role.objects.create(code='m2m_role', name='M2M Role')

        role.permissions.add(perm1, perm2)
        assert role.permissions.count() == 2
        assert perm1 in role.permissions.all()

        if not _is_mongodb:
            # M2M remove/set unsupported on MongoDB (through tables lack integer PKs)
            role.permissions.remove(perm1)
            assert role.permissions.count() == 1

    def test_user_roles_m2m(self):
        user = User.objects.create_user(email='roles@test.com', password='P@ss123!')
        role1 = Role.objects.create(code='r1', name='Role 1')
        role2 = Role.objects.create(code='r2', name='Role 2')

        user.roles.add(role1, role2)
        assert user.roles.count() == 2

        if not _is_mongodb:
            # M2M remove unsupported on MongoDB (through tables lack integer PKs)
            user.roles.remove(role2)
            assert user.roles.count() == 1

    def test_permission_code_unique(self):
        Permission.objects.create(code='unique.perm', name='Unique')
        with pytest.raises(Exception):
            Permission.objects.create(code='unique.perm', name='Duplicate')


@pytest.mark.django_db
class TestRefreshTokenCRUD:
    """CRUD sur RefreshToken."""

    def _make_user_app(self):
        user = User.objects.create_user(email='rt@test.com', password='P@ss123!')
        app, _ = Application.create_application(name='RT App')
        return user, app

    def test_create_refresh_token(self):
        user, app = self._make_user_app()
        token = RefreshToken.objects.create(
            user=user,
            application=app,
            token='refresh_multidb_123',
            expires_at=timezone.now() + timedelta(days=30)
        )
        assert token.pk is not None
        assert token.is_valid() is True

    def test_refresh_token_expired(self):
        user, app = self._make_user_app()
        token = RefreshToken.objects.create(
            user=user,
            application=app,
            token='expired_token',
            expires_at=timezone.now() - timedelta(days=1)
        )
        assert token.is_valid() is False

    def test_refresh_token_revoked(self):
        user, app = self._make_user_app()
        token = RefreshToken.objects.create(
            user=user,
            application=app,
            token='revoked_token',
            expires_at=timezone.now() + timedelta(days=30),
            is_revoked=True
        )
        assert token.is_valid() is False

    def test_refresh_token_generate(self):
        user, app = self._make_user_app()
        token = RefreshToken.generate(
            user=user,
            application=app,
            device_info='pytest-multidb',
            ip_address='127.0.0.1'
        )
        assert token.pk is not None
        assert token.is_valid() is True

    def test_refresh_token_filter_by_user(self):
        user, app = self._make_user_app()
        RefreshToken.objects.create(
            user=user, application=app,
            token='t1', expires_at=timezone.now() + timedelta(days=30)
        )
        RefreshToken.objects.create(
            user=user, application=app,
            token='t2', expires_at=timezone.now() + timedelta(days=30)
        )
        assert RefreshToken.objects.filter(user=user).count() == 2


@pytest.mark.django_db
class TestOTPCodeCRUD:
    """CRUD sur OTPCode."""

    def test_generate_otp(self):
        user = User.objects.create_user(email='otp@test.com', password='P@ss123!')
        otp, raw_code = OTPCode.generate(user, 'email_verification', validity_minutes=10)

        assert otp.pk is not None
        assert len(raw_code) == 6
        assert otp.is_valid() is True
        assert otp.verify(raw_code) is True

    def test_otp_expired(self):
        user = User.objects.create_user(email='otp_exp@test.com', password='P@ss123!')
        otp, raw_code = OTPCode.generate(user, 'email_verification', validity_minutes=10)
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()
        assert otp.is_valid() is False

    def test_otp_wrong_code(self):
        user = User.objects.create_user(email='otp_wrong@test.com', password='P@ss123!')
        otp, raw_code = OTPCode.generate(user, 'email_verification', validity_minutes=10)
        assert otp.verify('000000') is False

    def test_otp_hash_stored(self):
        user = User.objects.create_user(email='otp_hash@test.com', password='P@ss123!')
        otp, raw_code = OTPCode.generate(user, 'email_verification', validity_minutes=10)
        assert otp.code != raw_code
        assert len(otp.code) == 64  # SHA-256


@pytest.mark.django_db
class TestLoginAttemptCRUD:
    """CRUD sur LoginAttempt."""

    def test_record_login_attempt(self):
        app, _ = Application.create_application(name='LA App')
        LoginAttempt.record(
            identifier='la@test.com',
            ip_address='192.168.1.1',
            application=app,
            success=False,
            failure_reason='Invalid password'
        )
        attempts = LoginAttempt.objects.filter(identifier='la@test.com')
        assert attempts.count() == 1
        assert attempts.first().success is False

    def test_record_multiple_attempts(self):
        app, _ = Application.create_application(name='LA App2')
        for i in range(5):
            LoginAttempt.record(
                identifier='multi@test.com',
                ip_address='192.168.1.1',
                application=app,
                success=(i == 4),
            )
        total = LoginAttempt.objects.filter(identifier='multi@test.com').count()
        failed = LoginAttempt.objects.filter(identifier='multi@test.com', success=False).count()
        assert total == 5
        assert failed == 4


@pytest.mark.django_db
class TestBlacklistedTokenCRUD:
    """CRUD sur BlacklistedToken."""

    def test_blacklist_token(self):
        user = User.objects.create_user(email='bl@test.com', password='P@ss123!')
        BlacklistedToken.objects.create(
            token_jti='test-jti-12345',
            user=user,
            expires_at=timezone.now() + timedelta(hours=1),
            reason='test'
        )
        assert BlacklistedToken.is_blacklisted('test-jti-12345') is True

    def test_not_blacklisted(self):
        assert BlacklistedToken.is_blacklisted('nonexistent-jti') is False


@pytest.mark.django_db
class TestAuditLogCRUD:
    """CRUD sur AuditLog."""

    def test_create_audit_log(self):
        user = User.objects.create_user(email='audit@test.com', password='P@ss123!')
        log = AuditLog.objects.create(
            user=user,
            action='login',
            ip_address='127.0.0.1',
            details={'method': 'email'}
        )
        assert log.pk is not None
        assert log.action == 'login'

    def test_audit_log_ordering(self):
        user = User.objects.create_user(email='order@test.com', password='P@ss123!')
        AuditLog.objects.create(user=user, action='login', ip_address='127.0.0.1')
        AuditLog.objects.create(user=user, action='logout', ip_address='127.0.0.1')

        logs = AuditLog.objects.filter(user=user)
        assert logs.count() == 2
        actions = list(logs.values_list('action', flat=True))
        assert 'login' in actions
        assert 'logout' in actions


@pytest.mark.django_db
class TestPasswordHistoryCRUD:
    """CRUD sur PasswordHistory."""

    def test_add_password_history(self):
        user = User.objects.create_user(email='pwh@test.com', password='P@ss123!')
        PasswordHistory.add_password(user, 'hashed_password_1')
        PasswordHistory.add_password(user, 'hashed_password_2')

        entries = PasswordHistory.objects.filter(user=user)
        assert entries.count() == 2
