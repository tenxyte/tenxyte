"""
Tests multi-DB: flux d'authentification complet.

Vérifie que le flow auth end-to-end (register → login → JWT → refresh → logout)
fonctionne correctement quel que soit le backend DB.
"""
import pytest
from django.conf import settings
from django.core.cache import cache

_is_mongodb = 'mongodb' in settings.DATABASES.get('default', {}).get('ENGINE', '')

from tenxyte.models import User, Application, RefreshToken
from tenxyte.services import AuthService, JWTService
from tenxyte.services.otp_service import OTPService
from tenxyte.services import TOTPService


@pytest.mark.django_db
class TestAuthFlowMultiDB:
    """Flow complet d'authentification sur chaque backend."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Créer les données de base pour chaque test."""
        self.app, self.raw_secret = Application.create_application(
            name='AuthFlow App',
            description='Test auth flow'
        )
        self.user = User.objects.create_user(
            email='authflow@test.com',
            password='AuthP@ss123!'
        )
        self.auth_service = AuthService()
        self.jwt_service = JWTService()

    def test_authenticate_by_email(self):
        """Test auth par email → tokens générés."""
        success, data, error = self.auth_service.authenticate_by_email(
            email='authflow@test.com',
            password='AuthP@ss123!',
            application=self.app,
            ip_address='127.0.0.1'
        )
        assert success is True
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert error == ''

    def test_authenticate_wrong_password(self):
        """Test auth avec mauvais mot de passe."""
        success, data, error = self.auth_service.authenticate_by_email(
            email='authflow@test.com',
            password='WrongPassword!',
            application=self.app,
            ip_address='127.0.0.1'
        )
        assert success is False
        assert error != ''

    def test_authenticate_nonexistent_user(self):
        """Test auth avec utilisateur inexistant."""
        success, data, error = self.auth_service.authenticate_by_email(
            email='ghost@test.com',
            password='AuthP@ss123!',
            application=self.app,
            ip_address='127.0.0.1'
        )
        assert success is False

    def test_jwt_generate_decode_cycle(self):
        """Test cycle complet: generate → decode → validate."""
        token, jti, expires_at = self.jwt_service.generate_access_token(
            user_id=str(self.user.pk),
            application_id=str(self.app.pk)
        )

        payload = self.jwt_service.decode_token(token)
        assert payload is not None
        assert payload['user_id'] == str(self.user.pk)
        assert payload['app_id'] == str(self.app.pk)
        assert self.jwt_service.is_token_valid(token) is True

    def test_jwt_blacklist(self):
        """Test blacklisting d'un token."""
        token, jti, expires_at = self.jwt_service.generate_access_token(
            user_id=str(self.user.pk),
            application_id=str(self.app.pk)
        )
        assert self.jwt_service.is_token_valid(token) is True

        self.jwt_service.blacklist_token(token, user=self.user, reason='multidb_test')

        assert self.jwt_service.is_token_valid(token) is False

    def test_refresh_token_lifecycle(self):
        """Test cycle refresh token: create → validate → revoke."""
        success, data, _ = self.auth_service.authenticate_by_email(
            email='authflow@test.com',
            password='AuthP@ss123!',
            application=self.app,
            ip_address='127.0.0.1'
        )
        assert success

        # Le refresh token doit être valide en DB
        rt = RefreshToken.objects.filter(user=self.user, application=self.app).first()
        assert rt is not None
        assert rt.is_valid() is True

        # Révoquer
        rt.revoke()
        rt.refresh_from_db()
        assert rt.is_valid() is False

    def test_multiple_applications_isolation(self):
        """Test que les tokens sont isolés entre applications."""
        app_b, secret_b = Application.create_application(name='App B')

        success_a, data_a, _ = self.auth_service.authenticate_by_email(
            email='authflow@test.com',
            password='AuthP@ss123!',
            application=self.app,
            ip_address='127.0.0.1'
        )
        success_b, data_b, _ = self.auth_service.authenticate_by_email(
            email='authflow@test.com',
            password='AuthP@ss123!',
            application=app_b,
            ip_address='127.0.0.1'
        )
        assert success_a and success_b

        # Les tokens doivent être différents
        assert data_a['access_token'] != data_b['access_token']
        assert data_a['refresh_token'] != data_b['refresh_token']

        # Les payloads doivent référencer la bonne application
        payload_a = self.jwt_service.decode_token(data_a['access_token'])
        payload_b = self.jwt_service.decode_token(data_b['access_token'])
        assert payload_a['app_id'] == str(self.app.pk)
        assert payload_b['app_id'] == str(app_b.pk)


@pytest.mark.django_db
class TestOTPFlowMultiDB:
    """Flow OTP sur chaque backend."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
            email='otp_flow@test.com',
            password='OTPP@ss123!'
        )
        self.otp_service = OTPService()

    def test_email_otp_generate_verify(self):
        """Test cycle OTP email: generate → verify."""
        otp, raw_code = self.otp_service.generate_email_verification_otp(self.user)
        assert otp.is_valid() is True

        is_valid, error = self.otp_service.verify_email_otp(self.user, raw_code)
        assert is_valid is True

        self.user.refresh_from_db()
        assert self.user.is_email_verified is True

    def test_password_reset_otp(self):
        """Test cycle OTP password reset."""
        otp, raw_code = self.otp_service.generate_password_reset_otp(self.user)

        is_valid, error = self.otp_service.verify_password_reset_otp(self.user, raw_code)
        assert is_valid is True

    def test_otp_invalidation(self):
        """Un nouveau OTP doit invalider l'ancien."""
        otp1, code1 = self.otp_service.generate_email_verification_otp(self.user)
        otp2, code2 = self.otp_service.generate_email_verification_otp(self.user)

        otp1.refresh_from_db()
        assert otp1.is_used is True
        assert otp2.is_used is False


@pytest.mark.django_db
class TestTOTPMultiDB:
    """2FA TOTP sur chaque backend."""

    def test_setup_and_verify_2fa(self):
        """Test setup 2FA complet."""
        import pyotp

        user = User.objects.create_user(email='totp@test.com', password='TOTPP@ss123!')
        totp_service = TOTPService()

        # Générer secret
        secret = totp_service.generate_secret()
        user.totp_secret = secret
        user.save()

        # Vérifier un code valide
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        assert totp_service.verify_code(secret, valid_code) is True

        # Activer 2FA
        user.is_2fa_enabled = True
        user.save()
        user.refresh_from_db()
        assert user.is_2fa_enabled is True
        assert user.totp_secret == secret

    def test_backup_codes_stored(self):
        """Test que les backup codes peuvent être stockés et récupérés."""
        import json

        user = User.objects.create_user(email='backup@test.com', password='BackP@ss123!')
        totp_service = TOTPService()

        plain_codes, hashed_codes = totp_service.generate_backup_codes()

        # Stocker les codes hashés dans le user
        user.backup_codes = json.dumps(hashed_codes)
        user.save()

        user.refresh_from_db()
        stored = json.loads(user.backup_codes)
        assert len(stored) == len(hashed_codes)
        assert stored == hashed_codes


@pytest.mark.django_db
class TestRBACMultiDB:
    """RBAC (rôles et permissions) sur chaque backend."""

    def test_user_roles_permissions_chain(self):
        """Test chaîne complète: Permission → Role → User."""
        from tenxyte.models import Permission, Role

        # Créer permissions
        p_read = Permission.objects.create(code='multi.read', name='Read')
        p_write = Permission.objects.create(code='multi.write', name='Write')
        p_delete = Permission.objects.create(code='multi.delete', name='Delete')

        # Créer rôles
        editor = Role.objects.create(code='multi_editor', name='Editor')
        editor.permissions.add(p_read, p_write)

        admin = Role.objects.create(code='multi_admin', name='Admin')
        admin.permissions.add(p_read, p_write, p_delete)

        # Assigner rôles à l'utilisateur
        user = User.objects.create_user(email='rbac@test.com', password='P@ss123!')
        user.roles.add(editor)

        assert user.roles.count() == 1
        assert editor.permissions.count() == 2

        # Promouvoir
        user.roles.add(admin)
        assert user.roles.count() == 2

        # Vérifier get_all_roles / get_all_permissions
        roles = user.get_all_roles()
        assert len(roles) == 2

        permissions = user.get_all_permissions()
        assert 'multi.read' in permissions
        assert 'multi.write' in permissions
        assert 'multi.delete' in permissions

    def test_remove_role_from_user(self):
        """Test retrait de rôle."""
        from tenxyte.models import Permission, Role

        role = Role.objects.create(code='temp_role', name='Temp')
        perm = Permission.objects.create(code='temp.perm', name='Temp Perm')
        role.permissions.add(perm)

        user = User.objects.create_user(email='remove_role@test.com', password='P@ss123!')
        user.roles.add(role)
        assert user.roles.count() == 1

        if not _is_mongodb:
            # M2M remove unsupported on MongoDB (through tables lack integer PKs)
            user.roles.remove(role)
            assert user.roles.count() == 0
