import pytest
from unittest.mock import patch, MagicMock
from django.http import JsonResponse
from django.test import override_settings
from tenxyte.decorators import (
    _extract_request, require_jwt, require_verified_email, require_verified_phone,
    require_org_context, require_org_membership, require_org_role,
    require_org_permission, require_org_admin, require_org_owner,
    require_role, require_any_role, require_all_roles,
    require_permission, require_any_permission, require_all_permissions
)
from tenxyte.models import User, Application

def test_extract_request_fallback():
    # Line 31 fallback
    view_instance, req, args = _extract_request("not_a_request", "other_arg")
    assert view_instance is None
    assert req is None
    assert args == ("not_a_request", "other_arg")

def test_extract_request_class_based():
    # Lines 29, 37
    req = MagicMock(META={}, method='GET')
    view_instance, out_req, args = _extract_request("self_instance", req, "other")
    assert view_instance == "self_instance"
    assert out_req == req
    assert args == ("other",)

class DummyView:
    @require_jwt
    def my_view(self, request):
        return JsonResponse({"status": "ok"})

@pytest.mark.django_db
class TestDecoratorsRequireJWT:
    def test_require_jwt_invalid_request(self):
        # Line 57
        view = DummyView()
        response = view.my_view() # no request object passed!
        assert response.status_code == 400

    @override_settings(TENXYTE_JWT_AUTH_ENABLED=False)
    def test_require_jwt_disabled(self):
        # Lines 64-66
        req = MagicMock(META={}, method='GET')
        req.user = "something"
        req.jwt_payload = "something"
        response = require_jwt(lambda r: JsonResponse({"status": "ok"}))(req)
        assert response.status_code == 200
        assert req.user is None
        assert req.jwt_payload is None

    @override_settings(TENXYTE_JWT_AUTH_ENABLED=True, TENXYTE_ACCOUNT_LOCKOUT_ENABLED=True)
    @patch('tenxyte.decorators.JWTService')
    def test_require_jwt_account_locked(self, mock_jwt_service):
        # Line 104
        user = User.objects.create(email='locked@test.com')
        user.is_account_locked = MagicMock(return_value=True)

        mock_jwt_service.return_value.decode_token.return_value = {'user_id': user.id, 'app_id': 'app123'}
        
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer asdf'}
        req.application = MagicMock()
        req.application.id = 'app123'
        
        with patch('tenxyte.decorators.User.objects.get', return_value=user):
            response = require_jwt(lambda r: JsonResponse({"status": "ok"}))(req)
        
        assert response.status_code == 401

    @override_settings(TENXYTE_JWT_AUTH_ENABLED=True)
    @patch('tenxyte.decorators.JWTService')
    def test_require_jwt_user_does_not_exist(self, mock_jwt_service):
        # Line 112-113
        mock_jwt_service.return_value.decode_token.return_value = {'user_id': 9999, 'app_id': 'app123'}
        
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer asdf'}
        req.application = MagicMock()
        req.application.id = 'app123'
        
        with patch('tenxyte.decorators.User.objects.get', side_effect=User.DoesNotExist):
            response = require_jwt(lambda r: JsonResponse({"status": "ok"}))(req)
            
        assert response.status_code == 401

@pytest.mark.django_db
class TestRBACDecorators:
    def setup_method(self):
        self.user = User.objects.create(email='rbac@test.com')
        self.req = MagicMock(META={}, method='GET')
        self.req.headers = {'Authorization': 'Bearer asdf'}
        self.req.application = MagicMock()
        self.req.application.id = 'app123'
        
    def _run(self, decorator_factory, arg, hook_method, mock_return):
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as mock_jwt:
                mock_jwt.return_value.decode_token.return_value = {'user_id': self.user.id, 'app_id': 'app123'}
                with patch('tenxyte.decorators.User.objects.get', return_value=self.user):
                    with patch.object(self.user, hook_method, return_value=mock_return):
                        @decorator_factory(arg)
                        def view(request):
                            return JsonResponse({"status": "ok"})
                        return view(self.req)

    def test_rbac_roles(self):
        assert self._run(require_role, 'admin', 'has_role', False).status_code == 403
        assert self._run(require_role, 'admin', 'has_role', True).status_code == 200

        assert self._run(require_any_role, ['admin'], 'has_any_role', False).status_code == 403
        assert self._run(require_any_role, ['admin'], 'has_any_role', True).status_code == 200

        assert self._run(require_all_roles, ['admin'], 'has_all_roles', False).status_code == 403
        assert self._run(require_all_roles, ['admin'], 'has_all_roles', True).status_code == 200

    def test_rbac_permissions(self):
        assert self._run(require_permission, 'read', 'has_permission', False).status_code == 403
        assert self._run(require_permission, 'read', 'has_permission', True).status_code == 200

        assert self._run(require_any_permission, ['read'], 'has_any_permission', False).status_code == 403
        assert self._run(require_any_permission, ['read'], 'has_any_permission', True).status_code == 200

        assert self._run(require_all_permissions, ['read'], 'has_all_permissions', False).status_code == 403
        assert self._run(require_all_permissions, ['read'], 'has_all_permissions', True).status_code == 200


@pytest.mark.django_db
class TestVerifiedDecorators:
    @override_settings(TENXYTE_JWT_AUTH_ENABLED=True)
    @patch('tenxyte.decorators.JWTService')
    def test_require_verified_email(self, mock_jwt_service):
        user = User.objects.create(email='unverified@test.com')
        mock_jwt_service.return_value.decode_token.return_value = {'user_id': user.id, 'app_id': 'app123'}
        
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer asdf'}
        req.application = MagicMock()
        req.application.id = 'app123'
        
        @require_verified_email
        def view(request):
            return JsonResponse({"status": "ok"})
            
        with patch('tenxyte.decorators.User.objects.get', return_value=user):
            response = view(req)
            assert response.status_code == 403

    @override_settings(TENXYTE_JWT_AUTH_ENABLED=True)
    @patch('tenxyte.decorators.JWTService')
    def test_require_verified_email_success(self, mock_jwt_service):
        user = User.objects.create(email='verified@test.com')
        user.is_email_verified = True
        mock_jwt_service.return_value.decode_token.return_value = {'user_id': user.id, 'app_id': 'app123'}
        
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer asdf'}
        req.application = MagicMock()
        req.application.id = 'app123'
        
        @require_verified_email
        def view(request):
            return JsonResponse({"status": "ok"})
            
        with patch('tenxyte.decorators.User.objects.get', return_value=user):
            response = view(req)
            assert response.status_code == 200

    @override_settings(TENXYTE_JWT_AUTH_ENABLED=True)
    @patch('tenxyte.decorators.JWTService')
    def test_require_verified_phone(self, mock_jwt_service):
        user = User.objects.create(email='unvphone@test.com')
        user.is_phone_verified = False
        mock_jwt_service.return_value.decode_token.return_value = {'user_id': user.id, 'app_id': 'app123'}
        
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer asdf'}
        req.application = MagicMock()
        req.application.id = 'app123'
        
        @require_verified_phone
        def view(request):
            return JsonResponse({"status": "ok"})
            
        with patch('tenxyte.decorators.User.objects.get', return_value=user):
            response = view(req)
            assert response.status_code == 403

@pytest.mark.django_db
class TestOrgDecorators:
    def get_req(self, org=None, user=None, authenticated=True):
        req = MagicMock()
        if org:
            org.slug = 'test-org'
        req.organization = org
        if user:
            req.user = user
            req.user.is_authenticated = authenticated
        else:
            req.user = MagicMock()
            req.user.is_authenticated = authenticated
        return req

    def test_org_context_disabled_and_no_context(self):
        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=False):
            response = require_org_context(lambda r: JsonResponse({"status": "ok"}))(self.get_req())
            assert response.status_code == 400

        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            response = require_org_context(lambda r: JsonResponse({"status": "ok"}))(self.get_req(org=None))
            assert response.status_code == 400
            
            response_ok = require_org_context(lambda r: JsonResponse({"status": "ok"}))(self.get_req(org=MagicMock()))
            assert response_ok.status_code == 200

    def test_org_membership_disabled_and_auth(self):
        req_no_org = self.get_req(org=None)
        req_unauth = self.get_req(org=MagicMock(), authenticated=False)
        req_not_member = self.get_req(org=MagicMock())
        req_not_member.user.is_org_member.return_value = False

        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=False):
            assert require_org_membership(lambda r: None)(req_no_org).status_code == 400

        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            assert require_org_membership(lambda r: None)(req_no_org).status_code == 400
            assert require_org_membership(lambda r: None)(req_unauth).status_code == 401
            
            response = require_org_membership(lambda r: JsonResponse({"status": "ok"}))(req_not_member)
            assert response.status_code == 403

    def test_org_role_disabled_context_auth_perm(self):
        req_no_org = self.get_req(org=None)
        req_unauth = self.get_req(org=MagicMock(), authenticated=False)
        req_no_role = self.get_req(org=MagicMock())
        req_no_role.user.has_org_role.return_value = False

        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=False):
            assert require_org_role('admin')(lambda r: None)(req_no_org).status_code == 400 

        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            assert require_org_role('admin')(lambda r: None)(req_no_org).status_code == 400
            assert require_org_role('admin')(lambda r: None)(req_unauth).status_code == 401
            
            req_role_ok = self.get_req(org=MagicMock())
            req_role_ok.user.has_org_role.return_value = True
            req_role_ok.user.get_org_membership.return_value = "membership"
            del req_role_ok.org_membership
            
            resp = require_org_role('admin')(lambda r: JsonResponse({"status": "ok"}))(req_role_ok)
            assert resp.status_code == 200
            assert req_role_ok.org_membership == "membership"

    def test_org_permission_disabled_and_checks(self):
        req_no_org = self.get_req(org=None)
        req_unauth = self.get_req(org=MagicMock(), authenticated=False)
        req_perm_ok = self.get_req(org=MagicMock())
        req_perm_ok.user.has_org_permission.return_value = True
        del req_perm_ok.org_membership
        
        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=False):
            assert require_org_permission('do.x')(lambda r: None)(req_no_org).status_code == 400

        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            assert require_org_permission('do.x')(lambda r: None)(req_no_org).status_code == 400
            assert require_org_permission('do.x')(lambda r: None)(req_unauth).status_code == 401
            
            resp = require_org_permission('do.x')(lambda r: JsonResponse({"status": "ok"}))(req_perm_ok)
            assert resp.status_code == 200
            assert hasattr(req_perm_ok, 'org_membership')

    def test_org_admin_checks(self):
        req_no_org = self.get_req(org=None)
        req_unauth = self.get_req(org=MagicMock(), authenticated=False)
        req_no_admin = self.get_req(org=MagicMock())
        req_no_admin.user.has_org_role.side_effect = [False, False] # admin, owner
        
        req_admin_ok = self.get_req(org=MagicMock())
        req_admin_ok.user.has_org_role.side_effect = [True, False] # admin, owner
        del req_admin_ok.org_membership
        
        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=False):
            assert require_org_admin(lambda r: None)(req_no_org).status_code == 400

        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            assert require_org_admin(lambda r: None)(req_no_org).status_code == 400
            assert require_org_admin(lambda r: None)(req_unauth).status_code == 401
            assert require_org_admin(lambda r: None)(req_no_admin).status_code == 403
            
            resp = require_org_admin(lambda r: JsonResponse({"status": "ok"}))(req_admin_ok)
            assert resp.status_code == 200
            assert hasattr(req_admin_ok, 'org_membership')
            
    def test_org_owner_checks(self):
        req_unauth = self.get_req(org=MagicMock(), authenticated=False)
        req_no_owner = self.get_req(org=MagicMock())
        req_no_owner.user.has_org_role.return_value = False
        
        req_owner_ok = self.get_req(org=MagicMock())
        req_owner_ok.user.has_org_role.return_value = True
        del req_owner_ok.org_membership
        
        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            assert require_org_owner(lambda r: JsonResponse({"status": "ok"}))(req_unauth).status_code == 401
            assert require_org_owner(lambda r: JsonResponse({"status": "ok"}))(req_no_owner).status_code == 403
            resp = require_org_owner(lambda r: JsonResponse({"status": "ok"}))(req_owner_ok)
            assert resp.status_code == 200
            assert hasattr(req_owner_ok, 'org_membership')

from tenxyte.decorators import rate_limit, get_client_ip

class CBVTest:
    @require_jwt
    def my_method(self, request):
        return JsonResponse({'status': 'ok'})

@pytest.mark.django_db
class TestRemainingCoverage:
    def test_cbv_call_view(self): # Line 37
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer test'}
        req.application = None
        user = User.objects.create(email='cbv@test.com', is_active=True)
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as jwt:
                jwt.return_value.decode_token.return_value = {'user_id': user.id}
                view = CBVTest()
                assert view.my_method(req).status_code == 200

    def test_jwt_no_auth_header(self): # Line 71
        req = MagicMock(META={}, method='GET')
        req.headers = {}
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            assert require_jwt(lambda r: None)(req).status_code == 401
            
    def test_jwt_invalid_token(self): # Line 81
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer bad'}
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as jwt:
                jwt.return_value.decode_token.return_value = None
                assert require_jwt(lambda r: None)(req).status_code == 401
                
    def test_jwt_app_mismatch(self): # Line 89
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer test'}
        req.application = MagicMock()
        req.application.id = 'app1'
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as jwt:
                jwt.return_value.decode_token.return_value = {'app_id': 'app2'}
                assert require_jwt(lambda r: None)(req).status_code == 401
                
    def test_jwt_user_inactive(self): # Line 98
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer test'}
        req.application = None
        user = User.objects.create(email='inact@test.com', is_active=False)
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as jwt:
                jwt.return_value.decode_token.return_value = {'user_id': user.id}
                assert require_jwt(lambda r: None)(req).status_code == 401

    @override_settings(TENXYTE_JWT_AUTH_ENABLED=True)
    @patch('tenxyte.decorators.JWTService')
    def test_require_verified_phone_success(self, mock_jwt_service): # Line 158
        user = User.objects.create(email='vphone@test.com')
        user.is_phone_verified = True
        mock_jwt_service.return_value.decode_token.return_value = {'user_id': user.id}
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer test'}
        req.application = None
        with patch('tenxyte.decorators.User.objects.get', return_value=user):
            assert require_verified_phone(lambda r: JsonResponse({"ok": "ok"}))(req).status_code == 200

    def test_rate_limit_disabled(self): # 174-176
        req = MagicMock(META={}, method='GET')
        with override_settings(TENXYTE_RATE_LIMITING_ENABLED=False):
            assert rate_limit(1, 10)(lambda r: JsonResponse({"st": "ok"}))(req).status_code == 200
            
    def test_rate_limit_user(self): # 184-205
        req = MagicMock(META={}, method='GET')
        req.user = MagicMock()
        req.user.id = 1
        with override_settings(TENXYTE_RATE_LIMITING_ENABLED=True):
            with patch('django.core.cache.cache.get', return_value=1):
                assert rate_limit(1, 10)(lambda r: None)(req).status_code == 429
            with patch('django.core.cache.cache.get', return_value=0):
                with patch('django.core.cache.cache.set') as set_mock:
                    assert rate_limit(1, 10)(lambda r: JsonResponse({"st":"ok"}))(req).status_code == 200
                    set_mock.assert_called()

    @override_settings(TENXYTE_TRUSTED_PROXIES=["127.0.0.1"], TENXYTE_NUM_PROXIES=2)
    def test_rate_limit_ip_and_get_client_ip(self): # 187, 212-217
        req = MagicMock(META={'HTTP_X_FORWARDED_FOR': '1.2.3.4, 8.8.8.8', 'REMOTE_ADDR': '127.0.0.1'}, method='GET')
        req.user = None
        assert get_client_ip(req) == '1.2.3.4'
        req2 = MagicMock(META={'REMOTE_ADDR': '2.2.2.2'}, method='GET')
        req2.user = None
        assert get_client_ip(req2) == '2.2.2.2'
        
        with override_settings(TENXYTE_RATE_LIMITING_ENABLED=True):
            with patch('django.core.cache.cache.get', return_value=0):
                assert rate_limit(1, 10)(lambda r: JsonResponse({"st":"ok"}))(req).status_code == 200

    def test_org_membership_success(self): # 438-440
        req = MagicMock()
        req.organization.slug = 'org'
        req.user.is_authenticated = True
        req.user.is_org_member.return_value = True
        req.user.get_org_membership.return_value = "mem"
        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            assert require_org_membership(lambda r: JsonResponse({"ok": "ok"}))(req).status_code == 200
            assert req.org_membership == "mem"
            
    def test_org_permission_failure(self): # 543
        req = MagicMock()
        req.organization.slug = 'org'
        req.user.is_authenticated = True
        req.user.has_org_permission.return_value = False
        with override_settings(TENXYTE_ORGANIZATIONS_ENABLED=True):
            assert require_org_permission('do.x')(lambda r: None)(req).status_code == 403
