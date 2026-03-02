============================================================================================= test session starts ==============================================================================================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0
django: version: 6.0.2, settings: tests.settings (from ini)
rootdir: C:\Users\bobop\Documents\own\tenxyte
configfile: pyproject.toml
plugins: anyio-4.12.1, cov-7.0.0, django-4.11.1
collected 1408 items

tests\integration\test_agent_workflow.py F                                                                                                                                                                [  0%]
tests\integration\test_default_org_creation.py .....                                                                                                                                                      [  0%]
tests\integration\test_hitl_workflow.py F                                                                                                                                                                 [  0%]
tests\integration\test_tenant_isolation.py .......                                                                                                                                                        [  0%]
tests\integration\test_views.py ..............................                                                                                                                                            [  3%]
tests\multidb\test_db_auth_flow.py ..............                                                                                                                                                         [  4%]
tests\multidb\test_db_models.py ....................................                                                                                                                                      [  6%]
tests\security\test_security.py .....................................                                                                                                                                     [  9%]
tests\test_dashboard.py ................                                                                                                                                                                  [ 10%]
tests\test_documentation_examples.py ...................                                                                                                                                                  [ 11%]
tests\test_filters.py .................                                                                                                                                                                   [ 12%]
tests\test_security_views.py .............                                                                                                                                                                [ 13%]
tests\test_user_admin.py ...........                                                                                                                                                                      [ 14%]
tests\unit\test_account_deletion.py ............................................                                                                                                                          [ 17%]
tests\unit\test_admin.py .............                                                                                                                                                                    [ 18%]
tests\unit\test_agent_budget.py ....                                                                                                                                                                      [ 19%]
tests\unit\test_agent_decorators.py ....                                                                                                                                                                  [ 19%]
tests\unit\test_agent_forensic_audit.py F                                                                                                                                                                 [ 19%]
tests\unit\test_agent_middleware.py ..F.F                                                                                                                                                                 [ 19%]
tests\unit\test_agent_service.py ..F.FF.......F.......                                                                                                                                                    [ 21%]
tests\unit\test_agent_tasks.py ...                                                                                                                                                                        [ 21%]
tests\unit\test_agent_views.py .....F..........                                                                                                                                                           [ 22%]
tests\unit\test_application_serializers.py .                                                                                                                                                              [ 22%]
tests\unit\test_application_views.py ........................                                                                                                                                             [ 24%]
tests\unit\test_auth_serializers.py ..                                                                                                                                                                    [ 24%]
tests\unit\test_auth_service_edge_cases.py ....................                                                                                                                                           [ 25%]
tests\unit\test_auth_service_extended.py F.F.....F.F.F..........................                                                                                                                          [ 28%]
tests\unit\test_auth_views.py ................F........                                                                                                                                                   [ 30%]
tests\unit\test_authentication.py ..........                                                                                                                                                              [ 31%]
tests\unit\test_breach_check.py .....                                                                                                                                                                     [ 31%]
tests\unit\test_dashboard_views.py .......................................                                                                                                                                [ 34%]
tests\unit\test_decorators.py ..........................                                                                                                                                                  [ 36%]
tests\unit\test_direct_permissions.py .............                                                                                                                                                       [ 37%]
tests\unit\test_email_service.py ....                                                                                                                                                                     [ 37%]
tests\unit\test_email_service_deletion.py .............                                                                                                                                                   [ 38%]
tests\unit\test_filters.py .......................................                                                                                                                                        [ 41%]
tests\unit\test_gdpr_admin_serializers.py .                                                                                                                                                               [ 41%]
tests\unit\test_gdpr_admin_views.py ................                                                                                                                                                      [ 42%]
tests\unit\test_hierarchical_permissions.py ...................                                                                                                                                           [ 43%]
tests\unit\test_jwt.py ........                                                                                                                                                                           [ 44%]
tests\unit\test_magic_link.py ................................                                                                                                                                            [ 46%]
tests\unit\test_management_commands.py ...                                                                                                                                                                [ 46%]
tests\unit\test_middleware.py .........                                                                                                                                                                   [ 47%]
tests\unit\test_models.py ..............................                                                                                                                                                  [ 49%]
tests\unit\test_models_base.py ......                                                                                                                                                                     [ 49%]
tests\unit\test_models_gdpr.py ........                                                                                                                                                                   [ 50%]
tests\unit\test_models_organization.py .........                                                                                                                                                          [ 51%]
tests\unit\test_organization_service.py ........................................................                                                                                                          [ 55%]
tests\unit\test_organization_views.py ....................................                                                                                                                                [ 57%]
tests\unit\test_otp.py .......................                                                                                                                                                            [ 59%]
tests\unit\test_otp_views.py ..............                                                                                                                                                               [ 60%]
tests\unit\test_rbac_serializers.py .........                                                                                                                                                             [ 60%]
tests\unit\test_rbac_views.py ...............................................................                                                                                                             [ 65%]
tests\unit\test_security_serializers.py ....                                                                                                                                                              [ 65%]
tests\unit\test_security_views.py ......................................                                                                                                                                  [ 68%]
tests\unit\test_social_auth.py ...................................                                                                                                                                        [ 70%]
tests\unit\test_tenxyte_cleanup.py ...                                                                                                                                                                    [ 71%]
tests\unit\test_twofa_views.py ..................                                                                                                                                                         [ 72%]
tests\unit\test_user_admin_serializers.py ..                                                                                                                                                              [ 72%]
tests\unit\test_user_views.py ................................                                                                                                                                            [ 74%]
tests\unit\test_webauthn.py ................................................                                                                                                                              [ 78%]
tests\test_filters.py ..                                                                                                                                                                                  [ 78%]
tests\unit\test_application_serializers.py ......                                                                                                                                                         [ 78%]
tests\unit\test_auth_serializers.py ..........                                                                                                                                                            [ 79%]
tests\unit\test_auth_service_edge_cases.py .                                                                                                                                                              [ 79%]
tests\unit\test_authentication.py .                                                                                                                                                                       [ 79%]
tests\unit\test_backends.py ..............                                                                                                                                                                [ 80%]
tests\unit\test_breach_check.py ..........                                                                                                                                                                [ 81%]
tests\unit\test_cors_middleware.py ..................                                                                                                                                                     [ 82%]
tests\unit\test_decorators.py ..                                                                                                                                                                          [ 82%]
tests\unit\test_device_info.py .......                                                                                                                                                                    [ 83%]
tests\unit\test_email_backends.py ..........                                                                                                                                                              [ 83%]
tests\unit\test_email_service_deletion.py ...                                                                                                                                                             [ 84%]
tests\unit\test_gdpr_admin_serializers.py ..                                                                                                                                                              [ 84%]
tests\unit\test_init.py ..                                                                                                                                                                                [ 84%]
tests\unit\test_middleware.py ............                                                                                                                                                                [ 85%]
tests\unit\test_otp_serializers.py ......                                                                                                                                                                 [ 85%]
tests\unit\test_password_serializers.py ..........                                                                                                                                                        [ 86%]
tests\unit\test_pii_redaction.py ...                                                                                                                                                                      [ 86%]
tests\unit\test_rbac_serializers.py ....                                                                                                                                                                  [ 86%]
tests\unit\test_schemas.py .....                                                                                                                                                                          [ 87%]
tests\unit\test_secure_mode.py FFF..FF.F..F.F.........................................................                                                                                                    [ 92%]
tests\unit\test_security_serializers.py ..                                                                                                                                                                [ 92%]
tests\unit\test_sms_backends.py ..........                                                                                                                                                                [ 93%]
tests\unit\test_social_auth.py ..........................                                                                                                                                                 [ 94%]
tests\unit\test_throttles.py .........................                                                                                                                                                    [ 96%]
tests\unit\test_totp.py ..................                                                                                                                                                                [ 98%]
tests\unit\test_twofa_serializers.py ......                                                                                                                                                               [ 98%]
tests\unit\test_user_admin_serializers.py .......                                                                                                                                                         [ 98%]
tests\unit\test_validators.py ...............                                                                                                                                                             [100%]

=================================================================================================== FAILURES ===================================================================================================
___________________________________________________________________________________________ test_full_agent_workflow ___________________________________________________________________________________________

authenticated_client = <rest_framework.test.APIClient object at 0x000002A254E50260>, user = <User: test@example.com>, application = <Application: Test App>, permission = <Permission: data.read>
settings = <pytest_django.fixtures.SettingsWrapper object at 0x000002A254E51400>

    @pytest.mark.django_db
    def test_full_agent_workflow(authenticated_client, user, application, permission, settings):
        settings.TENXYTE_AIRS_ENABLED = True
        settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = True

        user.direct_permissions.add(permission)

        # 1. Create Agent Token via REST API
        create_response = authenticated_client.post(reverse('authentication:agent_token_list_create'), {
            'permissions': ['data.read'],
            'expires_in': 3600,
            'application_id': application.id,
            'agent_id': 'integration-agent-v1'
        }, format='json')

        assert create_response.status_code == 201, create_response.content
        agent_data = create_response.json()
        assert 'token' in agent_data
        raw_agent_token = agent_data['token']
        token_id = agent_data['id']

        # 2. Simulate an Agent accessing a protected View
        agent_client = APIClient()
        agent_client.credentials(
            HTTP_AUTHORIZATION=f'AgentBearer {raw_agent_token}',
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )

        heartbeat_url = reverse('authentication:agent_token_heartbeat', kwargs={'pk': token_id})
        heartbeat_response = agent_client.post(heartbeat_url)
>       assert heartbeat_response.status_code == 200, heartbeat_response.content
E       AssertionError: b'{"error": "Unauthorized or token mismatch"}'
E       assert 403 == 200
E        +  where 403 = <JsonResponse status_code=403, "application/json">.status_code

tests\integration\test_agent_workflow.py:45: AssertionError
-------------------------------------------------------------------------------------------- Captured stdout setup ---------------------------------------------------------------------------------------------
Operations to perform:
  Synchronize unmigrated apps: drf_spectacular, messages, rest_framework
  Apply all migrations: admin, auth, contenttypes, sessions, tenxyte
Synchronizing apps without migrations:
  Creating tables...
    Running deferred SQL...
Running migrations:
  No migrations to apply.
  Your models in app(s): 'tenxyte' have changes that are not yet reflected in a migration, and so won't be applied.
  Run 'manage.py makemigrations' to make new migrations, and then re-run 'manage.py migrate' to apply them.
--------------------------------------------------------------------------------------------- Captured stderr call ---------------------------------------------------------------------------------------------
Forbidden: /api/v1/auth/ai/tokens/1/heartbeat/
---------------------------------------------------------------------------------------------- Captured log call -----------------------------------------------------------------------------------------------
WARNING  django.request:log.py:249 Forbidden: /api/v1/auth/ai/tokens/1/heartbeat/
______________________________________________________________________________________________ test_hitl_workflow ______________________________________________________________________________________________

authenticated_client = <rest_framework.test.APIClient object at 0x000002A253BD0440>, user = <User: test@example.com>, application = <Application: Test App>, permission = <Permission: critical.delete>
settings = <pytest_django.fixtures.SettingsWrapper object at 0x000002A254DF5B80>

    @pytest.mark.django_db
    def test_hitl_workflow(authenticated_client, user, application, permission, settings):
        settings.TENXYTE_AIRS_ENABLED = True
        settings.TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS = True

        user.direct_permissions.add(permission)

        from tenxyte.services.agent_service import AgentTokenService
        service = AgentTokenService()
        token = service.create(triggered_by=user, application=application, granted_permissions=[permission])

        # 1. Agent calls the critical endpoint
        from django.test import RequestFactory
        from tenxyte.middleware import AgentTokenMiddleware

        def get_response_mock(r):
            return dummy_critical_view(r)

        middleware = AgentTokenMiddleware(get_response_mock)

        request = RequestFactory().post('/api/test-critical-delete/', data=json.dumps({'target': 42}), content_type='application/json')
        request.META['HTTP_AUTHORIZATION'] = f'AgentBearer {token.token}'

        response = middleware(request)

        # 2. Should intercept and return 202
>       assert response.status_code == 202
E       assert 403 == 202
E        +  where 403 = <JsonResponse status_code=403, "application/json">.status_code

tests\integration\test_hitl_workflow.py:50: AssertionError
________________________________________________________________________________ test_agent_middleware_captures_prompt_trace_id ________________________________________________________________________________

agent_middleware = <tenxyte.middleware.AgentTokenMiddleware object at 0x000002A253C622A0>, settings = <pytest_django.fixtures.SettingsWrapper object at 0x000002A253C613D0>

    @pytest.mark.django_db
    def test_agent_middleware_captures_prompt_trace_id(agent_middleware, settings):
        settings.TENXYTE_AIRS_ENABLED = True
        settings.TENXYTE_AUDIT_LOGGING_ENABLED = True

        # Setup test token
        user = User.objects.create_user(email="forensic@test.com", password="password")
        app = Application.objects.create(name="TestApp")
        token = AgentToken.objects.create(
            token="test-trace-token-123",
            agent_id="test-agent",
            triggered_by=user,
            application=app,
            expires_at="2099-12-31T23:59:59Z"
        )

        factory = RequestFactory()
        request = factory.post(
            '/api/test-action/',
            data=json.dumps({'action': 'delete'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'AgentBearer {token.token}',
            HTTP_X_PROMPT_TRACE_ID='trace_abc123'
        )

        # Mocking check_circuit_breaker since this is just testing the middleware
        # Actually, the middleware uses AgentTokenService directly, so it will hit DB
        # The token is created, it should pass basic validation if not expired.

        # Process request
        response = agent_middleware(request)

>       assert response.status_code == 200
E       assert 403 == 200
E        +  where 403 = <JsonResponse status_code=403, "application/json">.status_code

tests\unit\test_agent_forensic_audit.py:53: AssertionError
__________________________________________________________________________________ TestAgentTokenMiddleware.test_valid_token ___________________________________________________________________________________

self = <tests.unit.test_agent_middleware.TestAgentTokenMiddleware object at 0x000002A253103710>, middleware = <tenxyte.middleware.AgentTokenMiddleware object at 0x000002A253B62000>
test_user = <User: agentmanager@example.com>, test_app = <Application: Test App>, permission = <Permission: docs.read>

    def test_valid_token(self, middleware, test_user, test_app, permission):
        test_user.direct_permissions.add(permission)
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permission])

        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'AgentBearer {token.token}')
        response = middleware(request)

>       assert response.status_code == 200
E       assert 403 == 200
E        +  where 403 = <JsonResponse status_code=403, "application/json">.status_code

tests\unit\test_agent_middleware.py:60: AssertionError
__________________________________________________________________________ TestAgentTokenMiddleware.test_suspended_by_circuit_breaker __________________________________________________________________________

self = <tests.unit.test_agent_middleware.TestAgentTokenMiddleware object at 0x000002A253110770>, middleware = <tenxyte.middleware.AgentTokenMiddleware object at 0x000002A253B614C0>
test_user = <User: agentmanager@example.com>, test_app = <Application: Test App>, permission = <Permission: docs.read>

    def test_suspended_by_circuit_breaker(self, middleware, test_user, test_app, permission):
        test_user.direct_permissions.add(permission)
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permission], circuit_breaker={'max_requests_total': 1})

        token.current_request_count = 2
        token.save()

        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f'AgentBearer {token.token}')
        response = middleware(request)

        assert response.status_code == 403
        import json
        data = json.loads(response.content)
>       assert data['code'] == 'AGENT_TOKEN_SUSPENDED'
E       AssertionError: assert 'AGENT_TOKEN_NOT_FOUND' == 'AGENT_TOKEN_SUSPENDED'
E
E         - AGENT_TOKEN_SUSPENDED
E         + AGENT_TOKEN_NOT_FOUND

tests\unit\test_agent_middleware.py:88: AssertionError
______________________________________________________________________________ TestAgentTokenService.test_validate_token_success _______________________________________________________________________________

self = <tests.unit.test_agent_service.TestAgentTokenService object at 0x000002A253100830>, test_user = <User: agentmanager@example.com>, test_app = <Application: Test App>
permissions = [<Permission: docs.read>, <Permission: docs.write>]

    def test_validate_token_success(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]])

        validated_token, error = service.validate(token.token)
>       assert error is None
E       AssertionError: assert 'NOT_FOUND' is None

tests\unit\test_agent_service.py:74: AssertionError
______________________________________________________________________________ TestAgentTokenService.test_validate_token_expired _______________________________________________________________________________

self = <tests.unit.test_agent_service.TestAgentTokenService object at 0x000002A2531126F0>, test_user = <User: agentmanager@example.com>, test_app = <Application: Test App>
permissions = [<Permission: docs.read>, <Permission: docs.write>]

    def test_validate_token_expired(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]], expires_in=-10)

        validated_token, error = service.validate(token.token)
>       assert error == "EXPIRED"
E       AssertionError: assert 'NOT_FOUND' == 'EXPIRED'
E
E         - EXPIRED
E         + NOT_FOUND

tests\unit\test_agent_service.py:90: AssertionError
_________________________________________________________________________ TestAgentTokenService.test_validate_token_missing_heartbeat __________________________________________________________________________

self = <tests.unit.test_agent_service.TestAgentTokenService object at 0x000002A253112C30>, test_user = <User: agentmanager@example.com>, test_app = <Application: Test App>
permissions = [<Permission: docs.read>, <Permission: docs.write>]

    def test_validate_token_missing_heartbeat(self, test_user, test_app, permissions):
        test_user.direct_permissions.add(permissions[0])
        service = AgentTokenService()
        token = service.create(triggered_by=test_user, application=test_app, granted_permissions=[permissions[0]], dead_mans_switch={"heartbeat_required_every": 60})

        # Simulate time passing (e.g. 100 seconds ago)
        token.last_heartbeat_at = timezone.now() - timedelta(seconds=100)
        token.save()

        validated_token, error = service.validate(token.token)
>       assert error == "HEARTBEAT_MISSING"
E       AssertionError: assert 'NOT_FOUND' == 'HEARTBEAT_MISSING'
E
E         - HEARTBEAT_MISSING
E         + NOT_FOUND

tests\unit\test_agent_service.py:104: AssertionError
______________________________________________________________________________ TestAgentTokenService.test_validate_inactive_token ______________________________________________________________________________

self = <tests.unit.test_agent_service.TestAgentTokenService object at 0x000002A253131640>, test_user = <User: agentmanager@example.com>, test_app = <Application: Test App>

    def test_validate_inactive_token(self, test_user, test_app):
        service = AgentTokenService()
        token = AgentToken.objects.create(
            token="inactive_token", agent_id="test", triggered_by=test_user,
            application=test_app, expires_at=timezone.now() + timedelta(days=1),
            status=AgentToken.Status.REVOKED
        )
        validated_token, error = service.validate(token.token)
>       assert error == "STATUS_REVOKED"
E       AssertionError: assert 'NOT_FOUND' == 'STATUS_REVOKED'
E
E         - STATUS_REVOKED
E         + NOT_FOUND

tests\unit\test_agent_service.py:214: AssertionError
__________________________________________________________________________________ TestAgentViews.test_heartbeat_agent_token ___________________________________________________________________________________

self = <tests.unit.test_agent_views.TestAgentViews object at 0x000002A25314DC70>, api_client = <rest_framework.test.APIClient object at 0x000002A253B22390>, user = <User: test@example.com>
application = <Application: Test App>, permission = <Permission: docs.read>

    def test_heartbeat_agent_token(self, api_client, user, application, permission):
        user.direct_permissions.add(permission)
        from tenxyte.services.agent_service import AgentTokenService
        service = AgentTokenService()
        token = service.create(triggered_by=user, application=application, granted_permissions=[permission])

        url = reverse('authentication:agent_token_heartbeat', kwargs={'pk': token.id})
        # The agent calls this, authenticating with AgentBearer (also add application secrets so the first HTTP middleware passes)
        api_client.credentials(
            HTTP_AUTHORIZATION=f'AgentBearer {token.token}',
            HTTP_X_ACCESS_KEY=application.access_key,
            HTTP_X_ACCESS_SECRET=application._plain_secret
        )
        response = api_client.post(url)
>       assert response.status_code == 200
E       assert 403 == 200
E        +  where 403 = <JsonResponse status_code=403, "application/json">.status_code

tests\unit\test_agent_views.py:109: AssertionError
--------------------------------------------------------------------------------------------- Captured stderr call ---------------------------------------------------------------------------------------------
Forbidden: /api/v1/auth/ai/tokens/1/heartbeat/
---------------------------------------------------------------------------------------------- Captured log call -----------------------------------------------------------------------------------------------
WARNING  django.request:log.py:249 Forbidden: /api/v1/auth/ai/tokens/1/heartbeat/
_________________________________________________________________________________ TestLogout.test_logout_revokes_refresh_token _________________________________________________________________________________

self = <tests.unit.test_auth_service_extended.TestLogout object at 0x000002A2531B0D40>

    @pytest.mark.django_db
    def test_logout_revokes_refresh_token(self):
        app = _app("LogoutApp1")
        user = _user("logout1@test.com")
        rt = _refresh_token(user, app)

        service = AuthService()
        result = service.logout(rt.token)

>       assert result is True
E       assert False is True

tests\unit\test_auth_service_extended.py:62: AssertionError
_________________________________________________________________________ TestLogout.test_logout_blacklists_access_token_when_provided _________________________________________________________________________

self = <tests.unit.test_auth_service_extended.TestLogout object at 0x000002A2531C6540>

    @pytest.mark.django_db
    def test_logout_blacklists_access_token_when_provided(self):
        app = _app("LogoutApp2")
        user = _user("logout2@test.com")
        rt = _refresh_token(user, app)

        service = AuthService()
        with patch.object(service.jwt_service, 'blacklist_token') as mock_bl:
            service.logout(rt.token, access_token="fake.access.token")

>       mock_bl.assert_called_once_with("fake.access.token", user, 'logout')

tests\unit\test_auth_service_extended.py:82:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <MagicMock name='blacklist_token' id='2896212400400'>, args = ('fake.access.token', <User: logout2@test.com>, 'logout'), kwargs = {}
msg = "Expected 'blacklist_token' to be called once. Called 0 times."

    def assert_called_once_with(self, /, *args, **kwargs):
        """assert that the mock was called exactly once and that that call was
        with the specified arguments."""
        if not self.call_count == 1:
            msg = ("Expected '%s' to be called once. Called %s times.%s"
                   % (self._mock_name or 'mock',
                      self.call_count,
                      self._calls_repr()))
>           raise AssertionError(msg)
E           AssertionError: Expected 'blacklist_token' to be called once. Called 0 times.

..\..\..\AppData\Local\Python\pythoncore-3.12-64\Lib\unittest\mock.py:960: AssertionError
_________________________________________________________________________ TestRefreshAccessToken.test_refresh_returns_new_access_token _________________________________________________________________________

self = <tests.unit.test_auth_service_extended.TestRefreshAccessToken object at 0x000002A2531E0380>

    @pytest.mark.django_db
    @override_settings(TENXYTE_REFRESH_TOKEN_ROTATION=False)
    def test_refresh_returns_new_access_token(self):
        app = _app("RefreshApp1")
        user = _user("refresh1@test.com")
        rt = _refresh_token(user, app)

        service = AuthService()
        success, data, error = service.refresh_access_token(rt.token, app)

>       assert success is True
E       assert False is True

tests\unit\test_auth_service_extended.py:170: AssertionError
_______________________________________________________________________ TestRefreshAccessToken.test_refresh_expired_token_returns_error ________________________________________________________________________

self = <tests.unit.test_auth_service_extended.TestRefreshAccessToken object at 0x000002A25317D640>

    @pytest.mark.django_db
    def test_refresh_expired_token_returns_error(self):
        app = _app("RefreshApp3")
        user = _user("refresh3@test.com")
        rt = _refresh_token(user, app, expired=True)

        service = AuthService()
        success, data, error = service.refresh_access_token(rt.token, app)

        assert success is False
>       assert 'expired' in error.lower() or 'revoked' in error.lower()
E       AssertionError: assert ('expired' in 'invalid refresh token' or 'revoked' in 'invalid refresh token')
E        +  where 'invalid refresh token' = <built-in method lower of str object at 0x000002A2528C5870>()
E        +    where <built-in method lower of str object at 0x000002A2528C5870> = 'Invalid refresh token'.lower
E        +  and   'invalid refresh token' = <built-in method lower of str object at 0x000002A2528C5870>()
E        +    where <built-in method lower of str object at 0x000002A2528C5870> = 'Invalid refresh token'.lower

tests\unit\test_auth_service_extended.py:194: AssertionError
_____________________________________________________________________ TestRefreshAccessToken.test_refresh_with_rotation_creates_new_token ______________________________________________________________________

self = <tests.unit.test_auth_service_extended.TestRefreshAccessToken object at 0x000002A2531C78F0>

    @pytest.mark.django_db
    @override_settings(TENXYTE_REFRESH_TOKEN_ROTATION=True)
    def test_refresh_with_rotation_creates_new_token(self):
        app = _app("RefreshApp5")
        user = _user("refresh5@test.com")
        rt = _refresh_token(user, app)
        old_token_str = rt.token

        service = AuthService()
        success, data, error = service.refresh_access_token(rt.token, app)

>       assert success is True
E       assert False is True

tests\unit\test_auth_service_extended.py:218: AssertionError
__________________________________________________________________________________ TestRefreshTokenView.test_refresh_success ___________________________________________________________________________________

self = <tests.unit.test_auth_views.TestRefreshTokenView object at 0x000002A25320A540>

    @pytest.mark.django_db
    def test_refresh_success(self):
        app = _app("RefreshView1")
        user = _user("refreshview1@test.com")
        rt = _refresh_token(user, app)

        resp = _post(RefreshTokenView, "/auth/refresh/", {
            "refresh_token": rt.token
        }, app)
>       assert resp.status_code == 200
E       assert 401 == 200
E        +  where 401 = <Response status_code=401, "text/html; charset=utf-8">.status_code

tests\unit\test_auth_views.py:301: AssertionError
______________________________________________________________________________ TestPresetDefinitions.test_all_three_modes_defined ______________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25360CB30>

    def test_all_three_modes_defined(self):
>       assert 'starter' in SECURE_MODE_PRESETS
E       AssertionError: assert 'starter' in {'development': {'ACCOUNT_LOCKOUT_ENABLED': True, 'AUDIT_LOGGING_ENABLED': False, 'BREACH_CHECK_ENABLED': False, 'BREA...LOCKOUT_ENABLED': True, 'AUDIT_LOGGING_ENABLED': True, 'BREACH_CHECK_ENABLED': True, 'BREACH_CHECK_REJECT': True, ...}}

tests\unit\test_secure_mode.py:55: AssertionError
________________________________________________________________________ TestPresetDefinitions.test_valid_secure_modes_matches_presets _________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25360CF80>

    def test_valid_secure_modes_matches_presets(self):
>       assert VALID_SECURE_MODES == set(SECURE_MODE_PRESETS.keys())
E       AssertionError: assert {'development...t', 'starter'} == {'development...um', 'robust'}
E
E         Extra items in the left set:
E         'starter'
E         Use -v to get more diff

tests\unit\test_secure_mode.py:60: AssertionError
_____________________________________________________________________________ TestPresetDefinitions.test_starter_has_required_keys _____________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25360D460>

    def test_starter_has_required_keys(self):
>       preset = SECURE_MODE_PRESETS['starter']
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'starter'

tests\unit\test_secure_mode.py:63: KeyError
______________________________________________________________________ TestPresetDefinitions.test_starter_jwt_lifetime_longer_than_robust ______________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25360CCB0>

    def test_starter_jwt_lifetime_longer_than_robust(self):
>       assert SECURE_MODE_PRESETS['starter']['JWT_ACCESS_TOKEN_LIFETIME'] > \
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
               SECURE_MODE_PRESETS['robust']['JWT_ACCESS_TOKEN_LIFETIME']
E       KeyError: 'starter'

tests\unit\test_secure_mode.py:91: KeyError
________________________________________________________________________ TestPresetDefinitions.test_robust_max_login_attempts_strictest ________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25360DDC0>

    def test_robust_max_login_attempts_strictest(self):
        assert SECURE_MODE_PRESETS['robust']['MAX_LOGIN_ATTEMPTS'] < \
               SECURE_MODE_PRESETS['medium']['MAX_LOGIN_ATTEMPTS'] < \
>              SECURE_MODE_PRESETS['starter']['MAX_LOGIN_ATTEMPTS']
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'starter'

tests\unit\test_secure_mode.py:97: KeyError
____________________________________________________________________________ TestPresetDefinitions.test_starter_cors_allow_all_true ____________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25360E780>

    def test_starter_cors_allow_all_true(self):
>       assert SECURE_MODE_PRESETS['starter']['CORS_ALLOW_ALL_ORIGINS'] is True
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'starter'

tests\unit\test_secure_mode.py:104: KeyError
_____________________________________________________________________________ TestPresetDefinitions.test_starter_webauthn_disabled _____________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25360F620>

    def test_starter_webauthn_disabled(self):
>       assert SECURE_MODE_PRESETS['starter']['WEBAUTHN_ENABLED'] is False
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'starter'

tests\unit\test_secure_mode.py:114: KeyError
___________________________________________________________________________ TestPresetDefinitions.test_starter_breach_check_disabled ___________________________________________________________________________

self = <tests.unit.test_secure_mode.TestPresetDefinitions object at 0x000002A25362C0B0>

    def test_starter_breach_check_disabled(self):
>       assert SECURE_MODE_PRESETS['starter']['BREACH_CHECK_ENABLED'] is False
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'starter'

tests\unit\test_secure_mode.py:120: KeyError
=============================================================================================== warnings summary ===============================================================================================
src\tenxyte\models\auth.py:203
  C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\models\auth.py:203: RuntimeWarning: django-cryptography not installed. totp_secret will be stored in plaintext. Install it: pip install django-cryptography
    warnings.warn(

tests/unit/test_secure_mode.py::TestNoPriorityMode::test_api_prefix_formatting
  C:\Users\bobop\Documents\own\tenxyte\src\tenxyte\conf.py:202: DeprecationWarning: TENXYTE_SHORTCUT_SECURE_MODE='starter' is deprecated. Use 'development' instead. Note: this preset is NOT suitable for production.
    prefix = self._get('API_PREFIX', f'/api/v{self.API_VERSION}')

tests/unit/test_secure_mode.py: 10 warnings
  C:\Users\bobop\Documents\own\tenxyte\tests\unit\test_secure_mode.py:37: DeprecationWarning: TENXYTE_SHORTCUT_SECURE_MODE='starter' is deprecated. Use 'development' instead. Note: this preset is NOT suitable for production.
    return getattr(s, name)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================================================================ tests coverage ================================================================================================
_______________________________________________________________________________ coverage: platform win32, python 3.12.10-final-0 _______________________________________________________________________________

Name                                                  Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------------
src\tenxyte\__init__.py                                   9      0   100%
src\tenxyte\admin.py                                    275      0   100%
src\tenxyte\apps.py                                      21      6    71%   39-52
src\tenxyte\authentication.py                            37      0   100%
src\tenxyte\backends\__init__.py                          0      0   100%
src\tenxyte\backends\email.py                            82      2    98%   120, 127
src\tenxyte\backends\sms.py                              73      0   100%
src\tenxyte\conf.py                                     337      9    97%   223-238, 907, 912, 917
src\tenxyte\decorators.py                               277      5    98%   662, 669-676
src\tenxyte\device_info.py                              200      0   100%
src\tenxyte\docs\__init__.py                              0      0   100%
src\tenxyte\docs\schemas.py                              56      0   100%
src\tenxyte\filters.py                                  123      0   100%
src\tenxyte\management\__init__.py                        0      0   100%
src\tenxyte\management\commands\__init__.py               0      0   100%
src\tenxyte\management\commands\tenxyte_cleanup.py       39      0   100%
src\tenxyte\middleware.py                               172     15    91%   280, 291-327, 362
src\tenxyte\models\__init__.py                           13      0   100%
src\tenxyte\models\agent.py                              70      3    96%   91, 112, 139
src\tenxyte\models\application.py                        52      3    94%   63-64, 68
src\tenxyte\models\auth.py                              279      1    99%   199
src\tenxyte\models\base.py                               57      0   100%
src\tenxyte\models\gdpr.py                               78      0   100%
src\tenxyte\models\magic_link.py                         43      0   100%
src\tenxyte\models\operational.py                        94      1    99%   73
src\tenxyte\models\organization.py                      179      0   100%
src\tenxyte\models\security.py                           58      5    91%   40, 160, 181, 186-187
src\tenxyte\models\social.py                             26      1    96%   63
src\tenxyte\models\tenant.py                             29      1    97%   30
src\tenxyte\models\webauthn.py                           47      1    98%   44
src\tenxyte\pagination.py                                16      1    94%   53
src\tenxyte\serializers\__init__.py                      10      0   100%
src\tenxyte\serializers\application_serializers.py       16      0   100%
src\tenxyte\serializers\auth_serializers.py              60      0   100%
src\tenxyte\serializers\gdpr_admin_serializers.py        14      0   100%
src\tenxyte\serializers\organization_serializers.py      82      4    95%   79, 94-95, 99
src\tenxyte\serializers\otp_serializers.py                5      0   100%
src\tenxyte\serializers\password_serializers.py          13      0   100%
src\tenxyte\serializers\rbac_serializers.py              79      0   100%
src\tenxyte\serializers\security_serializers.py          56      0   100%
src\tenxyte\serializers\twofa_serializers.py             16      0   100%
src\tenxyte\serializers\user_admin_serializers.py        39      0   100%
src\tenxyte\services\__init__.py                         10      0   100%
src\tenxyte\services\account_deletion_service.py         94      0   100%
src\tenxyte\services\agent_service.py                   178     20    89%   120-146, 227-231
src\tenxyte\services\auth_service.py                    174     19    89%   41, 239, 272, 483, 502-510, 565, 600-617
src\tenxyte\services\breach_check_service.py              9      0   100%
src\tenxyte\services\email_service.py                   113      0   100%
src\tenxyte\services\jwt_service.py                      66      6    91%   113, 122, 137, 142, 146, 153
src\tenxyte\services\magic_link_service.py               48      1    98%   111
src\tenxyte\services\organization_service.py            176      0   100%
src\tenxyte\services\otp_service.py                      74      1    99%   87
src\tenxyte\services\social_auth_service.py             175      6    97%   81, 93, 128, 420-422
src\tenxyte\services\stats_service.py                    95      1    99%   336
src\tenxyte\services\totp_service.py                    127      2    98%   151, 162
src\tenxyte\services\webauthn_service.py                107      1    99%   25
src\tenxyte\signals.py                                   44      3    93%   94, 124, 127
src\tenxyte\tasks\__init__.py                             0      0   100%
src\tenxyte\tasks\agent_tasks.py                         24      0   100%
src\tenxyte\tenant_context.py                             7      0   100%
src\tenxyte\throttles.py                                119     13    89%   285-300
src\tenxyte\urls.py                                      14      0   100%
src\tenxyte\validators.py                                34      0   100%
src\tenxyte\views\__init__.py                             9      0   100%
src\tenxyte\views\account_deletion_views.py              36      1    97%   515
src\tenxyte\views\agent_views.py                        135     25    81%   49-53, 82-83, 166-167, 245-266
src\tenxyte\views\application_views.py                   90      0   100%
src\tenxyte\views\auth_views.py                          59      0   100%
src\tenxyte\views\dashboard_views.py                     36      0   100%
src\tenxyte\views\gdpr_admin_views.py                    82      8    90%   178-179, 316, 339, 398-402
src\tenxyte\views\magic_link_views.py                    29      0   100%
src\tenxyte\views\organization_views.py                 141      0   100%
src\tenxyte\views\otp_views.py                           26      0   100%
src\tenxyte\views\password_views.py                      25      0   100%
src\tenxyte\views\rbac_views.py                         263      0   100%
src\tenxyte\views\security_views.py                     138      0   100%
src\tenxyte\views\social_auth_views.py                   73      0   100%
src\tenxyte\views\twofa_views.py                         46      0   100%
src\tenxyte\views\user_views.py                         151     15    90%   302-331, 415-416, 464, 484
src\tenxyte\views\webauthn_views.py                      20      0   100%
-----------------------------------------------------------------------------------
TOTAL                                                  6179    180    97%
Coverage HTML written to dir htmlcov
Required test coverage of 90% reached. Total coverage: 97.09%
=========================================================================================== short test summary info ============================================================================================
FAILED tests/integration/test_agent_workflow.py::test_full_agent_workflow - AssertionError: b'{"error": "Unauthorized or token mismatch"}'
FAILED tests/integration/test_hitl_workflow.py::test_hitl_workflow - assert 403 == 202
FAILED tests/unit/test_agent_forensic_audit.py::test_agent_middleware_captures_prompt_trace_id - assert 403 == 200
FAILED tests/unit/test_agent_middleware.py::TestAgentTokenMiddleware::test_valid_token - assert 403 == 200
FAILED tests/unit/test_agent_middleware.py::TestAgentTokenMiddleware::test_suspended_by_circuit_breaker - AssertionError: assert 'AGENT_TOKEN_NOT_FOUND' == 'AGENT_TOKEN_SUSPENDED'
FAILED tests/unit/test_agent_service.py::TestAgentTokenService::test_validate_token_success - AssertionError: assert 'NOT_FOUND' is None
FAILED tests/unit/test_agent_service.py::TestAgentTokenService::test_validate_token_expired - AssertionError: assert 'NOT_FOUND' == 'EXPIRED'
FAILED tests/unit/test_agent_service.py::TestAgentTokenService::test_validate_token_missing_heartbeat - AssertionError: assert 'NOT_FOUND' == 'HEARTBEAT_MISSING'
FAILED tests/unit/test_agent_service.py::TestAgentTokenService::test_validate_inactive_token - AssertionError: assert 'NOT_FOUND' == 'STATUS_REVOKED'
FAILED tests/unit/test_agent_views.py::TestAgentViews::test_heartbeat_agent_token - assert 403 == 200
FAILED tests/unit/test_auth_service_extended.py::TestLogout::test_logout_revokes_refresh_token - assert False is True
FAILED tests/unit/test_auth_service_extended.py::TestLogout::test_logout_blacklists_access_token_when_provided - AssertionError: Expected 'blacklist_token' to be called once. Called 0 times.
FAILED tests/unit/test_auth_service_extended.py::TestRefreshAccessToken::test_refresh_returns_new_access_token - assert False is True
FAILED tests/unit/test_auth_service_extended.py::TestRefreshAccessToken::test_refresh_expired_token_returns_error - AssertionError: assert ('expired' in 'invalid refresh token' or 'revoked' in 'invalid refresh token')
FAILED tests/unit/test_auth_service_extended.py::TestRefreshAccessToken::test_refresh_with_rotation_creates_new_token - assert False is True
FAILED tests/unit/test_auth_views.py::TestRefreshTokenView::test_refresh_success - assert 401 == 200
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_all_three_modes_defined - AssertionError: assert 'starter' in {'development': {'ACCOUNT_LOCKOUT_ENABLED': True, 'AUDIT_LOGGING_ENABLED': False, 'BREACH_CHECK_ENABLED': False, 'BREA...LOCKOUT_ENABLED': True, 'AUDIT_LOGGING_ENABLED'...
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_valid_secure_modes_matches_presets - AssertionError: assert {'development...t', 'starter'} == {'development...um', 'robust'}
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_starter_has_required_keys - KeyError: 'starter'
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_starter_jwt_lifetime_longer_than_robust - KeyError: 'starter'
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_robust_max_login_attempts_strictest - KeyError: 'starter'
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_starter_cors_allow_all_true - KeyError: 'starter'
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_starter_webauthn_disabled - KeyError: 'starter'
FAILED tests/unit/test_secure_mode.py::TestPresetDefinitions::test_starter_breach_check_disabled - KeyError: 'starter'
=========================================================================== 24 failed, 1384 passed, 12 warnings in 396.28s (0:06:36) ===========================================================================
PS C:\Users\bobop\Documents\own\tenxyte>