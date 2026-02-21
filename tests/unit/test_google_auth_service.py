"""
Tests Phase 5 - GoogleAuthService
Couverture des appels externes mockés et logique d'authentification.
"""
import pytest
from unittest.mock import patch, MagicMock

from tenxyte.models import Application, User


# ─── Helpers ─────────────────────────────────────────────────────────────────

@pytest.fixture
def google_auth_service():
    # L'import de AuthService doit se faire dans le test
    from tenxyte.services.google_auth_service import GoogleAuthService
    return GoogleAuthService()

@pytest.fixture
def test_app():
    app, _ = Application.create_application(name="TestGoogleAuthApp")
    return app


# ─── Tests : verify_id_token ──────────────────────────────────────────────────

class TestVerifyIdToken:

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_verify_id_token_success(self, mock_verify, google_auth_service):
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'sub': '12345',
            'email': 'test@example.com',
            'email_verified': True,
            'given_name': 'John',
            'family_name': 'Doe',
            'picture': 'http://example.com/pic.jpg'
        }

        result = google_auth_service.verify_id_token("valid_token")

        assert result is not None
        assert result['google_id'] == '12345'
        assert result['email'] == 'test@example.com'
        assert result['first_name'] == 'John'
        assert result['last_name'] == 'Doe'

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_verify_id_token_invalid_issuer(self, mock_verify, google_auth_service):
        mock_verify.return_value = {
            'iss': 'evil.google.com',
            'sub': '12345'
        }
        result = google_auth_service.verify_id_token("token")
        assert result is None

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_verify_id_token_exception_returns_none(self, mock_verify, google_auth_service):
        mock_verify.side_effect = Exception("Invalid token")
        result = google_auth_service.verify_id_token("token")
        assert result is None


# ─── Tests : exchange_code_for_tokens ─────────────────────────────────────────

class TestExchangeCodeForTokens:

    @patch('requests.post')
    def test_exchange_code_success(self, mock_post, google_auth_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "abc", "expires_in": 3600}
        mock_post.return_value = mock_response

        result = google_auth_service.exchange_code_for_tokens("code", "http://redir")

        assert result == {"access_token": "abc", "expires_in": 3600}

    @patch('requests.post')
    def test_exchange_code_fails(self, mock_post, google_auth_service):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        result = google_auth_service.exchange_code_for_tokens("code", "http://redir")

        assert result is None

    @patch('requests.post')
    def test_exchange_code_exception(self, mock_post, google_auth_service):
        mock_post.side_effect = Exception("Network error")
        result = google_auth_service.exchange_code_for_tokens("code", "http://redir")
        assert result is None


# ─── Tests : get_user_info ────────────────────────────────────────────────────

class TestGetUserInfo:

    @patch('requests.get')
    def test_get_user_info_success(self, mock_get, google_auth_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sub': '111',
            'email': 'info@test.com',
            'email_verified': True,
            'given_name': 'Jane',
            'family_name': 'Smith',
            'picture': 'url'
        }
        mock_get.return_value = mock_response

        result = google_auth_service.get_user_info("access_token")

        assert result is not None
        assert result['google_id'] == '111'
        assert result['email'] == 'info@test.com'

    @patch('requests.get')
    def test_get_user_info_fails(self, mock_get, google_auth_service):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = google_auth_service.get_user_info("access_token")

        assert result is None


# ─── Tests : authenticate_with_google ─────────────────────────────────────────

class TestAuthenticateWithGoogle:

    @pytest.mark.django_db
    def test_authenticate_invalid_google_data(self, google_auth_service, test_app):
        # google_id manquant
        google_data = {"email": "test@test.com"}
        success, data, msg = google_auth_service.authenticate_with_google(google_data, test_app, "1.2.3.4")

        assert success is False
        assert "Invalid Google data" in msg

    @pytest.mark.django_db
    def test_authenticate_existing_google_id(self, google_auth_service, test_app):
        user = User.objects.create(email="exist@test.com", google_id="G123", is_active=True)
        user.save()

        google_data = {"google_id": "G123", "email": "exist@test.com"}
        success, data, msg = google_auth_service.authenticate_with_google(
            google_data, test_app, "1.2.3.4", "v=1|os=windows|device=desktop"
        )

        assert success is True
        assert data['user']['email'] == "exist@test.com"
        assert 'access_token' in data

    @pytest.mark.django_db
    def test_authenticate_link_by_email(self, google_auth_service, test_app):
        # Utilisateur existe mais n'a pas de google_id
        user = User.objects.create(email="link@test.com", is_active=True)
        user.save()

        google_data = {"google_id": "G456", "email": "link@test.com", "email_verified": True}
        success, data, msg = google_auth_service.authenticate_with_google(google_data, test_app, "1.2.3.4")

        assert success is True
        user.refresh_from_db()
        assert user.google_id == "G456"
        assert user.is_email_verified is True

    @pytest.mark.django_db
    def test_authenticate_creates_new_user(self, google_auth_service, test_app):
        # Email n'existe pas en DB
        google_data = {
            "google_id": "G789",
            "email": "new@test.com",
            "first_name": "New",
            "last_name": "User",
            "email_verified": True
        }
        success, data, msg = google_auth_service.authenticate_with_google(google_data, test_app, "1.2.3.4")

        assert success is True
        new_user = User.objects.get(email="new@test.com")
        assert new_user.google_id == "G789"
        assert new_user.first_name == "New"
        assert new_user.is_active is True

    @pytest.mark.django_db
    def test_authenticate_inactive_account(self, google_auth_service, test_app):
        user = User.objects.create(email="inactive@test.com", google_id="G999", is_active=False)
        user.save()

        google_data = {"google_id": "G999", "email": "inactive@test.com"}
        success, data, msg = google_auth_service.authenticate_with_google(google_data, test_app, "1.2.3.4")

        assert success is False
        assert msg == "Account is inactive"

    @pytest.mark.django_db
    def test_authenticate_locked_account(self, google_auth_service, test_app):
        from django.utils import timezone
        from datetime import timedelta

        user = User.objects.create(
            email="locked@test.com",
            google_id="GLOCK",
            is_active=True,
            is_locked=True,
            locked_until=timezone.now() + timedelta(hours=1)
        )
        user.save()

        google_data = {"google_id": "GLOCK", "email": "locked@test.com"}
        success, data, msg = google_auth_service.authenticate_with_google(google_data, test_app, "1.2.3.4")

        assert success is False
        assert msg == "Account is locked"
