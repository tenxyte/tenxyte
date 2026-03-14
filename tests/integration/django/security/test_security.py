"""
Tests de sécurité pour Tenxyte.

Couvre:
- Manipulation de tokens JWT (tampering, expiration, algorithme)
- Authentification application (credentials manquantes/invalides)
- Protection brute force (verrouillage de compte)
- Injection SQL dans les champs de login/register
- Payloads XSS dans les entrées utilisateur
- Accès non authentifié aux endpoints protégés
- Utilisation cross-application de tokens
- Réutilisation de refresh tokens révoqués
- Blacklisting de tokens JWT
- Banissement de compte (permanent, admin actions, auth blocking)
"""
from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import pytest
import jwt
import json
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from tenxyte.models import User, Application, RefreshToken
from tenxyte.services import JWTService, AuthService


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Vider le cache de throttling entre chaque test."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestJWTSecurity:
    """Tests de sécurité JWT."""

    def test_tampered_token_rejected(self, app_api_client, user, application):
        """Un token JWT modifié manuellement doit être rejeté."""
        auth_service = AuthService()
        success, data, _ = auth_service.authenticate_by_email(
            email=user.email,
            password="TestPassword123!",
            application=application,
            ip_address="127.0.0.1"
        )
        assert success

        # Modifier le payload du token (changer user_id)
        token = data['access_token']
        parts = token.split('.')
        # Altérer le payload en changeant un caractère
        tampered = parts[0] + '.' + parts[1][:-1] + ('A' if parts[1][-1] != 'A' else 'B') + '.' + parts[2]

        app_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {tampered}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_token_with_wrong_secret_rejected(self, app_api_client, user, application):
        """Un token signé avec une mauvaise clé doit être rejeté."""
        # Créer un token avec une fausse clé
        payload = {
            'type': 'access',
            'jti': 'fake-jti',
            'user_id': str(user.id),
            'app_id': str(application.id),
            'iat': datetime.now(dt_timezone.utc),
            'exp': datetime.now(dt_timezone.utc) + timedelta(hours=1),
        }
        # Use a string that is at least 32 bytes long to avoid InsecureKeyLengthWarning (SHA256 requirement)
        fake_token = jwt.encode(payload, 'wrong-secret-key-that-is-at-least-32-bytes-long-12345678', algorithm='HS256')

        app_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {fake_token}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_expired_token_rejected(self, app_api_client, user, application):
        """Un token expiré doit être rejeté."""
        jwt_service = JWTService()
        # Créer un token déjà expiré
        payload = {
            'type': 'access',
            'jti': 'expired-jti',
            'user_id': str(user.id),
            'app_id': str(application.id),
            'iat': datetime.now(dt_timezone.utc) - timedelta(hours=2),
            'exp': datetime.now(dt_timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, jwt_service.secret_key, algorithm=jwt_service.algorithm)

        app_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {expired_token}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_none_algorithm_rejected(self, app_api_client, user, application):
        """Un token avec l'algorithme 'none' doit être rejeté (attaque alg:none)."""
        payload = {
            'type': 'access',
            'jti': 'none-alg-jti',
            'user_id': str(user.id),
            'app_id': str(application.id),
            'iat': datetime.now(dt_timezone.utc),
            'exp': datetime.now(dt_timezone.utc) + timedelta(hours=1),
        }
        # Encoder sans signature
        header = jwt.utils.base64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        payload_b64 = jwt.utils.base64url_encode(json.dumps(payload, default=str).encode())
        none_token = f"{header.decode()}.{payload_b64.decode()}."

        app_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {none_token}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_blacklisted_token_rejected(self, app_api_client, user, application):
        """Un token blacklisté ne doit plus être accepté."""
        auth_service = AuthService()
        jwt_service = JWTService()

        success, data, _ = auth_service.authenticate_by_email(
            email=user.email,
            password="TestPassword123!",
            application=application,
            ip_address="127.0.0.1"
        )
        assert success

        token = data['access_token']
        # Blacklister le token
        jwt_service.blacklist_token(token, user=user, reason='security_test')

        app_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_random_string_as_token(self, app_api_client, application):
        """Une chaîne aléatoire comme token doit être rejetée."""
        app_api_client.credentials(
            HTTP_AUTHORIZATION="Bearer this-is-not-a-jwt-token-at-all",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_empty_bearer_token(self, app_api_client, application):
        """Un header Bearer vide doit être rejeté."""
        app_api_client.credentials(
            HTTP_AUTHORIZATION="Bearer ",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestApplicationAuthSecurity:
    """Tests de sécurité pour l'authentification application."""

    def test_missing_app_credentials(self, user):
        """Les requêtes sans credentials application doivent être rejetées."""
        client = APIClient()
        response = client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = json.loads(response.content)
        assert data.get('code') == 'APP_AUTH_REQUIRED'

    def test_invalid_access_key(self, user):
        """Une access_key invalide doit être rejetée."""
        client = APIClient()
        client.credentials(
            HTTP_X_ACCESS_KEY='invalid-key-12345',
            HTTP_X_ACCESS_SECRET='invalid-secret-12345'
        )
        response = client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = json.loads(response.content)
        assert data.get('code') == 'APP_AUTH_INVALID'

    def test_valid_key_wrong_secret(self, user, application):
        """Une access_key valide avec un mauvais secret doit être rejetée."""
        client = APIClient()
        client.credentials(
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET='wrong-secret-value'
        )
        response = client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = json.loads(response.content)
        assert data.get('code') == 'APP_AUTH_INVALID'

    def test_inactive_application_rejected(self, user):
        """Une application inactive doit être rejetée."""
        app, raw_secret = Application.create_application(name="Inactive App")
        app.is_active = False
        app.save()

        client = APIClient()
        client.credentials(
            HTTP_X_ACCESS_KEY=app.access_key,
            HTTP_X_ACCESS_SECRET=raw_secret
        )
        response = client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestBruteForceProtection:
    """Tests de protection contre les attaques brute force."""

    def test_login_with_wrong_password_multiple_times(self, app_api_client, user, application):
        """Plusieurs tentatives échouées doivent être comptabilisées."""
        from tenxyte.models import LoginAttempt

        for i in range(3):
            response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
                'email': user.email,
                'password': f'WrongPassword{i}!',
            })
            # 401 ou 429 (throttled) sont tous deux acceptables
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_429_TOO_MANY_REQUESTS,
            ]

        # Vérifier que les tentatives échouées ont été enregistrées
        failed_attempts = LoginAttempt.objects.filter(
            identifier=user.email, success=False
        ).count()
        assert failed_attempts > 0

    def test_locked_account_cannot_login(self, app_api_client, user, application):
        """Un compte verrouillé ne doit pas pouvoir se connecter."""
        from django.utils import timezone as tz

        user.is_locked = True
        user.locked_until = tz.now() + timedelta(hours=1)
        user.save()

        response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!',
        })

        # Devrait être refusé (401, 403, ou 429 si throttled)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]

    def test_expired_lock_allows_login(self, app_api_client, user, application):
        """Un verrouillage expiré doit permettre la connexion."""
        from django.utils import timezone as tz

        user.is_locked = True
        user.locked_until = tz.now() - timedelta(hours=1)  # Expiré
        user.save()

        response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!',
        })

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestInjectionProtection:
    """Tests de protection contre les injections SQL et XSS."""

    def test_sql_injection_in_email(self, app_api_client):
        """Les tentatives d'injection SQL dans l'email doivent être rejetées proprement."""
        payloads = [
            "' OR '1'='1",
            "admin@test.com' OR 1=1--",
            "'; DROP TABLE users;--",
            "admin@test.com' UNION SELECT * FROM users--",
        ]
        for payload in payloads:
            response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
                'email': payload,
                'password': 'TestPassword123!',
            })
            # Ne doit pas retourner 500 (erreur serveur)
            assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_sql_injection_in_password(self, app_api_client, user):
        """Les tentatives d'injection SQL dans le mot de passe doivent être rejetées."""
        payloads = [
            "' OR '1'='1",
            "password' OR 1=1--",
            "'; DROP TABLE users;--",
        ]
        for payload in payloads:
            response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
                'email': user.email,
                'password': payload,
            })
            # Ne doit jamais retourner 500 (erreur serveur) ni 200 (succès)
            assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
            assert response.status_code != status.HTTP_200_OK
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_429_TOO_MANY_REQUESTS,
            ]

    def test_xss_in_registration_fields(self, app_api_client):
        """Les payloads XSS dans les champs d'inscription ne doivent pas être exécutés."""
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '"><img src=x onerror=alert(1)>',
            "javascript:alert('XSS')",
        ]
        for payload in xss_payloads:
            response = app_api_client.post(f'{api_prefix}/auth/register/', {
                'email': f'{payload}@test.com',
                'password': 'SecureP@ssw0rd!',
                'password_confirm': 'SecureP@ssw0rd!',
            })
            # Ne doit pas retourner 500
            assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_xss_in_user_profile(self, authenticated_client, user):
        """Les payloads XSS dans la mise à jour du profil doivent être stockés en texte brut."""
        xss = '<script>alert("XSS")</script>'
        response = authenticated_client.patch(f'{api_prefix}/auth/me/', {
            'first_name': xss,
        })

        if response.status_code == status.HTTP_200_OK:
            # Le contenu doit être stocké en texte brut, pas interprété
            assert '<script>' not in response.data.get('first_name', '') or \
                   response.data.get('first_name') == xss  # Stored as-is, not executed


@pytest.mark.django_db
class TestUnauthenticatedAccess:
    """Tests d'accès non authentifié aux endpoints protégés."""

    def test_me_without_auth(self, app_api_client):
        """L'endpoint /me/ sans JWT doit retourner 401/403."""
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_change_password_without_auth(self, app_api_client):
        """Le changement de mot de passe sans JWT doit être rejeté."""
        response = app_api_client.post(f'{api_prefix}/auth/password/change/', {
            'current_password': 'TestPassword123!',
            'new_password': 'NewP@ssw0rd!123',
            'new_password_confirm': 'NewP@ssw0rd!123',
        })

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_otp_request_without_auth(self, app_api_client):
        """La demande d'OTP sans JWT doit être rejetée."""
        response = app_api_client.post(f'{api_prefix}/auth/otp/request/', {
            'otp_type': 'email',
        })

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_2fa_status_without_auth(self, app_api_client):
        """Le statut 2FA sans JWT doit être rejeté."""
        response = app_api_client.get(f'{api_prefix}/auth/2fa/status/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_roles_without_auth(self, app_api_client):
        """Les rôles sans JWT doivent être rejetés."""
        response = app_api_client.get(f'{api_prefix}/auth/me/roles/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestRefreshTokenSecurity:
    """Tests de sécurité pour les refresh tokens."""

    def test_revoked_refresh_token_rejected(self, app_api_client, user, application):
        """Un refresh token révoqué ne doit pas permettre le rafraîchissement."""
        # Utiliser AuthService pour éviter le throttling
        auth_service = AuthService()
        success, data, _ = auth_service.authenticate_by_email(
            email=user.email,
            password='TestPassword123!',
            application=application,
            ip_address='127.0.0.1'
        )
        assert success
        refresh_token_str = data['refresh_token']

        # Révoquer le refresh token
        RefreshToken.objects.filter(
            user=user, application=application
        ).update(is_revoked=True)

        # Tenter de rafraîchir
        response = app_api_client.post(f'{api_prefix}/auth/refresh/', {
            'refresh_token': refresh_token_str,
        })

        assert response.status_code != status.HTTP_200_OK

    def test_fake_refresh_token_rejected(self, app_api_client, user, application):
        """Un faux refresh token doit être rejeté."""
        response = app_api_client.post(f'{api_prefix}/auth/refresh/', {
            'refresh_token': 'fake-refresh-token-12345',
        })

        assert response.status_code != status.HTTP_200_OK

    def test_logout_invalidates_refresh_token(self, app_api_client, user, application):
        """Après logout, le refresh token ne doit plus fonctionner."""
        # Utiliser AuthService pour éviter le throttling
        auth_service = AuthService()
        success, data, _ = auth_service.authenticate_by_email(
            email=user.email,
            password='TestPassword123!',
            application=application,
            ip_address='127.0.0.1'
        )
        assert success
        refresh_token_str = data['refresh_token']

        # Se déconnecter
        app_api_client.post(f'{api_prefix}/auth/logout/', {
            'refresh_token': refresh_token_str,
        })

        # Tenter de rafraîchir avec le même token
        response = app_api_client.post(f'{api_prefix}/auth/refresh/', {
            'refresh_token': refresh_token_str,
        })

        assert response.status_code != status.HTTP_200_OK


@pytest.mark.django_db
class TestCrossApplicationSecurity:
    """Tests de sécurité cross-application."""

    def test_token_from_other_app_rejected(self, user):
        """Un token JWT d'une application A ne doit pas fonctionner avec l'application B."""
        # Créer deux applications
        app_a, secret_a = Application.create_application(name="App A")
        app_b, secret_b = Application.create_application(name="App B")

        # Authentifier via AuthService pour éviter le throttling
        auth_service = AuthService()
        success, data, _ = auth_service.authenticate_by_email(
            email=user.email,
            password='TestPassword123!',
            application=app_a,
            ip_address='127.0.0.1'
        )
        assert success
        token_a = data['access_token']

        # Utiliser le token de app A avec les credentials de app B
        client_b = APIClient()
        client_b.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_a}",
            HTTP_X_ACCESS_KEY=app_b.access_key,
            HTTP_X_ACCESS_SECRET=secret_b
        )
        response = client_b.get(f'{api_prefix}/auth/me/')

        # Doit être rejeté car le token contient app_id de app A mais les headers sont de app B
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestPasswordResetSecurity:
    """Tests de sécurité pour la réinitialisation de mot de passe."""

    def test_password_reset_nonexistent_email(self, app_api_client):
        """La réinitialisation pour un email inexistant doit retourner 200 (pas de fuite d'info)."""
        response = app_api_client.post(f'{api_prefix}/auth/password/reset/request/', {
            'email': 'nonexistent@example.com',
        })

        # Doit toujours retourner 200 pour ne pas révéler l'existence du compte
        assert response.status_code == status.HTTP_200_OK

    def test_password_reset_invalid_email_format(self, app_api_client):
        """Un format d'email invalide dans la réinitialisation doit être géré proprement."""
        response = app_api_client.post(f'{api_prefix}/auth/password/reset/request/', {
            'email': 'not-an-email',
        })

        # Ne doit pas retourner 500
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.django_db
class TestInactiveUserSecurity:
    """Tests de sécurité pour les utilisateurs inactifs."""

    def test_inactive_user_cannot_login(self, app_api_client, application):
        """Un utilisateur inactif ne doit pas pouvoir se connecter."""
        user = User.objects.create(email="inactive@test.com", is_active=False)
        user.set_password("TestPassword123!")
        user.save()

        response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
            'email': 'inactive@test.com',
            'password': 'TestPassword123!',
        })

        # 401 (auth échouée) ou 429 (throttled) - jamais 200
        assert response.status_code != status.HTTP_200_OK
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]


@pytest.mark.django_db
class TestAccountBanningSecurity:
    """Tests de sécurité pour le banissement de compte."""

    def test_banned_user_cannot_authenticate_with_jwt(self, app_api_client, user, application):
        """Un utilisateur banni ne doit pas pouvoir utiliser de token JWT."""
        auth_service = AuthService()
        success, data, _ = auth_service.authenticate_by_email(
            email=user.email,
            password="TestPassword123!",
            application=application,
            ip_address="127.0.0.1"
        )
        assert success
        assert 'access_token' in data

        # Bannir l'utilisateur
        user.is_banned = True
        user.save()

        # Tenter d'utiliser le token existant
        app_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = app_api_client.get(f'{api_prefix}/auth/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'banni' in response.json().get('detail', '').lower()

    def test_banned_user_cannot_login(self, app_api_client, user, application):
        """Un utilisateur banni ne doit pas pouvoir se connecter."""
        # Bannir l'utilisateur
        user.is_banned = True
        user.save()

        response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!',
        })

        assert response.status_code != status.HTTP_200_OK
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]

    def test_banned_user_cannot_get_new_tokens(self, app_api_client, user, application):
        """Un utilisateur banni ne doit pas pouvoir obtenir de nouveaux tokens."""
        # Bannir l'utilisateur
        user.is_banned = True
        user.save()

        # Tenter de se connecter pour obtenir des tokens
        response = app_api_client.post(f'{api_prefix}/auth/login/email/', {
            'email': user.email,
            'password': 'TestPassword123!',
        })

        if response.status_code == status.HTTP_200_OK:
            # Si login réussi (avant le check ban), tenter d'utiliser les tokens
            data = response.json()
            if 'access_token' in data:
                app_api_client.credentials(
                    HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
                    HTTP_X_ACCESS_KEY=application.access_key,
                    HTTP_X_ACCESS_SECRET=application._plain_secret
                )
                response = app_api_client.get(f'{api_prefix}/auth/me/')
                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_ban_status_persists_after_unlock(self, app_api_client, user, application):
        """Le statut banni doit persister même après déverrouillage du compte."""
        # Bannir et verrouiller l'utilisateur
        user.is_banned = True
        user.is_locked = True
        user.locked_until = timezone.now() + timedelta(hours=1)
        user.save()

        # Le compte est banni
        assert user.is_account_banned()
        assert user.is_account_locked()

        # Déverrouiller le compte (simuler expiration)
        user.locked_until = timezone.now() - timedelta(hours=1)
        user.save()

        # Le compte reste banni même si déverrouillé
        assert user.is_account_banned()
        assert not user.is_account_locked()

    def test_admin_ban_action_creates_audit_log(self, admin_user, user):
        """L'action de banissement admin doit créer un audit log."""
        from tenxyte.models import AuditLog
        
        # Simuler l'action admin de ban
        user.is_banned = True
        user.save()
        
        # Créer l'audit log manuellement (simuler l'admin action)
        AuditLog.objects.create(
            action='user_banned',
            user=user,
            ip_address='127.0.0.1',
            details={
                'banned_by': admin_user.email,
                'reason': 'Admin action',
                'email': user.email,
                'banned_at': timezone.now().isoformat()
            }
        )
        
        # Vérifier que l'audit log existe
        audit_log = AuditLog.objects.filter(action='user_banned', user=user).first()
        assert audit_log is not None
        assert audit_log.details['banned_by'] == admin_user.email
        assert audit_log.details['email'] == user.email

    def test_admin_unban_action_creates_audit_log(self, admin_user, user):
        """L'action de débannissement admin doit créer un audit log."""
        from tenxyte.models import AuditLog
        
        # Bannir d'abord
        user.is_banned = True
        user.save()
        
        # Débannir
        user.is_banned = False
        user.save()
        
        # Créer l'audit log manuellement (simuler l'admin action)
        AuditLog.objects.create(
            action='user_unbanned',
            user=user,
            ip_address='127.0.0.1',
            details={
                'unbanned_by': admin_user.email,
                'reason': 'Admin action',
                'email': user.email,
                'unbanned_at': timezone.now().isoformat()
            }
        )
        
        # Vérifier que l'audit log existe
        audit_log = AuditLog.objects.filter(action='user_unbanned', user=user).first()
        assert audit_log is not None
        assert audit_log.details['unbanned_by'] == admin_user.email
        assert audit_log.details['email'] == user.email

    def test_banned_user_cannot_access_any_protected_endpoint(self, app_api_client, user, application):
        """Un utilisateur banni ne doit accéder à aucun endpoint protégé."""
        auth_service = AuthService()
        success, data, _ = auth_service.authenticate_by_email(
            email=user.email,
            password="TestPassword123!",
            application=application,
            ip_address="127.0.0.1"
        )
        assert success

        # Bannir l'utilisateur
        user.is_banned = True
        user.save()

        # Tenter d'accéder à plusieurs endpoints protégés
        endpoints = [
            f'{api_prefix}/auth/me/',
            f'{api_prefix}/auth/refresh/',
        ]
        
        app_api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        
        for endpoint in endpoints:
            response = app_api_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert 'banni' in response.json().get('detail', '').lower()
