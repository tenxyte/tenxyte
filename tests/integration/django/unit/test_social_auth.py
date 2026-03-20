"""
Tests for Social Login Multi-Provider.

Coverage targets:
- models/social.py (SocialConnection)
- services/social_auth_service.py (providers + SocialAuthService)
- views/social_auth_views.py (SocialAuthView)
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from django.test import override_settings

from tenxyte.models import User, Application
from tenxyte.models.social import SocialConnection
from tenxyte.services.social_auth_service import (
    SocialAuthService, get_provider,
    GoogleOAuthProvider, GitHubOAuthProvider,
    MicrosoftOAuthProvider, FacebookOAuthProvider,
)
from tenxyte.views.social_auth_views import SocialAuthView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="SocialApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email="social@example.com"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


def _post(provider, data, app=None):
    factory = APIRequestFactory()
    with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
        req = factory.post(f'/social/{provider}/', data, format='json')
        if app:
            req.application = app
        return SocialAuthView.as_view()(req, provider=provider)


GITHUB_USER_DATA = {
    'provider_user_id': 'gh_123',
    'email': 'github@example.com',
    'email_verified': True,
    'first_name': 'John',
    'last_name': 'Doe',
    'avatar_url': 'https://avatars.github.com/u/123',
}

GOOGLE_USER_DATA = {
    'provider_user_id': 'google_456',
    'email': 'google@example.com',
    'email_verified': True,
    'first_name': 'Jane',
    'last_name': 'Smith',
    'avatar_url': 'https://lh3.googleusercontent.com/photo',
}

MICROSOFT_USER_DATA = {
    'provider_user_id': 'ms_789',
    'email': 'microsoft@example.com',
    'email_verified': True,
    'first_name': 'Bob',
    'last_name': 'Johnson',
    'avatar_url': '',
}

FACEBOOK_USER_DATA = {
    'provider_user_id': 'fb_101',
    'email': 'facebook@example.com',
    'email_verified': True,
    'first_name': 'Alice',
    'last_name': 'Brown',
    'avatar_url': 'https://graph.facebook.com/photo',
}


# ===========================================================================
# SocialConnection Model Tests
# ===========================================================================

@pytest.mark.django_db
class TestSocialConnectionModel:

    def test_get_or_create_creates_new(self):
        user = _user("sc_create@example.com")
        conn, created = SocialConnection.get_or_create_for_user(
            user=user,
            provider='github',
            provider_user_id='gh_999',
            email='sc_create@example.com',
        )
        assert created is True
        assert conn.user == user
        assert conn.provider == 'github'
        assert conn.provider_user_id == 'gh_999'

    def test_get_or_create_updates_existing(self):
        user = _user("sc_update@example.com")
        conn1, _ = SocialConnection.get_or_create_for_user(
            user=user, provider='github', provider_user_id='gh_update',
            first_name='Old',
        )
        conn2, created = SocialConnection.get_or_create_for_user(
            user=user, provider='github', provider_user_id='gh_update',
            first_name='New',
        )
        assert created is False
        assert conn2.first_name == 'New'
        assert conn1.pk == conn2.pk

    def test_unique_together_provider_and_id(self):
        user1 = _user("sc_unique1@example.com")
        user2 = _user("sc_unique2@example.com")
        SocialConnection.get_or_create_for_user(
            user=user1, provider='github', provider_user_id='gh_shared',
        )
        # Same provider_user_id → should update user1's connection, not create new
        conn, created = SocialConnection.get_or_create_for_user(
            user=user2, provider='github', provider_user_id='gh_shared',
        )
        assert created is False

    def test_different_providers_same_user(self):
        user = _user("sc_multi@example.com")
        SocialConnection.get_or_create_for_user(
            user=user, provider='github', provider_user_id='gh_multi',
        )
        SocialConnection.get_or_create_for_user(
            user=user, provider='google', provider_user_id='google_multi',
        )
        assert SocialConnection.objects.filter(user=user).count() == 2


# ===========================================================================
# Provider Registry Tests
# ===========================================================================

@pytest.mark.django_db
class TestProviderRegistry:

    @override_settings(TENXYTE_SOCIAL_PROVIDERS=['google', 'github', 'microsoft', 'facebook'])
    def test_get_provider_returns_correct_instance(self):
        assert isinstance(get_provider('google'), GoogleOAuthProvider)
        assert isinstance(get_provider('github'), GitHubOAuthProvider)
        assert isinstance(get_provider('microsoft'), MicrosoftOAuthProvider)
        assert isinstance(get_provider('facebook'), FacebookOAuthProvider)

    @override_settings(TENXYTE_SOCIAL_PROVIDERS=['google'])
    def test_get_provider_returns_none_for_disabled(self):
        assert get_provider('github') is None
        assert get_provider('microsoft') is None

    def test_get_provider_returns_none_for_unknown(self):
        assert get_provider('twitter') is None
        assert get_provider('') is None


# ===========================================================================
# Provider get_user_info Tests (mocked HTTP)
# ===========================================================================

class TestGoogleOAuthProvider:

    def test_get_user_info_success(self):
        provider = GoogleOAuthProvider()
        mock_response = {
            'sub': 'google_123',
            'email': 'test@gmail.com',
            'email_verified': True,
            'given_name': 'John',
            'family_name': 'Doe',
            'picture': 'https://photo.url',
        }
        with patch.object(provider, '_get', return_value=mock_response):
            result = provider.get_user_info('fake_token')
        assert result['provider_user_id'] == 'google_123'
        assert result['email'] == 'test@gmail.com'
        assert result['first_name'] == 'John'

    def test_get_user_info_failure(self):
        provider = GoogleOAuthProvider()
        with patch.object(provider, '_get', return_value=None):
            result = provider.get_user_info('bad_token')
        assert result is None

    def test_verify_id_token_failure(self):
        provider = GoogleOAuthProvider()
        with patch('google.oauth2.id_token.verify_oauth2_token', side_effect=Exception("invalid")):
            result = provider.verify_id_token('bad_id_token')
        assert result is None

    def test_exchange_code_success(self):
        provider = GoogleOAuthProvider()
        with patch.object(provider, '_post', return_value={'access_token': 'tok123'}):
            result = provider.exchange_code('code123', 'https://app.com/callback')
        assert result['access_token'] == 'tok123'

    def test_provider_name(self):
        assert GoogleOAuthProvider().provider_name == 'google'

    def test_verify_id_token_bad_issuer(self):
        provider = GoogleOAuthProvider()
        mock_idinfo = {'iss': 'bad_issuer.com', 'sub': '123'}
        with patch('google.oauth2.id_token.verify_oauth2_token', return_value=mock_idinfo):
            result = provider.verify_id_token('token')
        assert result is None

    def test_abstract_post_non_200(self):
        provider = GoogleOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        with patch('requests.post', return_value=mock_resp):
            # Calls abstract _post
            res = provider.exchange_code('fake', 'uri')
            assert res is None

    def test_abstract_post_exception(self):
        provider = GoogleOAuthProvider()
        with patch('requests.post', side_effect=Exception("Post error")):
            res = provider.exchange_code('fake', 'uri')
            assert res is None


class TestGitHubOAuthProvider:

    def test_get_user_info_with_email_in_profile(self):
        provider = GitHubOAuthProvider()
        mock_profile = {
            'id': 12345,
            'email': 'dev@github.com',
            'name': 'John Dev',
            'avatar_url': 'https://avatars.github.com/u/12345',
        }
        with patch.object(provider, '_get', return_value=mock_profile):
            result = provider.get_user_info('fake_token')
        assert result['provider_user_id'] == '12345'
        assert result['email'] == 'dev@github.com'
        assert result['first_name'] == 'John'
        assert result['last_name'] == 'Dev'

    def test_get_user_info_fetches_email_from_emails_endpoint(self):
        provider = GitHubOAuthProvider()
        mock_profile = {'id': 99, 'email': None, 'name': 'NoEmail User', 'avatar_url': ''}
        mock_emails = [
            {'email': 'primary@github.com', 'primary': True, 'verified': True},
            {'email': 'other@github.com', 'primary': False, 'verified': True},
        ]
        call_count = [0]

        def mock_get(url, token):
            call_count[0] += 1
            if 'emails' in url:
                return mock_emails
            return mock_profile

        with patch.object(provider, '_get', side_effect=mock_get):
            result = provider.get_user_info('fake_token')
        assert result['email'] == 'primary@github.com'
        assert result['email_verified'] is True

    def test_get_user_info_failure(self):
        provider = GitHubOAuthProvider()
        with patch.object(provider, '_get', return_value=None):
            result = provider.get_user_info('bad_token')
        assert result is None

    def test_exchange_code(self):
        provider = GitHubOAuthProvider()
        with patch.object(provider, '_post', return_value={'access_token': 'gh_tok'}):
            result = provider.exchange_code('code', 'https://app.com/callback')
        assert result['access_token'] == 'gh_tok'

    def test_provider_name(self):
        assert GitHubOAuthProvider().provider_name == 'github'

    def test_abstract_get_non_200(self):
        provider = GitHubOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        with patch('requests.get', return_value=mock_resp):
            # This calls abstract _get
            res = provider.get_user_info('fake')
            assert res is None

    def test_abstract_get_exception(self):
        provider = GitHubOAuthProvider()
        with patch('requests.get', side_effect=Exception("Get error")):
            res = provider.get_user_info('fake')
            assert res is None

class TestMicrosoftOAuthProvider:

    def test_get_user_info_success(self):
        provider = MicrosoftOAuthProvider()
        mock_data = {
            'id': 'ms_id_123',
            'mail': 'user@company.com',
            'givenName': 'Bob',
            'surname': 'Smith',
        }
        with patch.object(provider, '_get', return_value=mock_data):
            result = provider.get_user_info('fake_token')
        assert result['provider_user_id'] == 'ms_id_123'
        assert result['email'] == 'user@company.com'
        assert result['first_name'] == 'Bob'

    def test_get_user_info_uses_userPrincipalName_fallback(self):
        provider = MicrosoftOAuthProvider()
        mock_data = {
            'id': 'ms_id_456',
            'mail': None,
            'userPrincipalName': 'user@tenant.onmicrosoft.com',
            'givenName': 'Alice',
            'surname': 'Jones',
        }
        with patch.object(provider, '_get', return_value=mock_data):
            result = provider.get_user_info('fake_token')
        assert result['email'] == 'user@tenant.onmicrosoft.com'

    def test_get_user_info_failure(self):
        provider = MicrosoftOAuthProvider()
        with patch.object(provider, '_get', return_value=None):
            result = provider.get_user_info('bad_token')
        assert result is None

    def test_provider_name(self):
        assert MicrosoftOAuthProvider().provider_name == 'microsoft'

    def test_exchange_code(self):
        provider = MicrosoftOAuthProvider()
        with patch.object(provider, '_post', return_value={'access_token': 'ms_tok'}):
            result = provider.exchange_code('code', 'https://app.com/callback')
        assert result['access_token'] == 'ms_tok'


class TestFacebookOAuthProvider:

    def test_get_user_info_success(self):
        provider = FacebookOAuthProvider()
        mock_data = {
            'id': 'fb_id_789',
            'email': 'user@facebook.com',
            'first_name': 'Alice',
            'last_name': 'Brown',
            'picture': {'data': {'url': 'https://graph.facebook.com/photo'}},
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        with patch('requests.get', return_value=mock_resp):
            result = provider.get_user_info('fake_token')
        assert result['provider_user_id'] == 'fb_id_789'
        assert result['email'] == 'user@facebook.com'
        assert result['first_name'] == 'Alice'

    def test_get_user_info_failure(self):
        provider = FacebookOAuthProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch('requests.get', return_value=mock_resp):
            result = provider.get_user_info('bad_token')
        assert result is None

    def test_get_user_info_exception(self):
        provider = FacebookOAuthProvider()
        with patch('requests.get', side_effect=Exception("network error")):
            result = provider.get_user_info('bad_token')
        assert result is None

    def test_provider_name(self):
        assert FacebookOAuthProvider().provider_name == 'facebook'

    def test_exchange_code(self):
        provider = FacebookOAuthProvider()
        with patch.object(provider, '_post', return_value={'access_token': 'fb_tok'}):
            result = provider.exchange_code('code', 'https://app.com/callback')
        assert result['access_token'] == 'fb_tok'


# ===========================================================================
# SocialAuthService Tests
# ===========================================================================

@pytest.mark.django_db
class TestSocialAuthService:

    def test_authenticate_creates_new_user(self):
        app = _app("SocialSvcApp")
        service = SocialAuthService()
        success, data, error = service.authenticate(
            provider_name='github',
            user_data=GITHUB_USER_DATA,
            application=app,
            ip_address='127.0.0.1',
        )
        assert success is True
        assert 'access_token' in data
        assert error == ''
        assert User.objects.filter(email='github@example.com').exists()

    @override_settings(TENXYTE_SOCIAL_AUTO_MERGE_ACCOUNTS=True)
    def test_authenticate_links_existing_user_by_email(self):
        app = _app("SocialSvcApp2")
        existing = _user("github@example.com")
        service = SocialAuthService()
        success, data, error = service.authenticate(
            provider_name='github',
            user_data=GITHUB_USER_DATA,
            application=app,
            ip_address='127.0.0.1',
        )
        assert success is True
        conn = SocialConnection.objects.get(provider='github', provider_user_id='gh_123')
        assert conn.user == existing

    def test_authenticate_reuses_existing_social_connection(self):
        app = _app("SocialSvcApp3")
        user = _user("returning@example.com")
        SocialConnection.get_or_create_for_user(
            user=user, provider='google', provider_user_id='google_456',
        )
        service = SocialAuthService()
        success, data, error = service.authenticate(
            provider_name='google',
            user_data={**GOOGLE_USER_DATA, 'email': 'returning@example.com'},
            application=app,
            ip_address='127.0.0.1',
        )
        assert success is True
        assert User.objects.filter(email='returning@example.com').count() == 1

    def test_authenticate_fails_for_inactive_user(self):
        app = _app("SocialSvcApp4")
        user = _user("inactive_social@example.com")
        user.is_active = False
        user.save()
        SocialConnection.get_or_create_for_user(
            user=user, provider='github', provider_user_id='gh_inactive',
        )
        service = SocialAuthService()
        success, data, error = service.authenticate(
            provider_name='github',
            user_data={**GITHUB_USER_DATA, 'provider_user_id': 'gh_inactive'},
            application=app,
            ip_address='127.0.0.1',
        )
        assert success is False
        assert 'disabled' in error.lower()

    def test_authenticate_fails_without_provider_user_id(self):
        app = _app("SocialSvcApp5")
        service = SocialAuthService()
        success, data, error = service.authenticate(
            provider_name='github',
            user_data={'provider_user_id': '', 'email': 'x@example.com'},
            application=app,
            ip_address='127.0.0.1',
        )
        assert success is False
        assert 'missing user ID' in error

    def test_authenticate_creates_social_connection(self):
        app = _app("SocialSvcApp6")
        service = SocialAuthService()
        service.authenticate(
            provider_name='microsoft',
            user_data=MICROSOFT_USER_DATA,
            application=app,
            ip_address='127.0.0.1',
        )
        assert SocialConnection.objects.filter(
            provider='microsoft', provider_user_id='ms_789'
        ).exists()

    @override_settings(TENXYTE_SOCIAL_AUTO_MERGE_ACCOUNTS=True)
    def test_authenticate_multiple_providers_same_user(self):
        app = _app("SocialSvcApp7")
        service = SocialAuthService()
        # First: GitHub
        service.authenticate(
            provider_name='github',
            user_data={**GITHUB_USER_DATA, 'email': 'multi_provider@example.com'},
            application=app, ip_address='127.0.0.1',
        )
        user = User.objects.get(email='multi_provider@example.com')
        # Second: Google (same email → same user)
        service.authenticate(
            provider_name='google',
            user_data={**GOOGLE_USER_DATA, 'email': 'multi_provider@example.com'},
            application=app, ip_address='127.0.0.1',
        )
        assert SocialConnection.objects.filter(user=user).count() == 2

    def test_authenticate_no_email_no_connection(self):
        app = _app("SocialSvcApp8")
        service = SocialAuthService()
        user_data = {
            'provider_user_id': 'no_email_123',
            'email': None,
            'first_name': 'No',
            'last_name': 'Email'
        }
        success, data, error = service.authenticate('github', user_data, app, '127.0.0.1')
        assert success is True
        assert User.objects.filter(first_name='No').exists()

    def test_authenticate_account_locked(self):
        from django.utils import timezone
        import datetime
        app = _app("SocialSvcApp9")
        user = _user("locked_social@example.com")
        
        # Simulate locked account
        user.is_locked = True
        user.locked_until = timezone.now() + datetime.timedelta(hours=1)
        user.save()
        
        SocialConnection.get_or_create_for_user(
            user=user, provider='github', provider_user_id='gh_locked',
        )
        service = SocialAuthService()
        success, data, error = service.authenticate(
            provider_name='github',
            user_data={**GITHUB_USER_DATA, 'provider_user_id': 'gh_locked'},
            application=app,
            ip_address='127.0.0.1',
        )
        assert success is False
        assert 'locked' in error.lower()

class TestAbstractOAuthProvider:
    def test_abstract_methods_execute_for_coverage(self):
        from tenxyte.services.social_auth_service import AbstractOAuthProvider
        class MockProvider(AbstractOAuthProvider):
            @property
            def provider_name(self):
                return super().provider_name
                
            def get_user_info(self, access_token):
                return super().get_user_info(access_token)
                
            def exchange_code(self, code, redirect_uri):
                return super().exchange_code(code, redirect_uri)
        
        m = MockProvider()
        # Just calling them to cover the lines containing `...`
        _ = getattr(m, 'provider_name', None)
        m.get_user_info("token")
        m.exchange_code("code", "uri")


# ===========================================================================
# SocialAuthView Tests
# ===========================================================================

@pytest.mark.django_db
class TestSocialAuthView:

    def test_unsupported_provider_returns_400(self):
        app = _app("ViewApp1")
        resp = _post('twitter', {'access_token': 'tok'}, app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'PROVIDER_NOT_SUPPORTED'

    def test_missing_credentials_returns_400(self):
        app = _app("ViewApp2")
        resp = _post('github', {}, app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'MISSING_CREDENTIALS'

    def test_code_without_redirect_uri_returns_400(self):
        app = _app("ViewApp3")
        resp = _post('github', {'code': 'abc123'}, app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'REDIRECT_URI_REQUIRED'

    def test_provider_auth_failed_returns_401(self):
        app = _app("ViewApp4")
        with patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.get_user_info', return_value=None):
            resp = _post('github', {'access_token': 'bad_token'}, app=app)
        assert resp.status_code == 401
        assert resp.data['code'] == 'PROVIDER_AUTH_FAILED'

    def test_successful_auth_with_access_token(self):
        app = _app("ViewApp5")
        with patch(
            'tenxyte.services.social_auth_service.GitHubOAuthProvider.get_user_info',
            return_value=GITHUB_USER_DATA
        ):
            resp = _post('github', {'access_token': 'valid_token'}, app=app)
        assert resp.status_code == 200
        assert 'access_token' in resp.data

    def test_successful_auth_with_code(self):
        app = _app("ViewApp6")
        with patch(
            'tenxyte.services.social_auth_service.GitHubOAuthProvider.exchange_code',
            return_value={'access_token': 'exchanged_token'}
        ), patch(
            'tenxyte.services.social_auth_service.GitHubOAuthProvider.get_user_info',
            return_value={**GITHUB_USER_DATA, 'provider_user_id': 'gh_code_test'}
        ):
            resp = _post('github', {
                'code': 'auth_code',
                'redirect_uri': 'https://app.com/callback'
            }, app=app)
        assert resp.status_code == 200
        assert 'access_token' in resp.data

    def test_code_exchange_failure_returns_401(self):
        app = _app("ViewApp7")
        with patch(
            'tenxyte.services.social_auth_service.GitHubOAuthProvider.exchange_code',
            return_value=None
        ):
            resp = _post('github', {
                'code': 'bad_code',
                'redirect_uri': 'https://app.com/callback'
            }, app=app)
        assert resp.status_code == 401

    def test_google_id_token_auth(self):
        app = _app("ViewApp8")
        with patch(
            'tenxyte.services.social_auth_service.GoogleOAuthProvider.verify_id_token',
            return_value={**GOOGLE_USER_DATA, 'provider_user_id': 'google_idtoken_test'}
        ):
            resp = _post('google', {'id_token': 'valid_id_token'}, app=app)
        assert resp.status_code == 200
        assert 'access_token' in resp.data

    def test_id_token_only_works_for_google(self):
        app = _app("ViewApp9")
        # id_token sent to github → should return 400 (MISSING_CREDENTIALS)
        resp = _post('github', {'id_token': 'some_token'}, app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'MISSING_CREDENTIALS'

    @override_settings(TENXYTE_SOCIAL_PROVIDERS=['google'])
    def test_disabled_provider_returns_400(self):
        app = _app("ViewApp10")
        resp = _post('github', {'access_token': 'tok'}, app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'PROVIDER_NOT_SUPPORTED'

    def test_authenticate_failure_returns_401(self):
        app = _app("ViewAppAuthFail")
        with patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.get_user_info', return_value=GITHUB_USER_DATA):
            with patch('tenxyte.services.social_auth_service.SocialAuthService.authenticate', return_value=(False, None, "Some error")):
                resp = _post('github', {'access_token': 'valid_token'}, app=app)
        assert resp.status_code == 401
        assert resp.data['code'] == 'SOCIAL_AUTH_FAILED'
        assert resp.data['error'] == "Some error"

@pytest.mark.django_db
class TestSocialAuthCallbackView:
    
    def _get(self, provider, params=None, app=None):
        factory = APIRequestFactory()
        url = f'/auth/social/{provider}/callback/'
        if params:
            import urllib.parse
            url += '?' + urllib.parse.urlencode(params)
        req = factory.get(url)
        if app:
            req.application = app
        req.META['REMOTE_ADDR'] = '127.0.0.1'
        from tenxyte.views.social_auth_views import SocialAuthCallbackView
        view = SocialAuthCallbackView.as_view()
        return view(req, provider=provider)

    def test_unsupported_provider_returns_400(self):
        resp = self._get('twitter', {'code': 'abc', 'redirect_uri': 'http://app.com'})
        assert resp.status_code == 400
        assert resp.data['code'] == 'PROVIDER_NOT_SUPPORTED'

    def test_missing_code_returns_400(self):
        resp = self._get('github', {'redirect_uri': 'http://app.com'})
        assert resp.status_code == 400
        assert resp.data['code'] == 'MISSING_CODE'

    def test_missing_redirect_uri_returns_400(self):
        resp = self._get('github', {'code': 'abc'})
        assert resp.status_code == 400
        assert resp.data['code'] == 'MISSING_REDIRECT_URI'

    def test_code_exchange_failure_returns_401(self):
        with patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.exchange_code', return_value=None):
            resp = self._get('github', {'code': 'abc', 'redirect_uri': 'http://app.com'})
        assert resp.status_code == 401
        assert resp.data['code'] == 'CODE_EXCHANGE_FAILED'

    def test_get_user_info_failure_returns_401(self):
        with patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.exchange_code', return_value={'access_token': 'tok'}), \
             patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.get_user_info', return_value=None):
            resp = self._get('github', {'code': 'abc', 'redirect_uri': 'http://app.com'})
        assert resp.status_code == 401
        assert resp.data['code'] == 'PROVIDER_AUTH_FAILED'

    def test_authenticate_failure_returns_401(self):
        app = _app("CallbackViewAppAuthFail")
        with patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.exchange_code', return_value={'access_token': 'tok'}), \
             patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.get_user_info', return_value=GITHUB_USER_DATA), \
             patch('tenxyte.services.social_auth_service.SocialAuthService.authenticate', return_value=(False, None, "Auth error")):
            resp = self._get('github', {'code': 'abc', 'redirect_uri': 'http://app.com'}, app=app)
        assert resp.status_code == 401
        assert resp.data['code'] == 'SOCIAL_AUTH_FAILED'

    def test_successful_callback_returns_200(self):
        app = _app("CallbackViewAppSuccess")
        with patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.exchange_code', return_value={'access_token': 'tok'}), \
             patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.get_user_info', return_value=GITHUB_USER_DATA), \
             patch('tenxyte.services.social_auth_service.SocialAuthService.authenticate', return_value=(True, {'access': 'jwt', 'user': {}}, "")):
            resp = self._get('github', {'code': 'abc', 'redirect_uri': 'http://app.com'}, app=app)
        assert resp.status_code == 200
        assert resp.data['access'] == 'jwt'

    def test_exception_handling_returns_400(self):
        with patch('tenxyte.services.social_auth_service.GitHubOAuthProvider.exchange_code', side_effect=Exception("Boom")):
            resp = self._get('github', {'code': 'abc', 'redirect_uri': 'http://app.com'})
        assert resp.status_code == 400
        assert resp.data['code'] == 'CALLBACK_ERROR'
