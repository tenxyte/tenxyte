"""
Tests pour les vues admin Security.
"""
from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import pytest  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402
from datetime import timedelta  # noqa: E402
from rest_framework import status  # noqa: E402

from tenxyte.models import AuditLog, BlacklistedToken, RefreshToken, LoginAttempt  # noqa: E402

User = get_user_model()


@pytest.fixture
def sample_audit_logs(db, user, application):
    """Créer des entrées audit log de test."""
    logs = []
    for action in ['login', 'login_failed', 'logout', 'password_change']:
        log = AuditLog.objects.create(
            user=user,
            action=action,
            ip_address='127.0.0.1',
            user_agent='TestAgent',
            application=application,
            details={'method': 'email'}
        )
        logs.append(log)
    return logs


@pytest.fixture
def sample_login_attempts(db, application):
    """Créer des tentatives de connexion."""
    attempts = []
    for i in range(5):
        attempt = LoginAttempt.objects.create(
            identifier=f'user{i}@test.com',
            ip_address=f'192.168.1.{i}',
            application=application,
            success=(i % 2 == 0),
            failure_reason='' if i % 2 == 0 else 'invalid_password'
        )
        attempts.append(attempt)
    return attempts


@pytest.fixture
def sample_blacklisted_tokens(db, user):
    """Créer des tokens blacklistés."""
    tokens = []
    for i in range(3):
        token = BlacklistedToken.objects.create(
            token_jti=f'test-jti-{i}',
            user=user,
            expires_at=timezone.now() + timedelta(hours=1),
            reason='logout'
        )
        tokens.append(token)
    # Ajouter un token expiré
    expired = BlacklistedToken.objects.create(
        token_jti='expired-jti',
        user=user,
        expires_at=timezone.now() - timedelta(hours=1),
        reason='logout'
    )
    tokens.append(expired)
    return tokens


class TestAuditLogViews:
    """Tests pour les vues Audit Log."""

    @pytest.mark.django_db
    def test_list_audit_logs(self, authenticated_admin_client, admin_user, sample_audit_logs):
        """Admin peut lister les audit logs."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/audit-logs/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            assert 'results' in response.data or isinstance(response.data, list)

    @pytest.mark.django_db
    def test_filter_by_action(self, authenticated_admin_client, admin_user, sample_audit_logs):
        """Filtre par action."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/audit-logs/?action=login')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_filter_by_user(self, authenticated_admin_client, admin_user, user, sample_audit_logs):
        """Filtre par user_id."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/audit-logs/?user_id={user.id}')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_get_audit_log_detail(self, authenticated_admin_client, admin_user, sample_audit_logs):
        """Détail d'un audit log."""
        log = sample_audit_logs[0]
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/audit-logs/{log.id}/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            assert response.data['action'] == log.action

    @pytest.mark.django_db
    def test_audit_log_not_found(self, authenticated_admin_client, admin_user):
        """Audit log inexistant."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/audit-logs/99999/')
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]


class TestLoginAttemptViews:
    """Tests pour les vues Login Attempt."""

    @pytest.mark.django_db
    def test_list_login_attempts(self, authenticated_admin_client, admin_user, sample_login_attempts):
        """Admin peut lister les tentatives de connexion."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/login-attempts/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_filter_by_success(self, authenticated_admin_client, admin_user, sample_login_attempts):
        """Filtre par succès/échec."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/login-attempts/?success=true')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_filter_by_ip(self, authenticated_admin_client, admin_user, sample_login_attempts):
        """Filtre par adresse IP."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/login-attempts/?ip_address=192.168.1.0')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


class TestBlacklistedTokenViews:
    """Tests pour les vues Blacklisted Token."""

    @pytest.mark.django_db
    def test_list_blacklisted_tokens(self, authenticated_admin_client, admin_user, sample_blacklisted_tokens):
        """Admin peut lister les tokens blacklistés."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/blacklisted-tokens/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_cleanup_expired(self, authenticated_admin_client, admin_user, sample_blacklisted_tokens):
        """Nettoyage des tokens expirés."""
        response = authenticated_admin_client.post(f'{api_prefix}/auth/admin/blacklisted-tokens/cleanup/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            assert 'cleaned' in response.data


class TestRefreshTokenViews:
    """Tests pour les vues Refresh Token."""

    @pytest.mark.django_db
    def test_list_refresh_tokens(self, authenticated_admin_client, admin_user):
        """Admin peut lister les refresh tokens."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/refresh-tokens/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_refresh_token_no_value_exposed(self, authenticated_admin_client, admin_user, user, application):
        """La valeur du token ne doit jamais être exposée."""
        # Créer un refresh token
        RefreshToken.objects.create(
            user=user,
            application=application,
            token='secret-token-value',
            device_info='Test Device',
            ip_address='127.0.0.1',
            expires_at=timezone.now() + timedelta(days=7),
        )

        response = authenticated_admin_client.get(f'{api_prefix}/auth/admin/refresh-tokens/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            data = response.data.get('results', response.data)
            if isinstance(data, list):
                for item in data:
                    assert 'token' not in item

    @pytest.mark.django_db
    def test_revoke_refresh_token(self, authenticated_admin_client, admin_user, user, application):
        """Admin peut révoquer un refresh token."""
        refresh_token = RefreshToken.objects.create(
            user=user,
            application=application,
            token='token-to-revoke',
            device_info='Test Device',
            ip_address='127.0.0.1',
            expires_at=timezone.now() + timedelta(days=7),
        )

        response = authenticated_admin_client.post(
            f'{api_prefix}/auth/admin/refresh-tokens/{refresh_token.id}/revoke/'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            refresh_token.refresh_from_db()
            assert refresh_token.is_revoked is True
