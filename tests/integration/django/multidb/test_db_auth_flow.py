"""
Tests multi-DB: flux d'authentification complet.

Vérifie que le flow auth end-to-end (register → login → JWT → refresh → logout)
fonctionne correctement quel que soit le backend DB.
"""
import pytest
from django.conf import settings

_is_mongodb = 'mongodb' in settings.DATABASES.get('default', {}).get('ENGINE', '')

from tenxyte.models import User, Application, RefreshToken  # noqa: E402
from tests.integration.django.test_helpers import get_jwt_service  # noqa: E402
from tests.integration.django.auth_service_compat import AuthService  # noqa: E402
from tenxyte.services.otp_service import OTPService  # noqa: E402
from tests.integration.django.totp_compat import TOTPService  # noqa: E402

JWTService = get_jwt_service  # noqa: E402


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
        self.jwt_service = JWTService()
        self.app_secret = self.raw_secret
        self.auth_service = AuthService()

    def test_authenticate_by_email(self):
        """Test d'authentification par email."""
        success, data, error = self.auth_service.authenticate_by_email(
            email=self.user.email,
            password='AuthP@ss123!',
            application=self.app
        )
        
        assert success is True
        assert data is not None
        assert 'access_token' in data
        assert 'refresh_token' in data

    def test_authenticate_wrong_password(self):
        """Test d'authentification avec mauvais mot de passe."""
        success, data, error = self.auth_service.authenticate_by_email(
            email=self.user.email,
            password='WrongPassword',
            application=self.app
        )
        
        assert success is False
        assert data is None
        assert error is not None

    def test_authenticate_nonexistent_user(self):
        """Test auth avec utilisateur inexistant."""
        success, data, error = self.auth_service.authenticate_by_email(
            email='ghost@test.com',
            password='AuthP@ss123!',
            application=self.app
        )
        assert success is False

    def test_jwt_generate_decode_cycle(self):
        """Test cycle complet: generate → decode → validate."""
        import secrets
        token_pair = self.jwt_service._service.generate_token_pair(
            user_id=str(self.user.pk),
            application_id=str(self.app.pk),
            refresh_token_str=secrets.token_urlsafe(32)
        )

        decoded = self.jwt_service._service.decode_token(token_pair.access_token)
        assert decoded is not None
        assert decoded.user_id == str(self.user.pk)
        assert decoded.app_id == str(self.app.pk)
        assert decoded.is_valid is True

    def test_jwt_blacklist(self):
        """Test blacklisting d'un token."""
        import secrets
        token_pair = self.jwt_service._service.generate_token_pair(
            user_id=str(self.user.pk),
            application_id=str(self.app.pk),
            refresh_token_str=secrets.token_urlsafe(32)
        )
        decoded = self.jwt_service._service.decode_token(token_pair.access_token)
        assert decoded.is_valid is True

        # Blacklist le token en utilisant la méthode du service
        self.jwt_service._service.blacklist_service.blacklist_token(
            jti=decoded.jti,
            expires_at=decoded.exp,
            user_id=str(self.user.pk),
            reason='test_multidb'
        )

        decoded_after = self.jwt_service._service.decode_token(token_pair.access_token)
        assert decoded_after.is_blacklisted is True

    def test_refresh_token_lifecycle(self):
        """Test cycle refresh token: create → validate → revoke."""
        success, data, error = self.auth_service.authenticate_by_email(
            email=self.user.email,
            password='AuthP@ss123!',
            application=self.app
        )
        assert success is True

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
            email=self.user.email,
            password='AuthP@ss123!',
            application=self.app
        )
        success_b, data_b, _ = self.auth_service.authenticate_by_email(
            email=self.user.email,
            password='AuthP@ss123!',
            application=app_b
        )
        assert success_a and success_b

        # Les tokens doivent être différents
        assert data_a['access_token'] != data_b['access_token']
        assert data_a['refresh_token'] != data_b['refresh_token']

        # Les payloads doivent référencer la bonne application
        decoded_a = self.jwt_service._service.decode_token(data_a['access_token'])
        decoded_b = self.jwt_service._service.decode_token(data_b['access_token'])
        assert decoded_a.app_id == str(self.app.pk)
        assert decoded_b.app_id == str(app_b.pk)


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

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.raw_secret = Application.create_application(name='TestApp')
        self.user = User.objects.create_user(email='test@example.com', password='AuthP@ss123!')
        self.jwt_service = get_jwt_service()
        self.app_secret = self.raw_secret
        self.auth_service = AuthService()
        self.totp_service = TOTPService()

    def test_setup_and_verify_2fa(self):
        """Test setup 2FA complet."""
        import pyotp

        # Générer secret
        secret = self.totp_service.generate_secret()
        self.user.totp_secret = secret
        self.user.save()

        # Vérifier un code valide
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        assert self.totp_service.verify_code(self.user, valid_code) is True

        # Activer 2FA
        self.user.is_2fa_enabled = True
        self.user.save()
        self.user.refresh_from_db()
        assert self.user.is_2fa_enabled is True
        assert self.user.totp_secret == secret

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
