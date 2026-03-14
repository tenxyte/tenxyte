"""
Tests Phase 2 - ApplicationListView, ApplicationDetailView, ApplicationRegenerateView

Couvre :
- GET  /applications/          → liste paginée
- POST /applications/          → création
- GET  /applications/<id>/     → détail
- PUT  /applications/<id>/     → mise à jour
- DELETE /applications/<id>/   → suppression
- POST /applications/<id>/regenerate/ → régénération credentials
- Contrôle d'accès : 403 sans la permission, 401 sans token
"""

from tenxyte.conf import auth_settings
api_prefix = auth_settings.API_PREFIX

import json

NONEXISTENT_ID = 999999999  # ID entier qui n'existera jamais en DB (BigAutoField)
import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

from tenxyte.views.application_views import (
    ApplicationListView,
    ApplicationDetailView,
    ApplicationRegenerateView,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt_request(user, app):
    """Forge une requête authentifiée avec un vrai token JWT."""
    from tenxyte.services.jwt_service import JWTService
    tokens = JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )
    factory = APIRequestFactory()
    return tokens["access_token"], factory, app


def _authed_request(method, path, user, app, data=None):
    """Construit une requête DRF authentifiée prête à être passée à la vue."""
    from tenxyte.services.jwt_service import JWTService
    token = JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )["access_token"]

    factory = APIRequestFactory()
    kwargs = {}
    if data is not None:
        kwargs = {"data": data, "format": "json"}
    req = getattr(factory, method)(path, HTTP_AUTHORIZATION=f"Bearer {token}", **kwargs)
    req.application = app
    return req


def _setup_user_with_permissions(email, app, *permission_codes):
    """Crée un user actif avec les permissions listées et le retourne."""
    from tenxyte.models import User, Permission
    user = User.objects.create(email=email, is_active=True)
    user.set_password("pass"); user.save()
    for code in permission_codes:
        perm, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        user.direct_permissions.add(perm)
    return user


# ===========================================================================
# Tests : ApplicationListView  (GET + POST)
# ===========================================================================

class TestApplicationListView:

    @pytest.mark.django_db
    def test_list_without_token_returns_401(self):
        """Sans token → 401."""
        from django.test import RequestFactory as DRF
        factory = DRF()
        req = factory.get(f"{api_prefix}/auth/applications/")
        req.application = None
        view = ApplicationListView.as_view()
        response = view(req)
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_list_without_permission_returns_403(self):
        """Token valide mais sans la permission applications.view → 403."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="ListApp_noperm")
        user = _setup_user_with_permissions("applist_noperm@test.com", app)
        # Pas de permission applications.view

        req = _authed_request("get", f"{api_prefix}/auth/applications/", user, app)
        response = ApplicationListView.as_view()(req)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_with_permission_returns_200(self):
        """Permission applications.view → 200 avec liste."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="ListApp_ok")
        user = _setup_user_with_permissions("applist_ok@test.com", app, "applications.view")

        req = _authed_request("get", f"{api_prefix}/auth/applications/", user, app)
        response = ApplicationListView.as_view()(req)
        assert response.status_code == 200
        # La réponse doit contenir une liste (paginée ou non)
        data = response.data
        assert "results" in data or isinstance(data, list)

    @pytest.mark.django_db
    def test_create_application_success(self):
        """POST avec applications.create → 201 avec credentials."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="CreateParent")
        user = _setup_user_with_permissions("appcreate_ok@test.com", app, "applications.create")

        req = _authed_request(
            "post", f"{api_prefix}/auth/applications/", user, app,
            data={"name": "NewTestApp", "description": "Created in tests"}
        )
        response = ApplicationListView.as_view()(req)
        assert response.status_code == 201
        assert "credentials" in response.data
        assert "access_key" in response.data["credentials"]
        assert "access_secret" in response.data["credentials"]

    @pytest.mark.django_db
    def test_create_application_validation_error(self):
        """POST sans nom → 400."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="CreateParent2")
        user = _setup_user_with_permissions("appcreate_bad@test.com", app, "applications.create")

        req = _authed_request(
            "post", f"{api_prefix}/auth/applications/", user, app,
            data={"name": ""}  # nom vide
        )
        response = ApplicationListView.as_view()(req)
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_without_permission_returns_403(self):
        """POST sans la permission applications.create → 403."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="CreateNoPerm")
        user = _setup_user_with_permissions("appcreate_noperm@test.com", app)

        req = _authed_request(
            "post", f"{api_prefix}/auth/applications/", user, app,
            data={"name": "ShouldFail"}
        )
        response = ApplicationListView.as_view()(req)
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_unpaginated(self):
        from tenxyte.models import Application
        app, _ = Application.create_application(name="ListApp_unpag")
        user = _setup_user_with_permissions("applist_unpag@test.com", app, "applications.view")
        
        req = _authed_request("get", f"{api_prefix}/auth/applications/", user, app)
        with patch('tenxyte.views.application_views.TenxytePagination.paginate_queryset', return_value=None):
            response = ApplicationListView.as_view()(req)
        assert response.status_code == 200
        assert isinstance(response.data, list)



# ===========================================================================
# Tests : ApplicationDetailView  (GET + PUT + DELETE)
# ===========================================================================

class TestApplicationDetailView:

    @pytest.mark.django_db
    def test_get_detail_with_permission(self):
        """GET détail avec applications.view → 200."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="DetailApp")
        user = _setup_user_with_permissions("appdetail_ok@test.com", app, "applications.view")

        req = _authed_request("get", f"{api_prefix}/auth/applications/{app.id}/", user, app)
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 200
        assert response.data["name"] == "DetailApp"

    @pytest.mark.django_db
    def test_get_detail_not_found_returns_404(self):
        """GET avec un ID inexistant → 404."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="DetailApp404")
        user = _setup_user_with_permissions("appdetail_404@test.com", app, "applications.view")

        req = _authed_request("get", f"{api_prefix}/auth/applications/bad-id/", user, app)
        response = ApplicationDetailView.as_view()(req, app_id=NONEXISTENT_ID)
        assert response.status_code == 404
        assert response.data["code"] == "NOT_FOUND"

    @pytest.mark.django_db
    def test_get_detail_without_permission_returns_403(self):
        """GET sans applications.view → 403."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="DetailNoPerm")
        user = _setup_user_with_permissions("appdetail_noperm@test.com", app)

        req = _authed_request("get", f"{api_prefix}/auth/applications/{app.id}/", user, app)
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_update_application_success(self):
        """PUT avec applications.update → 200."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="UpdateApp")
        user = _setup_user_with_permissions("appupdate_ok@test.com", app, "applications.update")

        req = _authed_request(
            "put", f"{api_prefix}/auth/applications/{app.id}/", user, app,
            data={"name": "UpdatedName", "description": "updated desc"}
        )
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 200
        assert response.data["name"] == "UpdatedName"

    @pytest.mark.django_db
    def test_update_nonexistent_app_returns_404(self):
        """PUT sur ID inexistant → 404."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="UpdateApp404")
        user = _setup_user_with_permissions("appupdate_404@test.com", app, "applications.update")

        req = _authed_request(
            "put", f"{api_prefix}/auth/applications/bad/", user, app,
            data={"name": "X"}
        )
        response = ApplicationDetailView.as_view()(req, app_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_update_without_permission_returns_403(self):
        """PUT sans applications.update → 403."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="UpdateNoPerm")
        user = _setup_user_with_permissions("appupdate_noperm@test.com", app)

        req = _authed_request(
            "put", f"{api_prefix}/auth/applications/{app.id}/", user, app,
            data={"name": "X"}
        )
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_delete_application_success(self):
        """DELETE avec applications.delete → 200 + app supprimée."""
        from tenxyte.models import Application
        target_app, _ = Application.create_application(name="DeleteMe")
        auth_app, _ = Application.create_application(name="AuthApp_del")
        user = _setup_user_with_permissions("appdelete_ok@test.com", auth_app, "applications.delete")

        req = _authed_request("delete", f"{api_prefix}/auth/applications/{target_app.id}/", user, auth_app)
        response = ApplicationDetailView.as_view()(req, app_id=str(target_app.id))
        assert response.status_code == 200
        assert not Application.objects.filter(id=target_app.id).exists()

    @pytest.mark.django_db
    def test_delete_nonexistent_app_returns_404(self):
        """DELETE sur ID inexistant → 404."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="DeleteApp404")
        user = _setup_user_with_permissions("appdelete_404@test.com", app, "applications.delete")

        req = _authed_request("delete", f"{api_prefix}/auth/applications/bad/", user, app)
        response = ApplicationDetailView.as_view()(req, app_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_delete_without_permission_returns_403(self):
        """DELETE sans applications.delete → 403."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="DeleteNoPerm")
        user = _setup_user_with_permissions("appdelete_noperm@test.com", app)

        req = _authed_request("delete", f"{api_prefix}/auth/applications/{app.id}/", user, app)
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_update_application_validation_error(self):
        from tenxyte.models import Application
        app, _ = Application.create_application(name="UpdateAppVal")
        user = _setup_user_with_permissions("appupdate_val@test.com", app, "applications.update")

        req = _authed_request(
            "put", f"{api_prefix}/auth/applications/{app.id}/", user, app,
            data={"name": ""}
        )
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_patch_application_success(self):
        from tenxyte.models import Application
        app, _ = Application.create_application(name="PatchApp")
        user = _setup_user_with_permissions("apppatch_ok@test.com", app, "applications.update")

        req = _authed_request(
            "patch", f"{api_prefix}/auth/applications/{app.id}/", user, app,
            data={"is_active": False}
        )
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 200
        assert response.data["application"]["is_active"] is False
        assert "deactivated" in response.data["message"]
        
        req2 = _authed_request(
            "patch", f"{api_prefix}/auth/applications/{app.id}/", user, app,
            data={"is_active": True}
        )
        response2 = ApplicationDetailView.as_view()(req2, app_id=str(app.id))
        assert response2.status_code == 200
        assert "activated" in response2.data["message"]

    @pytest.mark.django_db
    def test_patch_application_invalid_fields(self):
        from tenxyte.models import Application
        app, _ = Application.create_application(name="PatchAppInv")
        user = _setup_user_with_permissions("apppatch_inv@test.com", app, "applications.update")

        req = _authed_request(
            "patch", f"{api_prefix}/auth/applications/{app.id}/", user, app,
            data={"name": "NewName"}
        )
        response = ApplicationDetailView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_patch_nonexistent_returns_404(self):
        from tenxyte.models import Application
        app, _ = Application.create_application(name="PatchApp404")
        user = _setup_user_with_permissions("apppatch_404@test.com", app, "applications.update")

        req = _authed_request(
            "patch", f"{api_prefix}/auth/applications/bad/", user, app,
            data={"is_active": False}
        )
        response = ApplicationDetailView.as_view()(req, app_id=NONEXISTENT_ID)
        assert response.status_code == 404



# ===========================================================================
# Tests : ApplicationRegenerateView  (POST)
# ===========================================================================

class TestApplicationRegenerateView:

    @pytest.mark.django_db
    def test_regenerate_success(self):
        """POST régénérer avec applications.regenerate → 200 + nouveaux credentials."""
        from tenxyte.models import Application
        target_app, _ = Application.create_application(name="RegenTarget")
        auth_app, _ = Application.create_application(name="RegenAuth")
        user = _setup_user_with_permissions("regen_ok@test.com", auth_app, "applications.regenerate")

        old_key = target_app.access_key

        req = _authed_request(
            "post", f"{api_prefix}/auth/applications/{target_app.id}/regenerate/",
            user, auth_app,
            data={"confirmation": "REGENERATE"}
        )
        response = ApplicationRegenerateView.as_view()(req, app_id=str(target_app.id))
        assert response.status_code == 200
        assert "credentials" in response.data
        # Les credentials ont été régénérés
        assert response.data["credentials"]["access_key"] != old_key

    @pytest.mark.django_db
    def test_regenerate_nonexistent_app_returns_404(self):
        """POST régénérer sur ID inexistant → 404."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="RegenApp404")
        user = _setup_user_with_permissions("regen_404@test.com", app, "applications.regenerate")

        req = _authed_request(
            "post", f"{api_prefix}/auth/applications/bad/regenerate/",
            user, app,
            data={"confirmation": "REGENERATE"}
        )
        response = ApplicationRegenerateView.as_view()(req, app_id=NONEXISTENT_ID)
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_regenerate_without_permission_returns_403(self):
        """POST régénérer sans applications.regenerate → 403."""
        from tenxyte.models import Application
        app, _ = Application.create_application(name="RegenNoPerm")
        user = _setup_user_with_permissions("regen_noperm@test.com", app)

        req = _authed_request(
            "post", f"{api_prefix}/auth/applications/{app.id}/regenerate/",
            user, app,
            data={"confirmation": "REGENERATE"}
        )
        response = ApplicationRegenerateView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_regenerate_wrong_confirmation(self):
        from tenxyte.models import Application
        app, _ = Application.create_application(name="RegenConf")
        user = _setup_user_with_permissions("regen_conf_err@test.com", app, "applications.regenerate")

        req = _authed_request(
            "post", f"{api_prefix}/auth/applications/{app.id}/regenerate/",
            user, app,
            data={"confirmation": "WRONG"}
        )
        response = ApplicationRegenerateView.as_view()(req, app_id=str(app.id))
        assert response.status_code == 400
        assert response.data["code"] == "CONFIRMATION_REQUIRED"

