"""
Tests for WebAuthn / Passkeys (FIDO2).

All py_webauthn calls are mocked — no real FIDO2 library required.

Coverage targets:
- models/webauthn.py (WebAuthnCredential, WebAuthnChallenge)
- services/webauthn_service.py (WebAuthnService)
- views/webauthn_views.py (all 6 views)
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application
from tenxyte.models.webauthn import WebAuthnCredential, WebAuthnChallenge
from tenxyte.services.webauthn_service import WebAuthnService
from tenxyte.services.jwt_service import JWTService
from tenxyte.views.webauthn_views import (
    WebAuthnRegisterBeginView, WebAuthnRegisterCompleteView,
    WebAuthnAuthenticateBeginView, WebAuthnAuthenticateCompleteView,
    WebAuthnCredentialListView, WebAuthnCredentialDeleteView,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="WebAuthnApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email="webauthn@example.com"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


def _jwt(user, app):
    return JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh"
    )["access_token"]


def _credential(user, cred_id="cred_abc123", device_name="iPhone 15"):
    return WebAuthnCredential.objects.create(
        user=user,
        credential_id=cred_id,
        public_key="fakepublickey",
        sign_count=0,
        device_name=device_name,
    )


def _challenge(user, operation="register", expired=False, used=False):
    instance, raw = WebAuthnChallenge.generate(
        operation=operation,
        user=user,
        expiry_seconds=300
    )
    if expired:
        instance.expires_at = timezone.now() - timedelta(seconds=1)
        instance.save()
    if used:
        instance.consume()
    return instance, raw


def _authed_post(view_cls, path, data, user, app, **kwargs):
    token = _jwt(user, app)
    factory = APIRequestFactory()
    req = factory.post(path, data, format='json')
    req.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    req.application = app
    return view_cls.as_view()(req, **kwargs)


def _authed_get(view_cls, path, user, app):
    token = _jwt(user, app)
    factory = APIRequestFactory()
    req = factory.get(path)
    req.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    req.application = app
    return view_cls.as_view()(req)


def _authed_delete(view_cls, path, user, app, **kwargs):
    token = _jwt(user, app)
    factory = APIRequestFactory()
    req = factory.delete(path)
    req.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    req.application = app
    return view_cls.as_view()(req, **kwargs)


def _anon_post(view_cls, path, data, app=None):
    factory = APIRequestFactory()
    req = factory.post(path, data, format='json')
    if app:
        req.application = app
    return view_cls.as_view()(req)


# ===========================================================================
# WebAuthnChallenge Model Tests
# ===========================================================================

@pytest.mark.django_db
class TestWebAuthnChallengeModel:

    def test_generate_creates_challenge(self):
        user = _user("ch_create@example.com")
        instance, raw = WebAuthnChallenge.generate(operation='register', user=user)
        assert instance.pk is not None
        assert instance.challenge == raw
        assert instance.is_used is False
        assert instance.operation == 'register'

    def test_is_valid_true_for_fresh_challenge(self):
        user = _user("ch_valid@example.com")
        instance, _ = WebAuthnChallenge.generate(operation='register', user=user)
        assert instance.is_valid() is True

    def test_is_valid_false_when_expired(self):
        user = _user("ch_expired@example.com")
        instance, _ = WebAuthnChallenge.generate(operation='register', user=user)
        instance.expires_at = timezone.now() - timedelta(seconds=1)
        assert instance.is_valid() is False

    def test_is_valid_false_when_used(self):
        user = _user("ch_used@example.com")
        instance, _ = WebAuthnChallenge.generate(operation='register', user=user)
        instance.consume()
        assert instance.is_valid() is False

    def test_consume_marks_as_used(self):
        user = _user("ch_consume@example.com")
        instance, _ = WebAuthnChallenge.generate(operation='register', user=user)
        instance.consume()
        instance.refresh_from_db()
        assert instance.is_used is True

    def test_generate_without_user(self):
        instance, raw = WebAuthnChallenge.generate(operation='authenticate')
        assert instance.user is None
        assert instance.is_valid() is True


# ===========================================================================
# WebAuthnCredential Model Tests
# ===========================================================================

@pytest.mark.django_db
class TestWebAuthnCredentialModel:

    def test_create_credential(self):
        user = _user("cred_create@example.com")
        cred = _credential(user)
        assert cred.pk is not None
        assert cred.user == user
        assert cred.sign_count == 0

    def test_update_sign_count(self):
        user = _user("cred_sign@example.com")
        cred = _credential(user)
        cred.update_sign_count(42)
        cred.refresh_from_db()
        assert cred.sign_count == 42
        assert cred.last_used_at is not None

    def test_credential_id_unique(self):
        from django.db import IntegrityError
        user = _user("cred_unique@example.com")
        _credential(user, cred_id="unique_cred_001")
        with pytest.raises(IntegrityError):
            WebAuthnCredential.objects.create(
                user=user,
                credential_id="unique_cred_001",
                public_key="anotherkey",
                sign_count=0,
            )


# ===========================================================================
# WebAuthnService Tests (mocked py_webauthn)
# ===========================================================================

@pytest.mark.django_db
class TestWebAuthnService:

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=False)
    def test_begin_registration_disabled(self):
        user = _user("svc_disabled@example.com")
        service = WebAuthnService()
        success, data, error = service.begin_registration(user)
        assert success is False
        assert 'not enabled' in error

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_begin_registration_success(self):
        user = _user("svc_begin_reg@example.com")
        service = WebAuthnService()

        mock_options = MagicMock()
        mock_webauthn = MagicMock()
        mock_webauthn.generate_registration_options.return_value = mock_options
        mock_webauthn.options_to_json.return_value = '{"challenge": "abc"}'
        mock_webauthn.PublicKeyCredentialDescriptor = MagicMock()

        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, data, error = service.begin_registration(user)

        assert success is True
        assert 'challenge_id' in data
        assert 'options' in data
        assert error == ''

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_begin_registration_error(self):
        user = _user("svc_begin_err@example.com")
        service = WebAuthnService()

        mock_webauthn = MagicMock()
        mock_webauthn.generate_registration_options.side_effect = Exception("webauthn error")
        mock_webauthn.PublicKeyCredentialDescriptor = MagicMock()

        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, data, error = service.begin_registration(user)

        assert success is False
        assert data is None

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_registration_invalid_challenge(self):
        user = _user("svc_comp_reg_inv@example.com")
        service = WebAuthnService()
        success, cred, error = service.complete_registration(
            user=user,
            credential_data={},
            challenge_id=99999,
        )
        assert success is False
        assert 'Invalid' in error

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_registration_expired_challenge(self):
        user = _user("svc_comp_reg_exp@example.com")
        instance, _ = _challenge(user, operation='register', expired=True)
        service = WebAuthnService()
        success, cred, error = service.complete_registration(
            user=user,
            credential_data={},
            challenge_id=instance.id,
        )
        assert success is False
        assert 'expired' in error.lower()

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_registration_verification_failure(self):
        user = _user("svc_comp_reg_fail@example.com")
        instance, _ = _challenge(user, operation='register')
        service = WebAuthnService()

        mock_webauthn = MagicMock()
        mock_webauthn.verify_registration_response.side_effect = Exception("invalid credential")

        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, cred, error = service.complete_registration(
                user=user,
                credential_data={'id': 'test'},
                challenge_id=instance.id,
            )

        assert success is False
        assert 'verification failed' in error.lower()

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_registration_success(self):
        user = _user("svc_comp_reg_ok@example.com")
        instance, _ = _challenge(user, operation='register')
        service = WebAuthnService()

        mock_verification = MagicMock()
        mock_verification.credential_id = b'new_cred_id_123'
        mock_verification.credential_public_key = b'fakepublickey'
        mock_verification.sign_count = 0
        mock_verification.aaguid = 'aaguid-123'

        mock_webauthn = MagicMock()
        mock_webauthn.verify_registration_response.return_value = mock_verification

        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, cred, error = service.complete_registration(
                user=user,
                credential_data={'id': 'test'},
                challenge_id=instance.id,
                device_name='MacBook Pro'
            )

        assert success is True
        assert cred is not None
        assert cred.device_name == 'MacBook Pro'
        assert error == ''

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=False)
    def test_begin_authentication_disabled(self):
        service = WebAuthnService()
        success, data, error = service.begin_authentication()
        assert success is False
        assert 'not enabled' in error

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_begin_authentication_success(self):
        user = _user("svc_begin_auth@example.com")
        service = WebAuthnService()

        mock_webauthn = MagicMock()
        mock_webauthn.generate_authentication_options.return_value = MagicMock()
        mock_webauthn.options_to_json.return_value = '{"challenge": "xyz"}'
        mock_webauthn.PublicKeyCredentialDescriptor = MagicMock()

        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, data, error = service.begin_authentication(user=user)

        assert success is True
        assert 'challenge_id' in data

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_authentication_invalid_challenge(self):
        service = WebAuthnService()
        success, data, error = service.complete_authentication(
            credential_data={'id': 'test'},
            challenge_id=99999,
        )
        assert success is False
        assert 'Invalid' in error

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_authentication_unknown_credential(self):
        user = _user("svc_auth_unk@example.com")
        instance, _ = _challenge(user, operation='authenticate')
        service = WebAuthnService()
        success, data, error = service.complete_authentication(
            credential_data={'id': 'nonexistent_cred'},
            challenge_id=instance.id,
        )
        assert success is False
        assert 'Unknown credential' in error

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_authentication_success(self):
        app = _app("AuthSvcApp")
        user = _user("svc_auth_ok@example.com")
        cred = _credential(user, cred_id="auth_cred_ok")
        instance, _ = _challenge(user, operation='authenticate')

        service = WebAuthnService()

        mock_verification = MagicMock()
        mock_verification.new_sign_count = 1

        mock_webauthn = MagicMock()
        mock_webauthn.verify_authentication_response.return_value = mock_verification

        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, data, error = service.complete_authentication(
                credential_data={'id': 'auth_cred_ok'},
                challenge_id=instance.id,
                application=app,
                ip_address='127.0.0.1',
            )

        assert success is True
        assert 'access_token' in data
        assert error == ''

    def test_list_credentials(self):
        user = _user("svc_list@example.com")
        _credential(user, cred_id="list_cred_1", device_name="iPhone")
        _credential(user, cred_id="list_cred_2", device_name="MacBook")
        service = WebAuthnService()
        result = service.list_credentials(user)
        assert len(result) == 2
        device_names = {r['device_name'] for r in result}
        assert 'iPhone' in device_names
        assert 'MacBook' in device_names

    def test_delete_credential_success(self):
        user = _user("svc_del@example.com")
        cred = _credential(user, cred_id="del_cred_1")
        service = WebAuthnService()
        success, error = service.delete_credential(user, cred.id)
        assert success is True
        assert not WebAuthnCredential.objects.filter(id=cred.id).exists()

    def test_delete_credential_not_found(self):
        user = _user("svc_del_nf@example.com")
        service = WebAuthnService()
        success, error = service.delete_credential(user, 99999)
        assert success is False
        assert 'not found' in error.lower()

    def test_delete_credential_wrong_user(self):
        user1 = _user("svc_del_u1@example.com")
        user2 = _user("svc_del_u2@example.com")
        cred = _credential(user1, cred_id="del_cred_wrong")
        service = WebAuthnService()
        success, error = service.delete_credential(user2, cred.id)
        assert success is False

    def test_get_webauthn_import_error(self):
        from tenxyte.services.webauthn_service import _get_webauthn
        with patch.dict('sys.modules', {'webauthn': None}):
            with pytest.raises(ImportError):
                _get_webauthn()

    @override_settings(TENXYTE_WEBAUTHN_RP_ID='example.com')
    def test_get_origin_not_localhost(self):
        service = WebAuthnService()
        assert service._get_origin() == 'https://example.com'

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=False)
    def test_complete_registration_disabled(self):
        user = _user("svc_comp_reg_dis@example.com")
        service = WebAuthnService()
        success, cred, error = service.complete_registration(user, {}, 1)
        assert success is False
        assert 'not enabled' in error

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_begin_authentication_error(self):
        user = _user("svc_begin_auth_err@example.com")
        service = WebAuthnService()
        mock_webauthn = MagicMock()
        mock_webauthn.generate_authentication_options.side_effect = Exception("auth err")
        mock_webauthn.PublicKeyCredentialDescriptor = MagicMock()
        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, data, error = service.begin_authentication(user)
        assert success is False
        assert error == 'An unexpected error occurred during WebAuthn authentication.'

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=False)
    def test_complete_authentication_disabled(self):
        service = WebAuthnService()
        success, data, error = service.complete_authentication({}, 1)
        assert success is False
        assert 'not enabled' in error

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_authentication_expired_challenge(self):
        user = _user("svc_comp_auth_exp@example.com")
        instance, _ = _challenge(user, operation='authenticate', expired=True)
        service = WebAuthnService()
        success, data, error = service.complete_authentication({'id': 'test'}, instance.id)
        assert success is False
        assert 'expired' in error.lower()

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_authentication_inactive_user(self):
        user = _user("svc_comp_auth_inactive@example.com")
        user.is_active = False
        user.save()
        cred = _credential(user, cred_id="auth_cred_inactive")
        instance, _ = _challenge(user, operation='authenticate')
        service = WebAuthnService()
        success, data, error = service.complete_authentication({'id': 'auth_cred_inactive'}, instance.id)
        assert success is False
        assert 'disabled' in error.lower()

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_authentication_locked_user(self):
        import datetime
        user = _user("svc_comp_auth_locked@example.com")
        user.is_locked = True
        user.locked_until = timezone.now() + datetime.timedelta(hours=1)
        user.save()
        cred = _credential(user, cred_id="auth_cred_locked")
        instance, _ = _challenge(user, operation='authenticate')
        service = WebAuthnService()
        success, data, error = service.complete_authentication({'id': 'auth_cred_locked'}, instance.id)
        assert success is False
        assert 'locked' in error.lower()

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_complete_authentication_verification_failure(self):
        user = _user("svc_comp_auth_ver_fail@example.com")
        cred = _credential(user, cred_id="auth_cred_fail")
        instance, _ = _challenge(user, operation='authenticate')
        service = WebAuthnService()
        mock_webauthn = MagicMock()
        mock_webauthn.verify_authentication_response.side_effect = Exception("failed verif")
        with patch('tenxyte.services.webauthn_service._get_webauthn', return_value=mock_webauthn):
            success, data, error = service.complete_authentication({'id': 'auth_cred_fail'}, instance.id)
        assert success is False
        assert 'failed' in error.lower()


# ===========================================================================
# WebAuthn Views Tests
# ===========================================================================

@pytest.mark.django_db
class TestWebAuthnViews:

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_register_begin_requires_auth(self):
        factory = APIRequestFactory()
        req = factory.post('/webauthn/register/begin/', {}, format='json')
        resp = WebAuthnRegisterBeginView.as_view()(req)
        assert resp.status_code == 401

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_register_begin_success(self):
        app = _app("ViewRegBeginApp")
        user = _user("view_reg_begin@example.com")
        with patch.object(WebAuthnService, 'begin_registration', return_value=(True, {'challenge_id': 1, 'options': '{}'}, '')):
            resp = _authed_post(WebAuthnRegisterBeginView, '/webauthn/register/begin/', {}, user, app)
        assert resp.status_code == 200
        assert 'challenge_id' in resp.data

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_register_begin_error(self):
        app = _app("ViewRegBeginErrApp")
        user = _user("view_reg_begin_err@example.com")
        with patch.object(WebAuthnService, 'begin_registration', return_value=(False, None, 'WebAuthn error')):
            resp = _authed_post(WebAuthnRegisterBeginView, '/webauthn/register/begin/', {}, user, app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'WEBAUTHN_ERROR'

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_register_complete_missing_fields(self):
        app = _app("ViewRegCompMissApp")
        user = _user("view_reg_comp_miss@example.com")
        resp = _authed_post(WebAuthnRegisterCompleteView, '/webauthn/register/complete/', {}, user, app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'MISSING_FIELDS'

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_register_complete_success(self):
        app = _app("ViewRegCompOkApp")
        user = _user("view_reg_comp_ok@example.com")
        mock_cred = MagicMock()
        mock_cred.id = 1
        mock_cred.device_name = 'iPhone 15'
        mock_cred.created_at.isoformat.return_value = '2026-01-01T00:00:00'
        with patch.object(WebAuthnService, 'complete_registration', return_value=(True, mock_cred, '')):
            resp = _authed_post(WebAuthnRegisterCompleteView, '/webauthn/register/complete/', {
                'challenge_id': 1,
                'credential': {'id': 'test'},
                'device_name': 'iPhone 15',
            }, user, app)
        assert resp.status_code == 201
        assert resp.data['credential']['device_name'] == 'iPhone 15'

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_authenticate_begin_anon_success(self):
        app = _app("ViewAuthBeginApp")
        with patch.object(WebAuthnService, 'begin_authentication', return_value=(True, {'challenge_id': 2, 'options': '{}'}, '')):
            resp = _anon_post(WebAuthnAuthenticateBeginView, '/webauthn/authenticate/begin/', {}, app=app)
        assert resp.status_code == 200

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_authenticate_begin_error(self):
        app = _app("ViewAuthBeginErrApp")
        with patch.object(WebAuthnService, 'begin_authentication', return_value=(False, None, 'error')):
            resp = _anon_post(WebAuthnAuthenticateBeginView, '/webauthn/authenticate/begin/', {}, app=app)
        assert resp.status_code == 400

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_authenticate_complete_missing_fields(self):
        app = _app("ViewAuthCompMissApp")
        resp = _anon_post(WebAuthnAuthenticateCompleteView, '/webauthn/authenticate/complete/', {}, app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'MISSING_FIELDS'

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_authenticate_complete_success(self):
        app = _app("ViewAuthCompOkApp")
        with patch.object(WebAuthnService, 'complete_authentication', return_value=(True, {'access_token': 'tok'}, '')):
            resp = _anon_post(WebAuthnAuthenticateCompleteView, '/webauthn/authenticate/complete/', {
                'challenge_id': 1,
                'credential': {'id': 'test'},
            }, app=app)
        assert resp.status_code == 200
        assert 'access_token' in resp.data

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_authenticate_complete_failure(self):
        app = _app("ViewAuthCompFailApp")
        with patch.object(WebAuthnService, 'complete_authentication', return_value=(False, None, 'invalid')):
            resp = _anon_post(WebAuthnAuthenticateCompleteView, '/webauthn/authenticate/complete/', {
                'challenge_id': 1,
                'credential': {'id': 'bad'},
            }, app=app)
        assert resp.status_code == 401
        assert resp.data['code'] == 'WEBAUTHN_AUTH_FAILED'

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_credential_list_requires_auth(self):
        factory = APIRequestFactory()
        req = factory.get('/webauthn/credentials/')
        resp = WebAuthnCredentialListView.as_view()(req)
        assert resp.status_code == 401

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_credential_list_success(self):
        app = _app("ViewListApp")
        user = _user("view_list@example.com")
        _credential(user, cred_id="list_view_cred_1", device_name="iPad")
        _credential(user, cred_id="list_view_cred_2", device_name="Android")
        resp = _authed_get(WebAuthnCredentialListView, '/webauthn/credentials/', user, app)
        assert resp.status_code == 200
        assert resp.data['count'] == 2

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_credential_delete_success(self):
        app = _app("ViewDelApp")
        user = _user("view_del@example.com")
        cred = _credential(user, cred_id="del_view_cred")
        resp = _authed_delete(WebAuthnCredentialDeleteView, f'/webauthn/credentials/{cred.id}/', user, app, credential_id=cred.id)
        assert resp.status_code == 204
        assert not WebAuthnCredential.objects.filter(id=cred.id).exists()

    @override_settings(TENXYTE_WEBAUTHN_ENABLED=True)
    def test_credential_delete_not_found(self):
        app = _app("ViewDelNFApp")
        user = _user("view_del_nf@example.com")
        resp = _authed_delete(WebAuthnCredentialDeleteView, '/webauthn/credentials/99999/', user, app, credential_id=99999)
        assert resp.status_code == 404
        assert resp.data['code'] == 'CREDENTIAL_NOT_FOUND'
