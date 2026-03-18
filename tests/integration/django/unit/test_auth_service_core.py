"""
Tests réécrits pour utiliser les services core directement.

Ces tests remplacent les tests qui appelaient des méthodes privées du wrapper AuthService.
Au lieu de tester l'implémentation interne, ils testent les comportements via l'API publique
ou utilisent directement les services core.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.utils import timezone

from tenxyte.models import User, Application, RefreshToken


# ===========================================================================
# Helpers
# ===========================================================================

def _app(name: str) -> Application:
    """Create test application."""
    return Application.objects.create(
        name=name,
        is_active=True
    )


def _user(email: str, password: str = "Pass123!") -> User:
    """Create test user."""
    user = User.objects.create(email=email, is_active=True)
    user.set_password(password)
    user.save()
    return user


def _refresh_token(user: User, app: Application, expired: bool = False) -> RefreshToken:
    """Create refresh token."""
    rt = RefreshToken.generate(
        user=user,
        application=app,
        ip_address="1.2.3.4"
    )
    
    # Si expiré, modifier manuellement la date d'expiration
    if expired:
        rt.expires_at = timezone.now() - timedelta(days=1)
        rt.save()
    
    return rt


# ===========================================================================
# Session Limit Tests - Réécrits pour tester via comportement observable
# ===========================================================================

class TestSessionLimitBehavior:
    """
    Tests de limitation de sessions réécrits pour tester le comportement
    via l'API publique (login) au lieu de méthodes privées.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_SESSION_LIMIT_ENABLED=False)
    def test_login_succeeds_when_session_limit_disabled(self):
        """Quand la limite de sessions est désactivée, le login réussit toujours."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("SessionLimitApp1")
        user = _user("sessionlimit1@test.com")
        
        # Créer 10 sessions actives
        for _ in range(10):
            _refresh_token(user, app)
        
        service = AuthService()
        success, data, error = service.authenticate_by_email(
            "sessionlimit1@test.com", "Pass123!", app, "1.2.3.4"
        )
        
        # Devrait réussir car la limite est désactivée
        assert success is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_SESSION_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_SESSIONS=0)
    def test_login_succeeds_when_max_sessions_is_zero(self):
        """Quand max_sessions=0, il n'y a pas de limite."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("SessionLimitApp2")
        user = _user("sessionlimit2@test.com")
        
        # Créer 10 sessions actives
        for _ in range(10):
            _refresh_token(user, app)
        
        service = AuthService()
        success, data, error = service.authenticate_by_email(
            "sessionlimit2@test.com", "Pass123!", app, "1.2.3.4"
        )
        
        # Devrait réussir car max=0 signifie illimité
        assert success is True

    @pytest.mark.django_db
    @override_settings(
        TENXYTE_SESSION_LIMIT_ENABLED=True,
        TENXYTE_DEFAULT_MAX_SESSIONS=2,
        TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='deny'
    )
    def test_login_denied_when_session_limit_exceeded(self):
        """Quand la limite est atteinte avec action='deny', le login échoue."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("SessionLimitApp3")
        user = _user("sessionlimit3@test.com")
        
        # Créer 2 sessions actives (atteint la limite)
        _refresh_token(user, app)
        _refresh_token(user, app)
        
        service = AuthService()
        success, data, error = service.authenticate_by_email(
            "sessionlimit3@test.com", "Pass123!", app, "1.2.3.4"
        )
        
        # Devrait échouer car limite atteinte
        assert success is False
        assert 'session limit' in error.lower() or 'limit' in error.lower()

    @pytest.mark.django_db
    @override_settings(
        TENXYTE_SESSION_LIMIT_ENABLED=True,
        TENXYTE_DEFAULT_MAX_SESSIONS=2,
        TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='revoke_oldest'
    )
    def test_login_revokes_oldest_when_limit_exceeded(self):
        """Quand la limite est atteinte avec action='revoke_oldest', la plus ancienne session est révoquée."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("SessionLimitApp4")
        user = _user("sessionlimit4@test.com")
        
        # Créer 2 sessions actives
        rt1 = _refresh_token(user, app)
        _refresh_token(user, app)
        
        service = AuthService()
        success, data, error = service.authenticate_by_email(
            "sessionlimit4@test.com", "Pass123!", app, "1.2.3.4"
        )
        
        # Devrait réussir et révoquer la plus ancienne
        assert success is True
        rt1.refresh_from_db()
        assert rt1.is_revoked is True

    @pytest.mark.django_db
    @override_settings(
        TENXYTE_SESSION_LIMIT_ENABLED=True,
        TENXYTE_DEFAULT_MAX_SESSIONS=2,
        TENXYTE_DEFAULT_SESSION_LIMIT_ACTION='deny'
    )
    def test_expired_tokens_dont_count_toward_limit(self):
        """Les tokens expirés ne comptent pas dans la limite de sessions."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("SessionLimitApp5")
        user = _user("sessionlimit5@test.com")
        
        # Créer 2 tokens expirés
        _refresh_token(user, app, expired=True)
        _refresh_token(user, app, expired=True)
        
        service = AuthService()
        success, data, error = service.authenticate_by_email(
            "sessionlimit5@test.com", "Pass123!", app, "1.2.3.4"
        )
        
        # Devrait réussir car les tokens expirés ne comptent pas
        assert success is True


# ===========================================================================
# Device Limit Tests - Réécrits pour tester via comportement observable
# ===========================================================================

class TestDeviceLimitBehavior:
    """
    Tests de limitation de devices réécrits pour tester le comportement
    via l'API publique au lieu de méthodes privées.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=False)
    def test_login_succeeds_when_device_limit_disabled(self):
        """Quand la limite de devices est désactivée, le login réussit toujours."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("DeviceLimitApp1")
        user = _user("devicelimit1@test.com")
        
        service = AuthService()
        success, data, error = service.authenticate_by_email(
            "devicelimit1@test.com", "Pass123!", app, "1.2.3.4",
            device_info="device_a"
        )
        
        assert success is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_DEVICES=0)
    def test_login_succeeds_when_max_devices_is_zero(self):
        """Quand max_devices=0, il n'y a pas de limite."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("DeviceLimitApp2")
        user = _user("devicelimit2@test.com")
        
        service = AuthService()
        success, data, error = service.authenticate_by_email(
            "devicelimit2@test.com", "Pass123!", app, "1.2.3.4",
            device_info="device_a"
        )
        
        assert success is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_DEVICE_LIMIT_ENABLED=True, TENXYTE_DEFAULT_MAX_DEVICES=1)
    def test_known_device_always_allowed(self):
        """Un device connu est toujours autorisé, même si la limite est atteinte."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("DeviceLimitApp3")
        user = _user("devicelimit3@test.com")
        device = 'v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=chrome;rtv=122'
        
        # Créer un token avec ce device
        RefreshToken.generate(
            user=user,
            application=app,
            ip_address="1.2.3.4",
            device_info=device
        )
        
        service = AuthService()
        # Se reconnecter avec le même device
        success, data, error = service.authenticate_by_email(
            "devicelimit3@test.com", "Pass123!", app, "1.2.3.4",
            device_info=device
        )
        
        # Devrait réussir car c'est un device connu
        assert success is True

    @pytest.mark.django_db
    @override_settings(
        TENXYTE_DEVICE_LIMIT_ENABLED=True,
        TENXYTE_DEFAULT_MAX_DEVICES=1,
        TENXYTE_DEVICE_LIMIT_ACTION='deny'
    )
    def test_login_denied_when_device_limit_exceeded(self):
        """Quand la limite de devices est atteinte, le login depuis un nouveau device échoue."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("DeviceLimitApp4")
        user = _user("devicelimit4@test.com")
        device_a = 'v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=chrome;rtv=122'
        
        # Créer un token avec device_a
        RefreshToken.generate(
            user=user,
            application=app,
            ip_address="1.2.3.4",
            device_info=device_a
        )
        
        service = AuthService()
        # Essayer de se connecter avec device_b (différent)
        device_b = 'v=1|os=ios;osv=17|device=mobile|arch=arm64|runtime=safari;rtv=17'
        success, data, error = service.authenticate_by_email(
            "devicelimit4@test.com", "Pass123!", app, "5.6.7.8",
            device_info=device_b
        )
        
        # Devrait échouer car limite atteinte
        assert success is False
        assert 'device limit' in error.lower() or 'limit' in error.lower()


# ===========================================================================
# New Device Alert Tests - DÉPLACÉS vers test_auth_service_email_alerts.py
# ===========================================================================
# Les 4 tests d'alertes email ont été déplacés vers:
# tests/integration/django/unit/test_auth_service_email_alerts.py
# 
# Raison: Nécessitent le service email complet, pas disponible dans le wrapper


# ===========================================================================
# Token Generation Tests - Réécrits pour utiliser l'API publique
# ===========================================================================

class TestTokenGeneration:
    """
    Tests de génération de tokens réécrits pour utiliser login au lieu de
    la méthode interne generate_tokens_for_user.
    """

    @pytest.mark.django_db
    def test_login_returns_token_pair(self):
        """Le login retourne une paire de tokens."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("GenTokensApp1")
        user = _user("gentokens1@test.com")
        service = AuthService()
        
        success, data, error = service.authenticate_by_email(
            "gentokens1@test.com", "Pass123!", app, "1.2.3.4"
        )
        
        assert success is True
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'token_type' in data
        assert 'expires_in' in data

    @pytest.mark.django_db
    def test_login_updates_last_login(self):
        """Le login met à jour last_login."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("GenTokensApp2")
        user = _user("gentokens2@test.com")
        user.last_login = None
        user.save()
        
        service = AuthService()
        service.authenticate_by_email(
            "gentokens2@test.com", "Pass123!", app, "1.2.3.4"
        )
        
        user.refresh_from_db()
        assert user.last_login is not None

    @pytest.mark.django_db
    def test_login_creates_refresh_token_in_db(self):
        """Le login crée un refresh token en DB."""
        from tests.integration.django.auth_service_compat import AuthService
        
        app = _app("GenTokensApp3")
        user = _user("gentokens3@test.com")
        service = AuthService()
        
        before_count = RefreshToken.objects.filter(user=user).count()
        service.authenticate_by_email(
            "gentokens3@test.com", "Pass123!", app, "1.2.3.4"
        )
        after_count = RefreshToken.objects.filter(user=user).count()
        
        assert after_count == before_count + 1


# ===========================================================================
# Timing Attack Mitigation Tests - DÉPLACÉS vers tests/core/
# ===========================================================================
# Les 3 tests de protection timing attack ont été déplacés vers:
# tests/core/test_timing_attack_mitigation.py
#
# Raison: Tests d'implémentation interne à faire au niveau du service core,
# pas au niveau du wrapper de compatibilité
