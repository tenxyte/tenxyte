"""
Tests user_views.py — MeView, MyRolesView, UserListView, UserDetailView,
UserBanView, UserUnbanView, UserLockView, UserUnlockView.

Coverage cible : views/user_views.py (41% → 80%)
"""

import pytest
from unittest.mock import patch
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application, Permission
from tenxyte.views.user_views import (
    MeView, MyRolesView, UserListView, UserDetailView,
    UserBanView, UserUnbanView, UserLockView, UserUnlockView,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="UserViewApp"):
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
    from tests.integration.django.test_helpers import create_jwt_token
    return create_jwt_token(user, app)["access_token"]


def _authed_get(view_cls, path, user, app, **url_kwargs):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    return view_cls.as_view()(req, **url_kwargs)


def _authed_post(view_cls, path, user, app, data=None, **url_kwargs):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.post(path, data=data or {}, format="json",
                       HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    return view_cls.as_view()(req, **url_kwargs)


def _authed_patch(view_cls, path, user, app, data=None, **url_kwargs):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.patch(path, data=data or {}, format="json",
                        HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    return view_cls.as_view()(req, **url_kwargs)


def _authed_delete(view_cls, path, user, app, **url_kwargs):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.delete(path, HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    return view_cls.as_view()(req, **url_kwargs)


# ===========================================================================
# MeView
# ===========================================================================

class TestMeView:

    @pytest.mark.django_db
    def test_get_profile_success(self):
        app = _app("MeView1")
        user = _user("me1@test.com")

        resp = _authed_get(MeView, "/auth/me/", user, app)

        assert resp.status_code == 200
        assert resp.data["email"] == "me1@test.com"

    @pytest.mark.django_db
    def test_patch_profile_success(self):
        app = _app("MeView2")
        user = _user("me2@test.com")

        resp = _authed_patch(MeView, "/auth/me/", user, app,
                             data={"first_name": "Updated"})

        assert resp.status_code == 200
        assert resp.data["user"]["first_name"] == "Updated"

    @pytest.mark.django_db
    def test_patch_profile_resets_verification_on_contact_change(self):
        # VULN-005 Mitigation Check
        app = _app("MeView5")
        user = _user("me5@test.com")
        user.is_email_verified = True
        user.is_phone_verified = True
        user.save()

        resp = _authed_patch(MeView, "/auth/me/", user, app,
                             data={"email": "new_email@test.com", "phone_number": "699999999"})

        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.is_email_verified is False
        assert user.is_phone_verified is False
        assert user.email == "new_email@test.com"

    @pytest.mark.django_db
    def test_patch_profile_invalid_data_returns_400(self):
        app = _app("MeView3")
        user = _user("me3@test.com")

        # email field with invalid format
        resp = _authed_patch(MeView, "/auth/me/", user, app,
                             data={"email": "not-an-email"})

        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_get_profile_requires_auth(self):
        app = _app("MeView4")
        factory = APIRequestFactory()
        req = factory.get("/auth/me/")
        req.application = app
        resp = MeView.as_view()(req)
        assert resp.status_code == 401 or resp.status_code == 403


# ===========================================================================
# MyRolesView
# ===========================================================================

class TestMyRolesView:

    @pytest.mark.django_db
    def test_get_roles_and_permissions(self):
        app = _app("MyRoles1")
        user = _user("myroles1@test.com", "users.view")

        resp = _authed_get(MyRolesView, "/auth/me/roles/", user, app)

        assert resp.status_code == 200
        assert "roles" in resp.data
        assert "permissions" in resp.data

    @pytest.mark.django_db
    def test_get_roles_requires_jwt(self):
        app = _app("MyRoles2")
        factory = APIRequestFactory()
        req = factory.get("/auth/me/roles/")
        req.application = app
        resp = MyRolesView.as_view()(req)
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_permissions_includes_direct_permissions(self):
        app = _app("MyRoles3")
        user = _user("myroles3@test.com", "users.view", "users.update")

        resp = _authed_get(MyRolesView, "/auth/me/roles/", user, app)

        assert resp.status_code == 200
        perms = resp.data["permissions"]
        assert "users.view" in perms
        assert "users.update" in perms


# ===========================================================================
# UserListView
# ===========================================================================

class TestUserListView:

    @pytest.mark.django_db
    def test_list_users_with_permission(self):
        app = _app("UserList1")
        admin = _user("userlist_admin1@test.com", "users.view")
        _user("userlist_target1@test.com")

        resp = _authed_get(UserListView, "/auth/admin/users/", admin, app)

        assert resp.status_code == 200
        assert "results" in resp.data or isinstance(resp.data, list)

    @pytest.mark.django_db
    def test_list_users_without_permission_returns_403(self):
        app = _app("UserList2")
        user = _user("userlist_noperm2@test.com")

        resp = _authed_get(UserListView, "/auth/admin/users/", user, app)

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_list_users_requires_jwt(self):
        app = _app("UserList3")
        factory = APIRequestFactory()
        req = factory.get("/auth/admin/users/")
        req.application = app
        resp = UserListView.as_view()(req)
        assert resp.status_code == 401 or resp.status_code == 403

    @pytest.mark.django_db
    def test_list_users_pagination(self):
        app = _app("UserList4")
        admin = _user("userlist_admin4@test.com", "users.view")
        for i in range(5):
            _user(f"userlist_target4_{i}@test.com")

        token = _jwt_token(admin, app)
        factory = APIRequestFactory()
        req = factory.get("/auth/admin/users/?page=1&page_size=3",
                          HTTP_AUTHORIZATION=f"Bearer {token}")
        req.application = app
        req.user = admin
        resp = UserListView.as_view()(req)

        assert resp.status_code == 200


# ===========================================================================
# UserDetailView
# ===========================================================================

class TestUserDetailView:

    @pytest.mark.django_db
    def test_get_user_detail_success(self):
        app = _app("UserDetail1")
        admin = _user("userdetail_admin1@test.com", "users.view")
        target = _user("userdetail_target1@test.com")

        resp = _authed_get(UserDetailView, f"/auth/admin/users/{target.id}/",
                           admin, app, user_id=str(target.id))

        assert resp.status_code == 200
        assert resp.data["email"] == "userdetail_target1@test.com"

    @pytest.mark.django_db
    def test_get_user_not_found_returns_404(self):
        app = _app("UserDetail2")
        admin = _user("userdetail_admin2@test.com", "users.view")

        resp = _authed_get(UserDetailView, "/auth/admin/users/999999999/",
                           admin, app, user_id="999999999")

        assert resp.status_code == 404

    @pytest.mark.django_db
    def test_patch_user_success(self):
        app = _app("UserDetail3")
        admin = _user("userdetail_admin3@test.com", "users.update")
        target = _user("userdetail_target3@test.com")

        resp = _authed_patch(UserDetailView, f"/auth/admin/users/{target.id}/",
                             admin, app, data={"first_name": "AdminUpdated"},
                             user_id=str(target.id))

        assert resp.status_code == 200
        assert resp.data["first_name"] == "AdminUpdated"

    @pytest.mark.django_db
    def test_patch_user_not_found_returns_404(self):
        app = _app("UserDetail4")
        admin = _user("userdetail_admin4@test.com", "users.update")

        resp = _authed_patch(UserDetailView, "/auth/admin/users/999999999/",
                             admin, app, data={"first_name": "X"},
                             user_id="999999999")

        assert resp.status_code == 404

    @pytest.mark.django_db
    def test_delete_user_soft_delete(self):
        app = _app("UserDetail5")
        admin = _user("userdetail_admin5@test.com", "users.delete")
        target = _user("userdetail_target5@test.com")

        resp = _authed_delete(UserDetailView, f"/auth/admin/users/{target.id}/",
                              admin, app, user_id=str(target.id))

        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.is_deleted is True

    @pytest.mark.django_db
    def test_delete_already_deleted_returns_404(self):
        app = _app("UserDetail6")
        admin = _user("userdetail_admin6@test.com", "users.delete")
        target = _user("userdetail_target6@test.com")
        target.soft_delete()

        resp = _authed_delete(UserDetailView, f"/auth/admin/users/{target.id}/",
                              admin, app, user_id=str(target.id))

        assert resp.status_code == 404

    @pytest.mark.django_db
    def test_get_user_without_permission_returns_403(self):
        app = _app("UserDetail7")
        user = _user("userdetail_noperm7@test.com")
        target = _user("userdetail_target7@test.com")

        resp = _authed_get(UserDetailView, f"/auth/admin/users/{target.id}/",
                           user, app, user_id=str(target.id))

        assert resp.status_code == 403


# ===========================================================================
# UserBanView / UserUnbanView
# ===========================================================================

class TestUserBanUnbanView:

    @pytest.mark.django_db
    def test_ban_user_success(self):
        app = _app("BanView1")
        admin = _user("ban_admin1@test.com", "users.ban")
        target = _user("ban_target1@test.com")

        resp = _authed_post(UserBanView, f"/auth/admin/users/{target.id}/ban/",
                            admin, app, user_id=str(target.id))

        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.is_banned is True
        assert target.is_active is False

    @pytest.mark.django_db
    def test_ban_already_banned_returns_400(self):
        app = _app("BanView2")
        admin = _user("ban_admin2@test.com", "users.ban")
        target = _user("ban_target2@test.com")
        target.is_banned = True
        target.save()

        resp = _authed_post(UserBanView, f"/auth/admin/users/{target.id}/ban/",
                            admin, app, user_id=str(target.id))

        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_ban_not_found_returns_404(self):
        app = _app("BanView3")
        admin = _user("ban_admin3@test.com", "users.ban")

        resp = _authed_post(UserBanView, "/auth/admin/users/999999999/ban/",
                            admin, app, user_id="999999999")

        assert resp.status_code == 404

    @pytest.mark.django_db
    def test_ban_without_permission_returns_403(self):
        app = _app("BanView4")
        user = _user("ban_noperm4@test.com")
        target = _user("ban_target4@test.com")

        resp = _authed_post(UserBanView, f"/auth/admin/users/{target.id}/ban/",
                            user, app, user_id=str(target.id))

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_unban_user_success(self):
        app = _app("UnbanView1")
        admin = _user("unban_admin1@test.com", "users.ban")
        target = _user("unban_target1@test.com")
        target.is_banned = True
        target.is_active = False
        target.save()

        resp = _authed_post(UserUnbanView, f"/auth/admin/users/{target.id}/unban/",
                            admin, app, user_id=str(target.id))

        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.is_banned is False
        assert target.is_active is True

    @pytest.mark.django_db
    def test_unban_not_banned_returns_400(self):
        app = _app("UnbanView2")
        admin = _user("unban_admin2@test.com", "users.ban")
        target = _user("unban_target2@test.com")

        resp = _authed_post(UserUnbanView, f"/auth/admin/users/{target.id}/unban/",
                            admin, app, user_id=str(target.id))

        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_unban_not_found_returns_404(self):
        app = _app("UnbanView3")
        admin = _user("unban_admin3@test.com", "users.ban")

        resp = _authed_post(UserUnbanView, "/auth/admin/users/999999999/unban/",
                            admin, app, user_id="999999999")

        assert resp.status_code == 404


# ===========================================================================
# UserLockView / UserUnlockView
# ===========================================================================

class TestUserLockUnlockView:

    @pytest.mark.django_db
    def test_lock_user_success(self):
        app = _app("LockView1")
        admin = _user("lock_admin1@test.com", "users.lock")
        target = _user("lock_target1@test.com")

        resp = _authed_post(UserLockView, f"/auth/admin/users/{target.id}/lock/",
                            admin, app,
                            data={"duration_minutes": 60},
                            user_id=str(target.id))

        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.is_locked is True

    @pytest.mark.django_db
    def test_lock_already_locked_returns_400(self):
        app = _app("LockView2")
        admin = _user("lock_admin2@test.com", "users.lock")
        target = _user("lock_target2@test.com")
        target.lock_account(30)

        resp = _authed_post(UserLockView, f"/auth/admin/users/{target.id}/lock/",
                            admin, app,
                            data={"duration_minutes": 30},
                            user_id=str(target.id))

        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_lock_not_found_returns_404(self):
        app = _app("LockView3")
        admin = _user("lock_admin3@test.com", "users.lock")

        resp = _authed_post(UserLockView, "/auth/admin/users/999999999/lock/",
                            admin, app,
                            data={"duration_minutes": 30},
                            user_id="999999999")

        assert resp.status_code == 404

    @pytest.mark.django_db
    def test_lock_without_permission_returns_403(self):
        app = _app("LockView4")
        user = _user("lock_noperm4@test.com")
        target = _user("lock_target4@test.com")

        resp = _authed_post(UserLockView, f"/auth/admin/users/{target.id}/lock/",
                            user, app,
                            data={"duration_minutes": 30},
                            user_id=str(target.id))

        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_unlock_user_success(self):
        app = _app("UnlockView1")
        admin = _user("unlock_admin1@test.com", "users.lock")
        target = _user("unlock_target1@test.com")
        target.lock_account(30)

        resp = _authed_post(UserUnlockView, f"/auth/admin/users/{target.id}/unlock/",
                            admin, app, user_id=str(target.id))

        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.is_locked is False

    @pytest.mark.django_db
    def test_unlock_not_locked_returns_400(self):
        app = _app("UnlockView2")
        admin = _user("unlock_admin2@test.com", "users.lock")
        target = _user("unlock_target2@test.com")

        resp = _authed_post(UserUnlockView, f"/auth/admin/users/{target.id}/unlock/",
                            admin, app, user_id=str(target.id))

        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_unlock_not_found_returns_404(self):
        app = _app("UnlockView3")
        admin = _user("unlock_admin3@test.com", "users.lock")

        resp = _authed_post(UserUnlockView, "/auth/admin/users/999999999/unlock/",
                            admin, app, user_id="999999999")

        assert resp.status_code == 404

# ---------------------------------------------------------------------------
# Extra Coverage Tests
# ---------------------------------------------------------------------------
from tenxyte.views.user_views import get_core_settings, AvatarUploadView  # noqa: E402

class TestExtraCoverage:
    def test_get_core_settings(self):
        # 52-54
        s = get_core_settings()
        assert s is not None

    @pytest.mark.django_db
    def test_patch_profile_phone_number_only(self):
        # 261-264
        app = _app("Extra1")
        user = _user("extra1@test.com")
        user.phone_number = "111"
        user.save()
        resp = _authed_patch(MeView, "/auth/me/", user, app, data={"phone_number": "222"})
        assert resp.status_code == 200

    @pytest.mark.django_db
    def test_patch_profile_phone_country_code_only(self):
        # 268
        app = _app("Extra2")
        user = _user("extra2@test.com")
        user.phone_country_code = "33"
        user.save()
        resp = _authed_patch(MeView, "/auth/me/", user, app, data={"phone_country_code": "44"})
        assert resp.status_code == 200

    @pytest.mark.django_db
    def test_patch_profile_user_not_found_core(self):
        # 275
        app = _app("Extra3")
        user = _user("extra3@test.com")
        token = _jwt_token(user, app)
        factory = APIRequestFactory()
        req = factory.patch("/auth/me/", data={"first_name": "x"}, format="json", HTTP_AUTHORIZATION=f"Bearer {token}")
        req.application = app
        req.user = user
        with patch("tenxyte.adapters.django.repositories.DjangoUserRepository.get_by_id", return_value=None):
            resp = MeView.as_view()(req)
            assert resp.status_code == 404

    @pytest.mark.django_db
    def test_avatar_upload_missing_file(self):
        # 375-378
        app = _app("Av1")
        user = _user("av1@test.com")
        resp = _authed_post(AvatarUploadView, "/auth/me/avatar/", user, app, data={})
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_avatar_upload_invalid_type(self):
        # 383-388
        from django.core.files.uploadedfile import SimpleUploadedFile
        app = _app("Av2")
        user = _user("av2@test.com")
        file = SimpleUploadedFile("test.txt", b"file_content", content_type="text/plain")
        resp = _authed_post(AvatarUploadView, "/auth/me/avatar/", user, app, data={"avatar": file})
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_avatar_upload_too_large(self):
        # 391-396
        from django.core.files.uploadedfile import SimpleUploadedFile
        app = _app("Av3")
        user = _user("av3@test.com")
        # 5MB + 1 byte
        file = SimpleUploadedFile("test.jpg", b"0" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
        # We must use APIRequestFactory.post directly with format="multipart" because 
        # _authed_post defaults to format="json".
        token = _jwt_token(user, app)
        factory = APIRequestFactory()
        req = factory.post("/auth/me/avatar/", data={"avatar": file}, format="multipart", HTTP_AUTHORIZATION=f"Bearer {token}")
        req.application = app
        req.user = user
        resp = AvatarUploadView.as_view()(req)
        assert resp.status_code == 413

    @pytest.mark.django_db
    def test_avatar_upload_success(self):
        # 398-402
        from django.core.files.uploadedfile import SimpleUploadedFile
        app = _app("Av4")
        user = _user("av4@test.com")
        file = SimpleUploadedFile("test.jpg", b"fakeimg", content_type="image/jpeg")
        
        token = _jwt_token(user, app)
        factory = APIRequestFactory()
        req = factory.post("/auth/me/avatar/", data={"avatar": file}, format="multipart", HTTP_AUTHORIZATION=f"Bearer {token}")
        req.application = app
        req.user = user
        
        # mock core repo to avoid actually uploading to S3/Cloud storage or verify
        with patch("tenxyte.adapters.django.repositories.DjangoUserRepository.update", return_value=user):
             resp = AvatarUploadView.as_view()(req)
             assert resp.status_code == 200

    @pytest.mark.django_db
    def test_user_detail_get_core_deleted_but_django_exist(self):
        # 576, 591-592
        app = _app("Udt1")
        admin = _user("udt1_admin@test.com", "users.update")
        target = _user("udt1_target@test.com")
        
        token = _jwt_token(admin, app)
        factory = APIRequestFactory()
        req = factory.patch(f"/auth/admin/users/{target.id}/", data={"first_name": "x"}, format="json", HTTP_AUTHORIZATION=f"Bearer {token}")
        req.application = app
        req.user = admin
        
        with patch("tenxyte.adapters.django.repositories.DjangoUserRepository.get_by_id", return_value=None):
             resp = UserDetailView.as_view()(req, user_id=str(target.id))
             assert resp.status_code == 404
             
        # what if django user is deleted but core is not:
        orig_get = User.objects.get
        def mock_get(*args, **kwargs):
            if kwargs.get('id') == str(target.id) or kwargs.get('id') == target.id:
                raise User.DoesNotExist
            return orig_get(*args, **kwargs)

        with patch("tenxyte.models.User.objects.get", side_effect=mock_get):
             # _authed_patch will setup token auth correctly
             resp = _authed_patch(UserDetailView, f"/auth/admin/users/{target.id}/", admin, app, data={"first_name": "x"}, user_id=str(target.id))
             assert resp.status_code == 404

    @pytest.mark.django_db
    def test_delete_user_not_found_core(self):
        # 613-617
        app = _app("Udt2")
        admin = _user("udt2_admin@test.com", "users.delete")
        
        # User 999999999 doesn't exist. _authed_delete authenticates as admin.
        resp = _authed_delete(UserDetailView, "/auth/admin/users/999999999/", admin, app, user_id="999999999")
        assert resp.status_code == 404

    @pytest.mark.django_db
    def test_ban_user_not_found_django(self):
        # 708-709
        app = _app("Ban1")
        admin = _user("ban1_admin@test.com", "users.ban")
        
        target = _user("ban1_target@test.com")
        
        orig_get = User.objects.get
        def mock_get(*args, **kwargs):
            if kwargs.get('id') == str(target.id) or kwargs.get('id') == target.id:
                raise User.DoesNotExist
            return orig_get(*args, **kwargs)

        with patch("tenxyte.models.User.objects.get", side_effect=mock_get):
            resp = _authed_post(UserBanView, f"/auth/admin/users/{target.id}/ban/", admin, app, user_id=str(target.id))
            assert resp.status_code == 404

    @pytest.mark.django_db
    def test_unban_user_not_found_django(self):
        # 743-744
        app = _app("Uban1")
        admin = _user("uban1_admin@test.com", "users.ban")
        target = _user("uban1_target@test.com")
        
        orig_get = User.objects.get
        def mock_get(*args, **kwargs):
            if kwargs.get('id') == str(target.id) or kwargs.get('id') == target.id:
                raise User.DoesNotExist
            return orig_get(*args, **kwargs)

        with patch("tenxyte.models.User.objects.get", side_effect=mock_get):
            resp = _authed_post(UserUnbanView, f"/auth/admin/users/{target.id}/unban/", admin, app, user_id=str(target.id))
            assert resp.status_code == 404

    @pytest.mark.django_db
    def test_lock_user_not_found_django(self):
        # 839-840
        app = _app("Lock1")
        admin = _user("lock1_admin@test.com", "users.lock")
        target = _user("lock1_target@test.com")

        orig_get = User.objects.get
        def mock_get(*args, **kwargs):
            if kwargs.get('id') == str(target.id) or kwargs.get('id') == target.id:
                raise User.DoesNotExist
            return orig_get(*args, **kwargs)

        with patch("tenxyte.models.User.objects.get", side_effect=mock_get):
            resp = _authed_post(UserLockView, f"/auth/admin/users/{target.id}/lock/", admin, app, user_id=str(target.id))
            assert resp.status_code == 404

    @pytest.mark.django_db
    def test_unlock_user_not_found_django(self):
        # 881-882
        app = _app("Ulock1")
        admin = _user("ulock1_admin@test.com", "users.lock")
        target = _user("ulock1_target@test.com")

        orig_get = User.objects.get
        def mock_get(*args, **kwargs):
            if kwargs.get('id') == str(target.id) or kwargs.get('id') == target.id:
                raise User.DoesNotExist
            return orig_get(*args, **kwargs)

        with patch("tenxyte.models.User.objects.get", side_effect=mock_get):
            resp = _authed_post(UserUnlockView, f"/auth/admin/users/{target.id}/unlock/", admin, app, user_id=str(target.id))
            assert resp.status_code == 404

