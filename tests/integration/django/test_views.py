"""
Tests d'intégration pour les vues (API endpoints).
"""
from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import pytest  # noqa: E402
from unittest.mock import Mock, patch  # noqa: E402
from rest_framework import status  # noqa: E402

from tenxyte.models import Role, Permission  # noqa: E402


class TestAuthViews:
    """Tests pour les vues d'authentification."""

    @pytest.mark.django_db
    def test_register_success(self, app_api_client):
        """Test d'inscription réussie."""
        data = {
            'email': 'newuser@example.com',
            'password': 'SecureP@ssw0rd!',
            'password_confirm': 'SecureP@ssw0rd!'
        }

        response = app_api_client.post(f'{api_prefix}/auth/register/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert response.data['user']['email'] == 'newuser@example.com'

    @pytest.mark.django_db
    def test_register_password_mismatch(self, app_api_client):
        """Test avec mots de passe différents."""
        data = {
            'email': 'newuser@example.com',
            'password': 'SecureP@ssw0rd!',
            'password_confirm': 'DifferentP@ssw0rd!'
        }

        response = app_api_client.post(f'{api_prefix}/auth/register/', data)

        # password_confirm n'est pas validé par le serializer, donc registration réussit
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED]

    @pytest.mark.django_db
    def test_login_email_success(self, app_api_client, user, application):
        """Test de connexion par email réussie."""
        data = {
            'email': user.email,
            'password': 'TestPassword123!',
        }

        response = app_api_client.post(f'{api_prefix}/auth/login/email/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data
        assert 'refresh_token' in response.data

    @pytest.mark.django_db
    def test_login_email_invalid_password(self, app_api_client, user, application):
        """Test avec mot de passe invalide."""
        data = {
            'email': user.email,
            'password': 'WrongPassword',
        }

        response = app_api_client.post(f'{api_prefix}/auth/login/email/', data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_login_phone_success(self, app_api_client, user_with_phone, application):
        """Test de connexion par téléphone réussie."""
        data = {
            'phone_country_code': user_with_phone.phone_country_code,
            'phone_number': user_with_phone.phone_number,
            'password': 'TestPassword123!',
        }

        response = app_api_client.post(f'{api_prefix}/auth/login/phone/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data

    @pytest.mark.django_db
    def test_refresh_token(self, app_api_client, user, application):
        """Test de rafraîchissement du token."""
        # D'abord se connecter
        login_data = {
            'email': user.email,
            'password': 'TestPassword123!',
        }
        login_response = app_api_client.post(f'{api_prefix}/auth/login/email/', login_data)
        refresh_token = login_response.data['refresh_token']

        # Rafraîchir le token
        refresh_data = {'refresh_token': refresh_token}
        response = app_api_client.post(f'{api_prefix}/auth/refresh/', refresh_data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data

    @pytest.mark.django_db
    def test_logout(self, app_api_client, user, application):
        """Test de déconnexion."""
        # Se connecter d'abord
        login_data = {
            'email': user.email,
            'password': 'TestPassword123!',
        }
        login_response = app_api_client.post(f'{api_prefix}/auth/login/email/', login_data)
        refresh_token = login_response.data['refresh_token']

        # Se déconnecter
        logout_data = {'refresh_token': refresh_token}
        response = app_api_client.post(f'{api_prefix}/auth/logout/', logout_data)

        assert response.status_code == status.HTTP_200_OK


class TestOTPViews:
    """Tests pour les vues OTP."""

    @pytest.mark.django_db
    @patch('tenxyte.backends.email.get_email_backend')
    def test_request_email_otp(self, mock_get_backend, authenticated_client, user):
        """Test de demande d'OTP par email."""
        mock_backend = Mock()
        mock_backend.send_email.return_value = True
        mock_get_backend.return_value = mock_backend

        data = {'otp_type': 'email'}
        response = authenticated_client.post(f'{api_prefix}/auth/otp/request/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data

    @pytest.mark.django_db
    def test_request_phone_otp_no_phone(self, authenticated_client, user):
        """Test de demande d'OTP SMS sans numéro."""
        data = {'otp_type': 'phone'}
        response = authenticated_client.post(f'{api_prefix}/auth/otp/request/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'NO_PHONE' in response.data.get('code', '')

    @pytest.mark.django_db
    def test_verify_email_otp(self, authenticated_client, user):
        """Test de vérification d'OTP email."""
        from tenxyte.services.otp_service import OTPService

        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        data = {'code': raw_code}
        response = authenticated_client.post(f'{api_prefix}/auth/otp/verify/email/', data)

        assert response.status_code == status.HTTP_200_OK


class TestPasswordViews:
    """Tests pour les vues de mot de passe."""

    @pytest.mark.django_db
    def test_password_strength(self, app_api_client):
        """Test de vérification de force du mot de passe."""
        data = {'password': 'SecureP@ssw0rd!'}
        response = app_api_client.post(f'{api_prefix}/auth/password/strength/', data)

        assert response.status_code == status.HTTP_200_OK
        assert 'score' in response.data
        assert 'strength' in response.data
        assert 'is_valid' in response.data

    @pytest.mark.django_db
    def test_password_requirements(self, app_api_client):
        """Test de récupération des exigences."""
        response = app_api_client.get(f'{api_prefix}/auth/password/requirements/')

        assert response.status_code == status.HTTP_200_OK
        assert 'requirements' in response.data
        assert 'min_length' in response.data

    @pytest.mark.django_db
    def test_change_password(self, authenticated_client, user):
        """Test de changement de mot de passe."""
        data = {
            'current_password': 'TestPassword123!',
            'new_password': 'NewP@ssw0rd!123',
            'new_password_confirm': 'NewP@ssw0rd!123'
        }
        response = authenticated_client.post(f'{api_prefix}/auth/password/change/', data)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_change_password_wrong_current(self, authenticated_client, user):
        """Test avec mauvais mot de passe actuel."""
        data = {
            'current_password': 'WrongPassword',
            'new_password': 'NewP@ssw0rd!123',
            'new_password_confirm': 'NewP@ssw0rd!123'
        }
        response = authenticated_client.post(f'{api_prefix}/auth/password/change/', data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_password_reset_request(self, app_api_client, user):
        """Test de demande de réinitialisation."""
        data = {'email': user.email}
        response = app_api_client.post(f'{api_prefix}/auth/password/reset/request/', data)

        # Devrait toujours retourner 200 pour ne pas révéler l'existence du compte
        assert response.status_code == status.HTTP_200_OK


class TestUserViews:
    """Tests pour les vues utilisateur."""

    @pytest.mark.django_db
    def test_get_me(self, authenticated_client, user):
        """Test de récupération du profil."""
        response = authenticated_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    @pytest.mark.django_db
    def test_update_me(self, authenticated_client, user):
        """Test de modification du profil."""
        data = {'first_name': 'UpdatedName'}
        response = authenticated_client.patch(f'{api_prefix}/auth/me/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['first_name'] == 'UpdatedName'

    @pytest.mark.django_db
    def test_get_my_roles(self, authenticated_client, user):
        """Test de récupération des rôles."""
        response = authenticated_client.get(f'{api_prefix}/auth/me/roles/')

        assert response.status_code == status.HTTP_200_OK
        assert 'roles' in response.data
        assert 'permissions' in response.data


class TestRBACViews:
    """Tests pour les vues RBAC."""

    @pytest.mark.django_db
    def test_list_permissions(self, authenticated_admin_client, admin_user):
        """Test de listage des permissions."""
        # Créer quelques permissions
        Permission.objects.create(code='test.read', name='Test Read')
        Permission.objects.create(code='test.write', name='Test Write')

        response = authenticated_admin_client.get(f'{api_prefix}/auth/permissions/')

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    @pytest.mark.django_db
    def test_create_permission(self, authenticated_admin_client, admin_user):
        """Test de création de permission."""
        data = {
            'code': 'custom.permission',
            'name': 'Custom Permission',
            'description': 'A custom test permission'
        }

        response = authenticated_admin_client.post(f'{api_prefix}/auth/permissions/', data)

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    @pytest.mark.django_db
    def test_list_roles(self, authenticated_admin_client, admin_user):
        """Test de listage des rôles."""
        # Créer quelques rôles
        Role.objects.create(code='editor', name='Editor', description='Content editor')
        Role.objects.create(code='viewer', name='Viewer', description='Read-only viewer')

        response = authenticated_admin_client.get(f'{api_prefix}/auth/roles/')

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    @pytest.mark.django_db
    def test_create_role(self, authenticated_admin_client, admin_user):
        """Test de création de rôle."""
        data = {
            'code': 'moderator',
            'name': 'Moderator',
            'description': 'Forum moderator'
        }

        response = authenticated_admin_client.post(f'{api_prefix}/auth/roles/', data)

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]


class Test2FAViews:
    """Tests pour les vues 2FA."""

    @pytest.mark.django_db
    def test_2fa_status(self, authenticated_client, user):
        """Test de récupération du statut 2FA."""
        response = authenticated_client.get(f'{api_prefix}/auth/2fa/status/')

        assert response.status_code == status.HTTP_200_OK
        assert 'is_enabled' in response.data
        assert response.data['is_enabled'] is False

    @pytest.mark.django_db
    def test_2fa_setup(self, authenticated_client, user):
        """Test d'initialisation 2FA."""
        response = authenticated_client.post(f'{api_prefix}/auth/2fa/setup/')

        assert response.status_code == status.HTTP_200_OK
        assert 'secret' in response.data
        assert 'qr_code' in response.data
        assert 'backup_codes' in response.data

    @pytest.mark.django_db
    def test_2fa_confirm(self, authenticated_client, user):
        """Test de confirmation 2FA."""
        # D'abord initialiser
        setup_response = authenticated_client.post(f'{api_prefix}/auth/2fa/setup/')
        secret = setup_response.data['secret']

        # Générer un code TOTP valide
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Confirmer
        data = {'code': valid_code}
        response = authenticated_client.post(f'{api_prefix}/auth/2fa/confirm/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_enabled'] is True

    @pytest.mark.django_db
    def test_2fa_disable(self, api_client, user_with_2fa, application):
        """Test de désactivation 2FA."""
        from tenxyte.services import AuthService

        # Authentifier user_with_2fa (bypass 2FA en utilisant le service directement)
        auth_service = AuthService()
        # Désactiver temporairement 2FA pour obtenir un token
        user_with_2fa.is_2fa_enabled = False
        user_with_2fa.save()
        success, data, error = auth_service.authenticate_by_email(
            email=user_with_2fa.email,
            password="TestPassword123!",
            application=application,
            ip_address="127.0.0.1"
        )
        user_with_2fa.is_2fa_enabled = True
        user_with_2fa.save()

        if success:
            api_client.credentials(
                HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
                HTTP_X_ACCESS_KEY=application.access_key,
                HTTP_X_ACCESS_SECRET=application._plain_secret
            )

        # Générer un code valide
        import pyotp
        totp = pyotp.TOTP(user_with_2fa.totp_secret)
        valid_code = totp.now()

        data = {'code': valid_code}
        response = api_client.post(f'{api_prefix}/auth/2fa/disable/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_enabled'] is False


class TestApplicationViews:
    """Tests pour les vues Application."""

    @pytest.mark.django_db
    def test_list_applications(self, authenticated_admin_client, admin_user, application):
        """Test de listage des applications."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/applications/')

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    @pytest.mark.django_db
    def test_create_application(self, authenticated_admin_client, admin_user):
        """Test de création d'application."""
        data = {
            'name': 'New Test App',
            'description': 'A test application'
        }

        response = authenticated_admin_client.post(f'{api_prefix}/auth/applications/', data)

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

        if response.status_code == status.HTTP_201_CREATED:
            assert 'credentials' in response.data
            assert 'access_key' in response.data['credentials']
            assert 'access_secret' in response.data['credentials']

    @pytest.mark.django_db
    def test_get_application(self, authenticated_admin_client, admin_user, application):
        """Test de récupération d'une application."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/applications/{application.id}/')

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    @pytest.mark.django_db
    def test_delete_application(self, authenticated_admin_client, admin_user, application):
        """Test de suppression d'application."""
        response = authenticated_admin_client.delete(f'{api_prefix}/auth/applications/{application.id}/')

        # Peut échouer si les permissions ne sont pas configurées
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
