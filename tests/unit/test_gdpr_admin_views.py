"""
Tests gdpr_admin_views.py - Admin GDPR deletion request management.

Coverage cible : views/gdpr_admin_views.py (32% → ~80%)
"""

import pytest
from unittest.mock import patch
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application, Permission, AccountDeletionRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="GdprApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, *perm_codes):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    for code in perm_codes:
        perm, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        u.direct_permissions.add(perm)
    return u


def _jwt_token(user, app):
    from tenxyte.services.jwt_service import JWTService
    return JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )["access_token"]


def _authed_request(method, path, user, app, data=None, params=None):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    kwargs = {}
    if data is not None:
        kwargs = {"data": data, "format": "json"}
    if params:
        path = path + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = getattr(factory, method)(
        path, HTTP_AUTHORIZATION=f"Bearer {token}", **kwargs
    )
    req.user = user
    req.application = app
    return req


def _make_deletion_request(user, status_val="pending"):
    with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
        req = AccountDeletionRequest.create_request(
            user=user, ip_address="1.2.3.4", user_agent="test"
        )
    req.status = status_val
    req.save()
    return req


# ===========================================================================
# DeletionRequestListView
# ===========================================================================

class TestDeletionRequestListView:

    @pytest.mark.django_db
    def test_list_returns_200_with_permission(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestListView
        app = _app("GdprListApp")
        admin = _user("gdpr_list@test.com", "gdpr.admin")

        req = _authed_request("get", "/admin/deletion-requests/", admin, app)
        view = DeletionRequestListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_returns_403_without_permission(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestListView
        app = _app("GdprListNoPerm")
        user = _user("gdpr_list_noperm@test.com")

        req = _authed_request("get", "/admin/deletion-requests/", user, app)
        view = DeletionRequestListView.as_view()
        response = view(req)

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_list_returns_401_unauthenticated(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestListView
        factory = APIRequestFactory()
        req = factory.get("/admin/deletion-requests/")
        view = DeletionRequestListView.as_view()
        response = view(req)

        assert response.status_code == 401

    @pytest.mark.django_db
    def test_list_filter_by_status(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestListView
        app = _app("GdprListFilterApp")
        admin = _user("gdpr_filter@test.com", "gdpr.admin")
        target_user = _user("gdpr_target@test.com")
        _make_deletion_request(target_user, "pending")

        req = _authed_request(
            "get", "/admin/deletion-requests/", admin, app,
            params={"status": "pending"}
        )
        view = DeletionRequestListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_user_id(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestListView
        app = _app("GdprListUserApp")
        admin = _user("gdpr_uid@test.com", "gdpr.admin")
        target_user = _user("gdpr_uid_target@test.com")
        _make_deletion_request(target_user)

        req = _authed_request(
            "get", "/admin/deletion-requests/", admin, app,
            params={"user_id": str(target_user.id)}
        )
        view = DeletionRequestListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_date_range(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestListView
        app = _app("GdprListDateApp")
        admin = _user("gdpr_date@test.com", "gdpr.admin")

        req = _authed_request(
            "get", "/admin/deletion-requests/", admin, app,
            params={"date_from": "2020-01-01", "date_to": "2030-12-31"}
        )
        view = DeletionRequestListView.as_view()
        response = view(req)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_ordering(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestListView
        app = _app("GdprListOrderApp")
        admin = _user("gdpr_order@test.com", "gdpr.admin")

        req = _authed_request(
            "get", "/admin/deletion-requests/", admin, app,
            params={"ordering": "requested_at"}
        )
        view = DeletionRequestListView.as_view()
        response = view(req)

        assert response.status_code == 200


# ===========================================================================
# DeletionRequestDetailView
# ===========================================================================

class TestDeletionRequestDetailView:

    @pytest.mark.django_db
    def test_detail_returns_200(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestDetailView
        app = _app("GdprDetailApp")
        admin = _user("gdpr_detail@test.com", "gdpr.admin")
        target_user = _user("gdpr_detail_target@test.com")
        del_req = _make_deletion_request(target_user)

        req = _authed_request("get", f"/admin/deletion-requests/{del_req.id}/", admin, app)
        view = DeletionRequestDetailView.as_view()
        response = view(req, request_id=del_req.id)

        assert response.status_code == 200
        assert "status" in response.data

    @pytest.mark.django_db
    def test_detail_returns_404_for_nonexistent(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestDetailView
        app = _app("GdprDetailNFApp")
        admin = _user("gdpr_detail_nf@test.com", "gdpr.admin")

        req = _authed_request("get", "/admin/deletion-requests/99999/", admin, app)
        view = DeletionRequestDetailView.as_view()
        response = view(req, request_id=99999)

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_detail_returns_403_without_permission(self):
        from tenxyte.views.gdpr_admin_views import DeletionRequestDetailView
        app = _app("GdprDetailNoPermApp")
        user = _user("gdpr_detail_noperm@test.com")
        target_user = _user("gdpr_detail_noperm_target@test.com")
        del_req = _make_deletion_request(target_user)

        req = _authed_request("get", f"/admin/deletion-requests/{del_req.id}/", user, app)
        view = DeletionRequestDetailView.as_view()
        response = view(req, request_id=del_req.id)

        assert response.status_code == 403


# ===========================================================================
# ProcessDeletionView
# ===========================================================================

class TestProcessDeletionView:

    @pytest.mark.django_db
    def test_process_confirmed_request_returns_200(self):
        from tenxyte.views.gdpr_admin_views import ProcessDeletionView
        app = _app("GdprProcessApp")
        admin = _user("gdpr_process@test.com", "gdpr.process")
        target_user = _user("gdpr_process_target@test.com")
        del_req = _make_deletion_request(target_user, "confirmed")

        with patch.object(del_req.__class__, 'execute_deletion', return_value=True):
            req = _authed_request(
                "post", f"/admin/deletion-requests/{del_req.id}/process/",
                admin, app, data={"admin_notes": "Approved"}
            )
            view = ProcessDeletionView.as_view()
            response = view(req, request_id=del_req.id)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_process_non_confirmed_returns_400(self):
        from tenxyte.views.gdpr_admin_views import ProcessDeletionView
        app = _app("GdprProcessBadApp")
        admin = _user("gdpr_process_bad@test.com", "gdpr.process")
        target_user = _user("gdpr_process_bad_target@test.com")
        del_req = _make_deletion_request(target_user, "pending")

        req = _authed_request(
            "post", f"/admin/deletion-requests/{del_req.id}/process/",
            admin, app, data={}
        )
        view = ProcessDeletionView.as_view()
        response = view(req, request_id=del_req.id)

        assert response.status_code == 400
        assert "INVALID_STATUS" in response.data.get("code", "")

    @pytest.mark.django_db
    def test_process_nonexistent_returns_404(self):
        from tenxyte.views.gdpr_admin_views import ProcessDeletionView
        app = _app("GdprProcessNFApp")
        admin = _user("gdpr_process_nf@test.com", "gdpr.process")

        req = _authed_request(
            "post", "/admin/deletion-requests/99999/process/",
            admin, app, data={}
        )
        view = ProcessDeletionView.as_view()
        response = view(req, request_id=99999)

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_process_returns_403_without_permission(self):
        from tenxyte.views.gdpr_admin_views import ProcessDeletionView
        app = _app("GdprProcessNoPermApp")
        user = _user("gdpr_process_noperm@test.com")
        target_user = _user("gdpr_process_noperm_target@test.com")
        del_req = _make_deletion_request(target_user, "confirmed")

        req = _authed_request(
            "post", f"/admin/deletion-requests/{del_req.id}/process/",
            user, app, data={}
        )
        view = ProcessDeletionView.as_view()
        response = view(req, request_id=del_req.id)

        assert response.status_code == 403


# ===========================================================================
# ProcessExpiredDeletionsView
# ===========================================================================

class TestProcessExpiredDeletionsView:

    @pytest.mark.django_db
    def test_process_expired_returns_200(self):
        from tenxyte.views.gdpr_admin_views import ProcessExpiredDeletionsView
        app = _app("GdprExpiredApp")
        admin = _user("gdpr_expired@test.com", "gdpr.process")

        req = _authed_request("post", "/admin/deletion-requests/process-expired/", admin, app)
        view = ProcessExpiredDeletionsView.as_view()
        response = view(req)

        assert response.status_code == 200
        assert "processed" in response.data
        assert "failed" in response.data

    @pytest.mark.django_db
    def test_process_expired_returns_403_without_permission(self):
        from tenxyte.views.gdpr_admin_views import ProcessExpiredDeletionsView
        app = _app("GdprExpiredNoPermApp")
        user = _user("gdpr_expired_noperm@test.com")

        req = _authed_request("post", "/admin/deletion-requests/process-expired/", user, app)
        view = ProcessExpiredDeletionsView.as_view()
        response = view(req)

        assert response.status_code == 403
