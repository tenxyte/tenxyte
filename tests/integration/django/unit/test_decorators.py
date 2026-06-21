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
from tenxyte.models import User

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

        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_jwt_service.return_value.decode_token.return_value = DecodedToken(
            user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        
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
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_jwt_service.return_value.decode_token.return_value = DecodedToken(
            user_id='9999', app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        
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
                from tenxyte.core.jwt_service import DecodedToken
                from datetime import datetime, timezone
                mock_jwt.return_value.decode_token.return_value = DecodedToken(
                    user_id=str(self.user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
                    iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
                )
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
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_jwt_service.return_value.decode_token.return_value = DecodedToken(
            user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        
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
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_jwt_service.return_value.decode_token.return_value = DecodedToken(
            user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        
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
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_jwt_service.return_value.decode_token.return_value = DecodedToken(
            user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        
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

from tenxyte.decorators import rate_limit, get_client_ip  # noqa: E402

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
                from tenxyte.core.jwt_service import DecodedToken
                from datetime import datetime, timezone
                jwt.return_value.decode_token.return_value = DecodedToken(
                    user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
                    iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
                )
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
                from tenxyte.core.jwt_service import DecodedToken
                from datetime import datetime, timezone
                jwt.return_value.decode_token.return_value = DecodedToken(
                    user_id='', app_id='', jti='', exp=datetime.now(timezone.utc),
                    iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=False, error='Invalid token'
                )
                assert require_jwt(lambda r: None)(req).status_code == 401
                
    def test_jwt_app_mismatch(self): # Line 89
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer test'}
        req.application = MagicMock()
        req.application.id = 'app1'
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as jwt:
                from tenxyte.core.jwt_service import DecodedToken
                from datetime import datetime, timezone
                jwt.return_value.decode_token.return_value = DecodedToken(
                    user_id='', app_id='app2', jti='jti123', exp=datetime.now(timezone.utc),
                    iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
                )
                assert require_jwt(lambda r: None)(req).status_code == 401
                
    def test_jwt_user_inactive(self): # Line 98
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer test'}
        req.application = None
        user = User.objects.create(email='inact@test.com', is_active=False)
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as jwt:
                from tenxyte.core.jwt_service import DecodedToken
                from datetime import datetime, timezone
                jwt.return_value.decode_token.return_value = DecodedToken(
                    user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
                    iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
                )
                assert require_jwt(lambda r: None)(req).status_code == 401

    @override_settings(TENXYTE_JWT_AUTH_ENABLED=True)
    @patch('tenxyte.decorators.JWTService')
    def test_require_verified_phone_success(self, mock_jwt_service): # Line 158
        user = User.objects.create(email='vphone@test.com')
        user.is_phone_verified = True
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_jwt_service.return_value.decode_token.return_value = DecodedToken(
            user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
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

    @override_settings(TENXYTE_TRUSTED_PROXIES=[], TENXYTE_NUM_PROXIES=2)
    def test_get_client_ip_rejects_forwarded_for_when_trusted_proxies_empty(self):
        # VULN-003 Mitigation
        req = MagicMock(META={'HTTP_X_FORWARDED_FOR': '1.2.3.4', 'REMOTE_ADDR': '127.0.0.1'}, method='GET')
        req.user = None
        with patch('logging.Logger.warning') as mock_warn:
            assert get_client_ip(req) == '127.0.0.1'
            mock_warn.assert_called()

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


from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st  # noqa: E402


@pytest.mark.django_db
class TestRequireJwtScopeEnforcement:
    """Tests for token scope extraction and enforcement in require_jwt (Task 3.2).

    Rules under test:
    - Full-scope tokens (no "scope" claim) are accepted everywhere (preservation).
    - Restricted tokens (non-empty "scope" claim) are only accepted on endpoints
      that explicitly allow that scope via allowed_scopes; otherwise 403
      INSUFFICIENT_SCOPE.
    - The token scope is exposed on request.jwt_scope.
    """

    def _make_request(self):
        req = MagicMock(META={}, method='GET')
        req.headers = {'Authorization': 'Bearer test'}
        req.application = None
        return req

    def _decoded(self, user, claims):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        return DecodedToken(
            user_id=str(user.id), app_id='app123', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims=claims, is_valid=True
        )

    def _run(self, claims, allowed_scopes=None):
        """Run a view protected by require_jwt with the given token claims."""
        import uuid
        user = User.objects.create(email=f'scope_{uuid.uuid4().hex}@test.com', is_active=True)
        req = self._make_request()
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=True):
            with patch('tenxyte.decorators.JWTService') as jwt:
                jwt.return_value.decode_token.return_value = self._decoded(user, claims)
                with patch('tenxyte.decorators.User.objects.get', return_value=user):
                    if allowed_scopes is None:
                        @require_jwt
                        def view(request):
                            return JsonResponse({"scope": request.jwt_scope})
                    else:
                        @require_jwt(allowed_scopes=allowed_scopes)
                        def view(request):
                            return JsonResponse({"scope": request.jwt_scope})
                    return view(req), req

    # --- Preservation: full-scope tokens (no scope claim) ---

    def test_full_scope_token_accepted_without_allowed_scopes(self):
        resp, req = self._run(claims={})
        assert resp.status_code == 200
        assert req.jwt_scope is None

    def test_full_scope_token_accepted_on_scoped_endpoint(self):
        # An endpoint that declares allowed_scopes still accepts full-scope tokens.
        resp, req = self._run(claims={}, allowed_scopes=["2fa_setup_only"])
        assert resp.status_code == 200
        assert req.jwt_scope is None

    # --- Restricted tokens ---

    def test_restricted_token_rejected_on_unscoped_endpoint(self):
        resp, req = self._run(claims={"scope": "2fa_setup_only"})
        assert resp.status_code == 403
        import json
        assert json.loads(resp.content)["code"] == "INSUFFICIENT_SCOPE"
        # Scope is still recorded on the request before rejection.
        assert req.jwt_scope == "2fa_setup_only"

    def test_restricted_token_accepted_on_matching_scoped_endpoint(self):
        resp, req = self._run(claims={"scope": "2fa_setup_only"}, allowed_scopes=["2fa_setup_only"])
        assert resp.status_code == 200
        assert req.jwt_scope == "2fa_setup_only"

    def test_restricted_token_rejected_when_scope_not_in_allowed(self):
        resp, req = self._run(claims={"scope": "other_scope"}, allowed_scopes=["2fa_setup_only"])
        assert resp.status_code == 403
        import json
        assert json.loads(resp.content)["code"] == "INSUFFICIENT_SCOPE"

    def test_jwt_scope_set_when_disabled(self):
        req = MagicMock(META={}, method='GET')
        req.user = "x"
        req.jwt_payload = "x"
        with override_settings(TENXYTE_JWT_AUTH_ENABLED=False):
            resp = require_jwt(lambda r: JsonResponse({"ok": "ok"}))(req)
        assert resp.status_code == 200
        assert req.jwt_scope is None

    # --- Property-based: scope enforcement consistency ---

    @hyp_settings(max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        token_scope=st.one_of(st.none(), st.sampled_from(["2fa_setup_only", "other", "admin_only"])),
        allowed=st.lists(st.sampled_from(["2fa_setup_only", "other", "admin_only"]), max_size=3, unique=True),
    )
    def test_scope_enforcement_property(self, token_scope, allowed):
        """Validates: Requirements 2.4

        For any token scope and any set of allowed scopes:
        - A token with no scope (full-scope) is always accepted.
        - A restricted token is accepted iff its scope is in allowed_scopes.
        Rejection always uses 403 INSUFFICIENT_SCOPE.
        """
        import json
        claims = {} if token_scope is None else {"scope": token_scope}
        allowed_scopes = allowed if allowed else None
        resp, req = self._run(claims=claims, allowed_scopes=allowed_scopes)

        if token_scope is None:
            assert resp.status_code == 200
            assert req.jwt_scope is None
        elif token_scope in (allowed or []):
            assert resp.status_code == 200
            assert req.jwt_scope == token_scope
        else:
            assert resp.status_code == 403
            assert json.loads(resp.content)["code"] == "INSUFFICIENT_SCOPE"
