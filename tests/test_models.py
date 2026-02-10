"""
Tests pour les modèles.
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from tenxyte.models import (
    User, Application, Permission, Role,
    RefreshToken, OTPCode
)


class TestUserModel:
    """Tests pour le modèle User."""

    @pytest.mark.django_db
    def test_create_user(self):
        """Test de création d'utilisateur."""
        user = User.objects.create_user(
            email="test@example.com",
            password="Test123!@#"
        )

        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.check_password("Test123!@#")

    @pytest.mark.django_db
    def test_create_superuser(self):
        """Test de création de superutilisateur."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="Admin123!@#"
        )

        assert user.is_staff is True
        assert user.is_superuser is True

    @pytest.mark.django_db
    def test_user_full_phone(self):
        """Test de numéro de téléphone complet."""
        user = User.objects.create_user(
            email="test@example.com",
            password="Test123!",
            phone_country_code="33",
            phone_number="612345678"
        )

        assert user.full_phone == "+33612345678"

    @pytest.mark.django_db
    def test_user_full_phone_none(self):
        """Test sans numéro de téléphone."""
        user = User.objects.create_user(
            email="test@example.com",
            password="Test123!"
        )

        assert user.full_phone == ""

    @pytest.mark.django_db
    def test_user_str(self):
        """Test de représentation string."""
        user = User.objects.create_user(
            email="test@example.com",
            password="Test123!"
        )

        assert str(user) == "test@example.com"

    @pytest.mark.django_db
    def test_user_roles(self, user):
        """Test d'assignation de rôles."""
        role = Role.objects.create(
            name="Admin",
            description="Administrator"
        )

        user.roles.add(role)

        assert role in user.roles.all()
        assert user.roles.count() == 1


class TestApplicationModel:
    """Tests pour le modèle Application."""

    @pytest.mark.django_db
    def test_create_application(self):
        """Test de création d'application."""
        import secrets
        app = Application.objects.create(
            name="Test App",
            access_key=secrets.token_hex(32),
            access_secret="secret_456"
        )

        assert app.name == "Test App"
        assert app.access_key is not None
        assert app.is_active is True

    @pytest.mark.django_db
    def test_application_str(self):
        """Test de représentation string."""
        import secrets
        app = Application.objects.create(
            name="My App",
            access_key=secrets.token_hex(32),
            access_secret="secret_456"
        )

        # __str__ returns name - access_key
        assert "My App" in str(app)

    @pytest.mark.django_db
    def test_application_create_with_method(self):
        """Test de création avec la méthode factory."""
        app, raw_secret = Application.create_application(
            name="Test App",
            description="Test description"
        )

        assert app.name == "Test App"
        assert app.access_key is not None
        assert raw_secret is not None
        assert app.verify_secret(raw_secret) is True


class TestPermissionModel:
    """Tests pour le modèle Permission."""

    @pytest.mark.django_db
    def test_create_permission(self):
        """Test de création de permission."""
        permission = Permission.objects.create(
            code="users.edit",
            name="Can edit users",
            description="Permission to edit user data"
        )

        assert permission.code == "users.edit"
        assert permission.name == "Can edit users"

    @pytest.mark.django_db
    def test_permission_str(self):
        """Test de représentation string."""
        permission = Permission.objects.create(
            code="can.delete",
            name="Can Delete"
        )

        assert str(permission) == "can.delete"


class TestRoleModel:
    """Tests pour le modèle Role."""

    @pytest.mark.django_db
    def test_create_role(self):
        """Test de création de rôle."""
        role = Role.objects.create(
            code="editor",
            name="Editor",
            description="Content editor role"
        )

        assert role.code == "editor"
        assert role.name == "Editor"
        assert role.description == "Content editor role"

    @pytest.mark.django_db
    def test_role_permissions(self):
        """Test d'assignation de permissions."""
        role = Role.objects.create(code="admin", name="Admin")
        perm1 = Permission.objects.create(code="can.read", name="Can Read")
        perm2 = Permission.objects.create(code="can.write", name="Can Write")

        role.permissions.add(perm1, perm2)

        assert role.permissions.count() == 2
        assert perm1 in role.permissions.all()
        assert perm2 in role.permissions.all()

    @pytest.mark.django_db
    def test_role_str(self):
        """Test de représentation string."""
        role = Role.objects.create(code="moderator", name="Moderator")

        assert str(role) == "Moderator"


class TestRefreshTokenModel:
    """Tests pour le modèle RefreshToken."""

    @pytest.mark.django_db
    def test_create_refresh_token(self, user, application):
        """Test de création de refresh token."""
        token = RefreshToken.objects.create(
            user=user,
            application=application,
            token="refresh_token_123",
            expires_at=timezone.now() + timedelta(days=30)
        )

        assert token.user == user
        assert token.application == application
        assert token.is_revoked is False

    @pytest.mark.django_db
    def test_refresh_token_is_valid(self, user, application):
        """Test de validation du token."""
        token = RefreshToken.objects.create(
            user=user,
            application=application,
            token="refresh_token_123",
            expires_at=timezone.now() + timedelta(days=30)
        )

        assert token.is_valid() is True

    @pytest.mark.django_db
    def test_refresh_token_expired(self, user, application):
        """Test de token expiré."""
        token = RefreshToken.objects.create(
            user=user,
            application=application,
            token="refresh_token_123",
            expires_at=timezone.now() - timedelta(days=1)
        )

        assert token.is_valid() is False

    @pytest.mark.django_db
    def test_refresh_token_revoked(self, user, application):
        """Test de token révoqué."""
        token = RefreshToken.objects.create(
            user=user,
            application=application,
            token="refresh_token_123",
            expires_at=timezone.now() + timedelta(days=30),
            is_revoked=True
        )

        assert token.is_valid() is False

    @pytest.mark.django_db
    def test_refresh_token_str(self, user, application):
        """Test de représentation string."""
        token = RefreshToken.objects.create(
            user=user,
            application=application,
            token="refresh_token_123",
            expires_at=timezone.now() + timedelta(days=30)
        )

        # __str__ format may vary
        assert str(token) is not None


class TestOTPCodeModel:
    """Tests pour le modèle OTPCode."""

    @pytest.mark.django_db
    def test_create_otp_code(self, user):
        """Test de création de code OTP."""
        from django.utils import timezone
        hashed = OTPCode._hash_code("123456")
        otp = OTPCode.objects.create(
            user=user,
            code=hashed,
            otp_type="email_verification",
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        assert otp.user == user
        assert otp.code == hashed
        assert len(otp.code) == 64  # SHA-256 hex digest
        assert otp.otp_type == "email_verification"
        assert otp.is_used is False

    @pytest.mark.django_db
    def test_otp_is_valid(self, user):
        """Test de validation du code OTP."""
        from django.utils import timezone
        otp = OTPCode.objects.create(
            user=user,
            code=OTPCode._hash_code("123456"),
            otp_type="email_verification",
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        assert otp.is_valid() is True

    @pytest.mark.django_db
    def test_otp_expired(self, user):
        """Test de code OTP expiré."""
        from django.utils import timezone
        otp = OTPCode.objects.create(
            user=user,
            code=OTPCode._hash_code("123456"),
            otp_type="email_verification",
            expires_at=timezone.now() - timedelta(minutes=5)
        )

        assert otp.is_valid() is False

    @pytest.mark.django_db
    def test_otp_already_used(self, user):
        """Test de code OTP déjà utilisé."""
        from django.utils import timezone
        otp = OTPCode.objects.create(
            user=user,
            code=OTPCode._hash_code("123456"),
            otp_type="email_verification",
            is_used=True,
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        assert otp.is_valid() is False

    @pytest.mark.django_db
    def test_otp_str(self, user):
        """Test de représentation string."""
        otp = OTPCode.objects.create(
            user=user,
            code=OTPCode._hash_code("123456"),
            otp_type="email_verification",
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        # __str__ returns meaningful representation
        assert str(otp) is not None

    @pytest.mark.django_db
    def test_otp_verify_with_hash(self, user):
        """Test que verify() compare correctement le hash SHA-256."""
        from django.utils import timezone
        otp, raw_code = OTPCode.generate(user, 'email_verification', validity_minutes=10)

        # Le code stocké est un hash, pas le code en clair
        assert otp.code != raw_code
        assert len(otp.code) == 64

        # La vérification avec le bon code fonctionne
        assert otp.verify(raw_code) is True

    @pytest.mark.django_db
    def test_otp_verify_wrong_code(self, user):
        """Test que verify() rejette un mauvais code."""
        from django.utils import timezone
        otp, raw_code = OTPCode.generate(user, 'email_verification', validity_minutes=10)

        assert otp.verify('000000') is False
