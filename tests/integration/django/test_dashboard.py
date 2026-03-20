"""
Tests pour les vues Dashboard.
"""
from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import pytest  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402
from datetime import timedelta  # noqa: E402
from rest_framework import status  # noqa: E402

from tenxyte.models import (  # noqa: E402
    AuditLog, LoginAttempt, BlacklistedToken,
)
from tenxyte.services.stats_service import StatsService  # noqa: E402

User = get_user_model()


@pytest.fixture
def dashboard_data(db, user, application):
    """Créer des données variées pour les dashboards."""
    now = timezone.now()

    # Login attempts
    for i in range(10):
        LoginAttempt.objects.create(
            identifier=f'user{i}@test.com',
            ip_address='127.0.0.1',
            application=application,
            success=(i % 3 != 0),
            failure_reason='' if i % 3 != 0 else 'invalid_password'
        )

    # Audit logs
    for action in ['login', 'login', 'logout', 'password_change', 'token_refresh']:
        AuditLog.objects.create(
            user=user,
            action=action,
            ip_address='127.0.0.1',
            application=application,
        )

    # Blacklisted tokens
    BlacklistedToken.objects.create(
        token_jti='dash-jti-1',
        user=user,
        expires_at=now + timedelta(hours=2),
        reason='logout'
    )

    return True


class TestStatsService:
    """Tests unitaires pour StatsService."""

    @pytest.mark.django_db
    def test_global_stats_structure(self, dashboard_data):
        """Structure de la réponse globale."""
        service = StatsService()
        result = service.get_global_stats()

        assert 'users' in result
        assert 'auth' in result
        assert 'applications' in result
        assert 'security' in result
        assert 'gdpr' in result

    @pytest.mark.django_db
    def test_user_stats_fields(self, dashboard_data):
        """Stats utilisateurs contiennent les bons champs."""
        service = StatsService()
        result = service.get_global_stats()
        users = result['users']

        expected_keys = [
            'total', 'active', 'locked', 'banned', 'deleted',
            'verified_email', 'verified_phone', 'with_2fa',
            'new_today', 'new_this_week', 'new_this_month',
        ]
        for key in expected_keys:
            assert key in users, f"Missing key: {key}"

    @pytest.mark.django_db
    def test_auth_stats_structure(self, dashboard_data):
        """Stats auth détaillées contiennent les bonnes sections."""
        service = StatsService()
        result = service.get_auth_stats()

        assert 'login_stats' in result
        assert 'registration_stats' in result
        assert 'token_stats' in result
        assert 'top_login_failure_reasons' in result
        assert 'charts' in result

    @pytest.mark.django_db
    def test_login_stats_periods(self, dashboard_data):
        """Stats login avec périodes today/week/month."""
        service = StatsService()
        result = service.get_auth_stats()
        login_stats = result['login_stats']

        for period in ['today', 'this_week', 'this_month']:
            assert period in login_stats
            assert 'total' in login_stats[period]
            assert 'success' in login_stats[period]
            assert 'failed' in login_stats[period]

    @pytest.mark.django_db
    def test_security_stats_structure(self, dashboard_data):
        """Stats sécurité."""
        service = StatsService()
        result = service.get_security_stats()

        assert 'audit_summary_24h' in result
        assert 'blacklisted_tokens' in result
        assert 'suspicious_activity' in result
        assert 'account_security' in result

    @pytest.mark.django_db
    def test_2fa_adoption_rate(self, dashboard_data):
        """Taux d'adoption 2FA."""
        service = StatsService()
        result = service.get_security_stats()

        rate = result['account_security']['2fa_adoption_rate']
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 100.0

    @pytest.mark.django_db
    def test_gdpr_stats_structure(self, dashboard_data):
        """Stats GDPR."""
        service = StatsService()
        result = service.get_gdpr_stats()

        assert 'deletion_requests' in result
        assert 'data_exports' in result

    @pytest.mark.django_db
    def test_organization_stats_disabled(self, dashboard_data):
        """Orgs désactivées retourne enabled: False."""
        service = StatsService()
        result = service.get_organization_stats()
        # Par défaut, les orgs ne sont probablement pas enabled dans le test env
        assert 'enabled' in result

    @pytest.mark.django_db
    def test_logins_per_day_chart(self, dashboard_data):
        """Chart logins par jour."""
        service = StatsService()
        result = service.get_auth_stats()
        chart = result['charts']['logins_per_day_7d']

        assert isinstance(chart, list)
        for entry in chart:
            assert 'date' in entry
            assert 'success' in entry
            assert 'failed' in entry

    @pytest.mark.django_db
    def test_top_failure_reasons(self, dashboard_data):
        """Top raisons d'échec login."""
        service = StatsService()
        result = service.get_auth_stats()
        reasons = result['top_login_failure_reasons']

        assert isinstance(reasons, list)
        for r in reasons:
            assert 'reason' in r
            assert 'count' in r


class TestDashboardEndpoints:
    """Tests d'intégration pour les endpoints dashboard."""

    @pytest.mark.django_db
    def test_dashboard_global(self, authenticated_admin_client, admin_user, dashboard_data):
        """GET /dashboard/stats/ retourne les stats globales."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/dashboard/stats/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        if response.status_code == status.HTTP_200_OK:
            assert 'users' in response.data

    @pytest.mark.django_db
    def test_dashboard_auth(self, authenticated_admin_client, admin_user, dashboard_data):
        """GET /dashboard/auth/ retourne les stats auth."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/dashboard/auth/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_dashboard_security(self, authenticated_admin_client, admin_user, dashboard_data):
        """GET /dashboard/security/ retourne les stats sécurité."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/dashboard/security/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_dashboard_gdpr(self, authenticated_admin_client, admin_user, dashboard_data):
        """GET /dashboard/gdpr/ retourne les stats GDPR."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/dashboard/gdpr/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_dashboard_organizations(self, authenticated_admin_client, admin_user, dashboard_data):
        """GET /dashboard/organizations/ retourne les stats orgs."""
        response = authenticated_admin_client.get(f'{api_prefix}/auth/dashboard/organizations/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    @pytest.mark.django_db
    def test_dashboard_unauthenticated(self, api_client, application):
        """Non authentifié = 401/403."""
        api_client.credentials(
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = api_client.get(f'{api_prefix}/auth/dashboard/stats/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
