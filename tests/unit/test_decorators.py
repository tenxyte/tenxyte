"""
Tests unitaires pour tenxyte/decorators.py

Couvre :
- require_jwt : pas de token, token invalide, token valide, user inactif, app mismatch, JWT désactivé
- require_role / require_any_role / require_all_roles
- require_permission / require_any_permission / require_all_permissions
- rate_limit : sous la limite, dépassement, désactivé
- get_client_ip : X-Forwarded-For, REMOTE_ADDR
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from django.test import RequestFactory
from django.http import JsonResponse

from tenxyte.decorators import (
    require_jwt,
    require_role,
    require_any_role,
    require_all_roles,
    require_permission,
    require_any_permission,
    require_all_permissions,
    rate_limit,
    get_client_ip,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dummy_view(request, *args, **kwargs):
    """Vue minimale pour vérifier que le décorateur laisse passer."""
    return JsonResponse({"ok": True}, status=200)


def make_request(method="GET", path="/", application=None, auth_header=None):
    """Forge une requête Django avec les attributs Tenxyte nécessaires."""
    factory = RequestFactory()
    kwargs = {}
    if auth_header:
        kwargs["HTTP_AUTHORIZATION"] = auth_header
    req = getattr(factory, method.lower())(path, **kwargs)
    req.application = application
    return req


def _make_jwt_request(user, app):
    """Crée une requête avec un vrai token JWT pour user + app.

    NOTE: Les décorateurs RBAC enchaînent @require_jwt en interne.
    Quand JWT_AUTH_ENABLED=True (défaut), require_jwt charge user depuis la DB
    à partir du payload. On doit donc passer un VRAI token pour un vrai user.
    """
    from tenxyte.services.jwt_service import JWTService
    jwt_service = JWTService()
    tokens = jwt_service.generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefreshtoken"
    )
    req = make_request(
        auth_header=f"Bearer {tokens['access_token']}",
        application=app,
    )
    return req


# ===========================================================================
# Tests : require_jwt
# ===========================================================================

class TestRequireJwt:
    """Tests pour le décorateur require_jwt."""

    def test_no_authorization_header_returns_401(self):
        """Sans header Authorization → 401."""
        protected = require_jwt(dummy_view)
        response = protected(make_request())
        assert response.status_code == 401
        assert json.loads(response.content)["code"] == "AUTH_REQUIRED"

    def test_malformed_header_no_bearer_prefix_returns_401(self):
        """Header sans préfixe 'Bearer ' → 401."""
        protected = require_jwt(dummy_view)
        response = protected(make_request(auth_header="Token sometoken"))
        assert response.status_code == 401

    def test_invalid_token_returns_401(self):
        """Token invalide / non décodable → 401."""
        with patch("tenxyte.decorators.JWTService") as MockJWT:
            MockJWT.return_value.decode_token.return_value = None
            protected = require_jwt(dummy_view)
            response = protected(make_request(auth_header="Bearer bad.token.here"))
        assert response.status_code == 401
        assert json.loads(response.content)["code"] == "TOKEN_INVALID"

    @pytest.mark.django_db
    def test_valid_token_calls_view(self):
        """Token valide avec utilisateur actif → 200."""
        from tenxyte.models import User, Application
        app, _ = Application.create_application(name="JWT Test App")
        user = User.objects.create(email="jwt_test@example.com", is_active=True)
        user.set_password("pass")
        user.save()

        protected = require_jwt(dummy_view)
        response = protected(_make_jwt_request(user, app))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_valid_token_inactive_user_returns_401(self):
        """Token valide mais utilisateur inactif → 401."""
        from tenxyte.models import User, Application
        app, _ = Application.create_application(name="Inactive User App")
        user = User.objects.create(email="inactive@example.com", is_active=False)
        user.set_password("pass")
        user.save()

        protected = require_jwt(dummy_view)
        response = protected(_make_jwt_request(user, app))
        assert response.status_code == 401
        assert json.loads(response.content)["code"] == "USER_INACTIVE"

    @pytest.mark.django_db
    def test_token_app_id_mismatch_returns_401(self):
        """Token d'une autre application → 401."""
        from tenxyte.models import User, Application
        from tenxyte.services.jwt_service import JWTService

        app1, _ = Application.create_application(name="App1_mm")
        app2, _ = Application.create_application(name="App2_mm")
        user = User.objects.create(email="mismatch@example.com", is_active=True)
        user.set_password("pass")
        user.save()

        tokens = JWTService().generate_token_pair(
            user_id=str(user.id),
            application_id=str(app1.id),
            refresh_token_str="dummy"
        )
        request = make_request(
            auth_header=f"Bearer {tokens['access_token']}",
            application=app2,
        )
        response = require_jwt(dummy_view)(request)
        assert response.status_code == 401
        assert json.loads(response.content)["code"] == "TOKEN_APP_MISMATCH"

    @patch("tenxyte.decorators.auth_settings")
    def test_jwt_disabled_bypasses_auth(self, mock_settings):
        """Avec JWT_AUTH_ENABLED=False → 200 sans token."""
        mock_settings.JWT_AUTH_ENABLED = False
        response = require_jwt(dummy_view)(make_request())
        assert response.status_code == 200

    def test_as_cbv_method_decorator_no_token(self):
        """require_jwt sur méthode CBV (self, request) → 401 sans token."""
        class MyView:
            @require_jwt
            def get(self, request, *args, **kwargs):
                return JsonResponse({"ok": True})

        response = MyView().get(make_request())
        assert response.status_code == 401


# ===========================================================================
# Tests : require_role
# ===========================================================================

class TestRequireRole:
    """Tests pour require_role."""

    @pytest.mark.django_db
    def test_user_with_correct_role_gets_access(self):
        """Utilisateur avec le bon rôle → 200."""
        from tenxyte.models import User, Application, Role
        app, _ = Application.create_application(name="RoleApp1")
        user = User.objects.create(email="role_ok@example.com", is_active=True)
        user.set_password("pass"); user.save()
        role, _ = Role.objects.get_or_create(code="admin_dec_t", defaults={"name": "Admin Dec T"})
        user.roles.add(role)

        @require_role("admin_dec_t")
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 200

    @pytest.mark.django_db
    def test_user_without_role_gets_403(self):
        """Utilisateur sans le rôle → 403."""
        from tenxyte.models import User, Application
        app, _ = Application.create_application(name="RoleApp2")
        user = User.objects.create(email="role_missing@example.com", is_active=True)
        user.set_password("pass"); user.save()

        @require_role("superuser_only")
        def view(request):
            return JsonResponse({"ok": True})

        response = view(_make_jwt_request(user, app))
        assert response.status_code == 403
        assert json.loads(response.content)["code"] == "ROLE_REQUIRED"


class TestRequireAnyRole:
    """Tests pour require_any_role."""

    @pytest.mark.django_db
    def test_one_matching_role_gets_access(self):
        """Au moins un rôle correspond → 200."""
        from tenxyte.models import User, Application, Role
        app, _ = Application.create_application(name="AnyRoleApp1")
        user = User.objects.create(email="any_role_ok@example.com", is_active=True)
        user.set_password("pass"); user.save()
        role, _ = Role.objects.get_or_create(code="manager_dec", defaults={"name": "Manager Dec"})
        user.roles.add(role)

        @require_any_role(["admin_dec", "manager_dec"])
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 200

    @pytest.mark.django_db
    def test_no_matching_role_gets_403(self):
        """Aucun rôle ne correspond → 403."""
        from tenxyte.models import User, Application
        app, _ = Application.create_application(name="AnyRoleApp2")
        user = User.objects.create(email="any_role_none@example.com", is_active=True)
        user.set_password("pass"); user.save()

        @require_any_role(["admin_dec2", "manager_dec2"])
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 403


class TestRequireAllRoles:
    """Tests pour require_all_roles."""

    @pytest.mark.django_db
    def test_all_roles_present_gets_access(self):
        """Tous les rôles présents → 200."""
        from tenxyte.models import User, Application, Role
        app, _ = Application.create_application(name="AllRoleApp1")
        user = User.objects.create(email="all_roles_ok@example.com", is_active=True)
        user.set_password("pass"); user.save()
        r1, _ = Role.objects.get_or_create(code="role_a", defaults={"name": "Role A"})
        r2, _ = Role.objects.get_or_create(code="role_b", defaults={"name": "Role B"})
        user.roles.add(r1, r2)

        @require_all_roles(["role_a", "role_b"])
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 200

    @pytest.mark.django_db
    def test_missing_one_role_gets_403(self):
        """Un seul rôle manquant → 403."""
        from tenxyte.models import User, Application, Role
        app, _ = Application.create_application(name="AllRoleApp2")
        user = User.objects.create(email="all_roles_missing@example.com", is_active=True)
        user.set_password("pass"); user.save()
        r1, _ = Role.objects.get_or_create(code="role_c", defaults={"name": "Role C"})
        user.roles.add(r1)  # role_d manquant

        @require_all_roles(["role_c", "role_d"])
        def view(request):
            return JsonResponse({"ok": True})

        response = view(_make_jwt_request(user, app))
        assert response.status_code == 403
        assert json.loads(response.content)["code"] == "ROLES_REQUIRED"


# ===========================================================================
# Tests : require_permission
# ===========================================================================

class TestRequirePermission:
    """Tests pour require_permission."""

    @pytest.mark.django_db
    def test_direct_permission_gets_access(self):
        """Permission directe sur l'user → 200."""
        from tenxyte.models import User, Application, Permission
        app, _ = Application.create_application(name="PermApp1")
        user = User.objects.create(email="perm_direct@example.com", is_active=True)
        user.set_password("pass"); user.save()
        perm, _ = Permission.objects.get_or_create(code="users.create_dec", defaults={"name": "Users Create Dec"})
        user.direct_permissions.add(perm)

        @require_permission("users.create_dec")
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 200

    @pytest.mark.django_db
    def test_permission_via_role_gets_access(self):
        """Permission héritée d'un rôle → 200."""
        from tenxyte.models import User, Application, Role, Permission
        app, _ = Application.create_application(name="PermApp2")
        user = User.objects.create(email="perm_via_role@example.com", is_active=True)
        user.set_password("pass"); user.save()
        perm, _ = Permission.objects.get_or_create(code="users.view_dec", defaults={"name": "Users View Dec"})
        role, _ = Role.objects.get_or_create(code="viewer_dec", defaults={"name": "Viewer Dec"})
        role.permissions.add(perm)
        user.roles.add(role)

        @require_permission("users.view_dec")
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 200

    @pytest.mark.django_db
    def test_no_permission_gets_403(self):
        """Aucune permission → 403."""
        from tenxyte.models import User, Application
        app, _ = Application.create_application(name="PermApp3")
        user = User.objects.create(email="perm_none@example.com", is_active=True)
        user.set_password("pass"); user.save()

        @require_permission("users.delete_dec")
        def view(request):
            return JsonResponse({"ok": True})

        response = view(_make_jwt_request(user, app))
        assert response.status_code == 403
        assert json.loads(response.content)["code"] == "PERMISSION_REQUIRED"


class TestRequireAnyPermission:
    """Tests pour require_any_permission."""

    @pytest.mark.django_db
    def test_one_matching_gets_access(self):
        """Une permission parmi les requises → 200."""
        from tenxyte.models import User, Application, Permission
        app, _ = Application.create_application(name="AnyPermApp1")
        user = User.objects.create(email="anyperm_ok@example.com", is_active=True)
        user.set_password("pass"); user.save()
        perm, _ = Permission.objects.get_or_create(code="users.view_any", defaults={"name": "Users View Any"})
        user.direct_permissions.add(perm)

        @require_any_permission(["users.create_any", "users.view_any"])
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 200

    @pytest.mark.django_db
    def test_no_match_gets_403(self):
        """Aucune permission requise → 403."""
        from tenxyte.models import User, Application
        app, _ = Application.create_application(name="AnyPermApp2")
        user = User.objects.create(email="anyperm_none@example.com", is_active=True)
        user.set_password("pass"); user.save()

        @require_any_permission(["users.create_any2", "users.delete_any2"])
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 403


class TestRequireAllPermissions:
    """Tests pour require_all_permissions."""

    @pytest.mark.django_db
    def test_all_present_gets_access(self):
        """Toutes les permissions présentes → 200."""
        from tenxyte.models import User, Application, Permission
        app, _ = Application.create_application(name="AllPermApp1")
        user = User.objects.create(email="allperm_ok@example.com", is_active=True)
        user.set_password("pass"); user.save()
        p1, _ = Permission.objects.get_or_create(code="perm.x", defaults={"name": "Perm X"})
        p2, _ = Permission.objects.get_or_create(code="perm.y", defaults={"name": "Perm Y"})
        user.direct_permissions.add(p1, p2)

        @require_all_permissions(["perm.x", "perm.y"])
        def view(request):
            return JsonResponse({"ok": True})

        assert view(_make_jwt_request(user, app)).status_code == 200

    @pytest.mark.django_db
    def test_one_missing_gets_403(self):
        """Une permission manquante → 403."""
        from tenxyte.models import User, Application, Permission
        app, _ = Application.create_application(name="AllPermApp2")
        user = User.objects.create(email="allperm_missing@example.com", is_active=True)
        user.set_password("pass"); user.save()
        p1, _ = Permission.objects.get_or_create(code="perm.z1", defaults={"name": "Perm Z1"})
        user.direct_permissions.add(p1)  # perm.z2 manquante

        @require_all_permissions(["perm.z1", "perm.z2"])
        def view(request):
            return JsonResponse({"ok": True})

        response = view(_make_jwt_request(user, app))
        assert response.status_code == 403
        assert json.loads(response.content)["code"] == "PERMISSIONS_REQUIRED"


# ===========================================================================
# Tests : rate_limit
# ===========================================================================

class TestRateLimit:
    """Tests pour le décorateur rate_limit."""

    @patch("tenxyte.decorators.auth_settings")
    def test_under_limit_calls_view(self, mock_settings):
        """Requêtes sous la limite → 200."""
        mock_settings.RATE_LIMITING_ENABLED = True

        @rate_limit(max_requests=5, window_seconds=60)
        def view(request):
            return JsonResponse({"ok": True})

        from django.core.cache import cache
        cache.clear()
        factory = RequestFactory()
        req = factory.get("/")
        req.META["REMOTE_ADDR"] = "10.0.0.1"
        assert view(req).status_code == 200

    @patch("tenxyte.decorators.auth_settings")
    def test_exceeding_limit_returns_429(self, mock_settings):
        """Après N requêtes, la N+1 retourne 429."""
        mock_settings.RATE_LIMITING_ENABLED = True

        @rate_limit(max_requests=2, window_seconds=60)
        def view(request):
            return JsonResponse({"ok": True})

        from django.core.cache import cache
        cache.clear()
        factory = RequestFactory()
        req = factory.get("/")
        req.META["REMOTE_ADDR"] = "10.0.0.50"

        assert view(req).status_code == 200
        assert view(req).status_code == 200
        r3 = view(req)
        assert r3.status_code == 429
        assert json.loads(r3.content)["code"] == "RATE_LIMITED"

    @patch("tenxyte.decorators.auth_settings")
    def test_rate_limit_disabled_always_calls_view(self, mock_settings):
        """Rate limiting désactivé → vue toujours appelée même à max_requests=1."""
        mock_settings.RATE_LIMITING_ENABLED = False

        @rate_limit(max_requests=1, window_seconds=60)
        def view(request):
            return JsonResponse({"ok": True})

        factory = RequestFactory()
        req = factory.get("/")
        req.META["REMOTE_ADDR"] = "10.0.0.99"
        for _ in range(5):
            assert view(req).status_code == 200

    @patch("tenxyte.decorators.auth_settings")
    def test_rate_limit_uses_user_id_key_when_authenticated(self, mock_settings):
        """Avec user authentifié, la limite est calculée par user_id."""
        mock_settings.RATE_LIMITING_ENABLED = True

        @rate_limit(max_requests=3, window_seconds=60)
        def view(request):
            return JsonResponse({"ok": True})

        from django.core.cache import cache
        cache.clear()
        factory = RequestFactory()
        req = factory.get("/")
        req.META["REMOTE_ADDR"] = "10.0.0.2"
        user_mock = MagicMock()
        user_mock.id = "test-user-ratelimit"
        req.user = user_mock
        assert view(req).status_code == 200


# ===========================================================================
# Tests : get_client_ip
# ===========================================================================

class TestGetClientIp:
    """Tests pour la fonction get_client_ip."""

    def test_returns_remote_addr_without_forwarded_for(self):
        factory = RequestFactory()
        req = factory.get("/")
        req.META["REMOTE_ADDR"] = "192.168.1.10"
        assert get_client_ip(req) == "192.168.1.10"

    def test_returns_first_ip_from_forwarded_for(self):
        factory = RequestFactory()
        req = factory.get("/")
        req.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.5, 10.0.0.1, 172.16.0.1"
        assert get_client_ip(req) == "203.0.113.5"

    def test_single_ip_in_forwarded_for(self):
        factory = RequestFactory()
        req = factory.get("/")
        req.META["HTTP_X_FORWARDED_FOR"] = "8.8.8.8"
        assert get_client_ip(req) == "8.8.8.8"

    def test_forwarded_for_strips_spaces(self):
        factory = RequestFactory()
        req = factory.get("/")
        req.META["HTTP_X_FORWARDED_FOR"] = "  1.2.3.4  , 5.6.7.8"
        assert get_client_ip(req) == "1.2.3.4"

    def test_fallback_to_default_when_no_addr(self):
        factory = RequestFactory()
        req = factory.get("/")
        req.META.pop("REMOTE_ADDR", None)
        req.META.pop("HTTP_X_FORWARDED_FOR", None)
        assert get_client_ip(req) == "0.0.0.0"
