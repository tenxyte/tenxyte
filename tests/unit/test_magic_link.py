"""
Tests for Magic Link (passwordless authentication).

Coverage targets:
- models/magic_link.py
- services/magic_link_service.py
- views/magic_link_views.py
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory
from django.test import override_settings

from tenxyte.models import User, Application, MagicLinkToken
from tenxyte.services.magic_link_service import MagicLinkService
from tenxyte.views.magic_link_views import MagicLinkRequestView, MagicLinkVerifyView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="MagicApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email="magic@example.com"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


def _post(view_cls, path, data, app=None):
    factory = APIRequestFactory()
    with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
        req = factory.post(path, data, format='json')
        if app:
            req.application = app
        return view_cls.as_view()(req)


def _get(view_cls, path, params="", app=None):
    factory = APIRequestFactory()
    with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
        req = factory.get(f"{path}?{params}")
        if app:
            req.application = app
        return view_cls.as_view()(req)


# ===========================================================================
# MagicLinkToken Model Tests
# ===========================================================================

@pytest.mark.django_db
class TestMagicLinkTokenModel:

    def test_generate_creates_token(self):
        user = _user("model@example.com")
        instance, raw_token = MagicLinkToken.generate(user=user, expiry_minutes=15)
        assert instance.pk is not None
        assert instance.user == user
        assert instance.is_used is False
        assert raw_token  # non-empty string

    def test_token_is_hashed(self):
        user = _user("hash@example.com")
        instance, raw_token = MagicLinkToken.generate(user=user)
        # The stored token should NOT equal the raw token
        assert instance.token != raw_token

    def test_get_valid_returns_instance(self):
        user = _user("valid@example.com")
        instance, raw_token = MagicLinkToken.generate(user=user, expiry_minutes=15)
        found = MagicLinkToken.get_valid(raw_token)
        assert found is not None
        assert found.pk == instance.pk

    def test_get_valid_returns_none_for_unknown_token(self):
        found = MagicLinkToken.get_valid("nonexistent-token-xyz")
        assert found is None

    def test_get_valid_returns_none_for_used_token(self):
        user = _user("used@example.com")
        instance, raw_token = MagicLinkToken.generate(user=user)
        instance.consume()
        found = MagicLinkToken.get_valid(raw_token)
        assert found is None

    def test_get_valid_returns_none_for_expired_token(self):
        user = _user("expired@example.com")
        instance, raw_token = MagicLinkToken.generate(user=user, expiry_minutes=15)
        # Force expiry
        instance.expires_at = timezone.now() - timedelta(minutes=1)
        instance.save()
        found = MagicLinkToken.get_valid(raw_token)
        assert found is None

    def test_consume_marks_as_used(self):
        user = _user("consume@example.com")
        instance, _ = MagicLinkToken.generate(user=user)
        assert instance.is_used is False
        instance.consume()
        instance.refresh_from_db()
        assert instance.is_used is True
        assert instance.used_at is not None

    def test_is_valid_true_for_fresh_token(self):
        user = _user("fresh@example.com")
        instance, _ = MagicLinkToken.generate(user=user, expiry_minutes=15)
        assert instance.is_valid() is True

    def test_is_valid_false_after_consume(self):
        user = _user("consumed2@example.com")
        instance, _ = MagicLinkToken.generate(user=user)
        instance.consume()
        assert instance.is_valid() is False

    def test_is_valid_false_when_expired(self):
        user = _user("expired2@example.com")
        instance, _ = MagicLinkToken.generate(user=user)
        instance.expires_at = timezone.now() - timedelta(seconds=1)
        assert instance.is_valid() is False

    def test_generate_with_application(self):
        user = _user("withapp@example.com")
        app = _app("TestApp")
        instance, _ = MagicLinkToken.generate(user=user, application=app)
        assert instance.application == app

    def test_generate_with_ip_address(self):
        user = _user("withip@example.com")
        instance, _ = MagicLinkToken.generate(user=user, ip_address="192.168.1.1")
        assert instance.ip_address == "192.168.1.1"


# ===========================================================================
# MagicLinkService Tests
# ===========================================================================

@pytest.mark.django_db
class TestMagicLinkService:

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_magic_link_success(self):
        user = _user("service@example.com")
        service = MagicLinkService()
        with patch.object(service.email_service, 'send_magic_link_email', return_value=True):
            success, error = service.request_magic_link(
                email="service@example.com",
                ip_address="127.0.0.1"
            )
        assert success is True
        assert error == ''

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=False)
    def test_request_magic_link_disabled(self):
        service = MagicLinkService()
        success, error = service.request_magic_link(email="x@example.com")
        assert success is False
        assert 'not enabled' in error

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_magic_link_unknown_email_returns_true(self):
        """Security: should not reveal whether email exists."""
        service = MagicLinkService()
        success, error = service.request_magic_link(
            email="doesnotexist@example.com",
            ip_address="127.0.0.1"
        )
        assert success is True
        assert error == ''

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_magic_link_inactive_user_returns_true(self):
        """Security: inactive user should also return True (no info leak)."""
        user = _user("inactive@example.com")
        user.is_active = False
        user.save()
        service = MagicLinkService()
        success, error = service.request_magic_link(
            email="inactive@example.com",
            ip_address="127.0.0.1"
        )
        assert success is True

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_magic_link_email_failure(self):
        user = _user("emailfail@example.com")
        service = MagicLinkService()
        with patch.object(service.email_service, 'send_magic_link_email', return_value=False):
            success, error = service.request_magic_link(
                email="emailfail@example.com",
                ip_address="127.0.0.1"
            )
        assert success is False
        assert 'Failed' in error

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_magic_link_invalidates_old_tokens(self):
        user = _user("oldtoken@example.com")
        app = _app("OldTokenApp")
        # Create an existing unused token
        old_instance, _ = MagicLinkToken.generate(user=user, application=app)
        assert old_instance.is_used is False

        service = MagicLinkService()
        with patch.object(service.email_service, 'send_magic_link_email', return_value=True):
            service.request_magic_link(
                email="oldtoken@example.com",
                application=app,
                ip_address="127.0.0.1"
            )

        old_instance.refresh_from_db()
        assert old_instance.is_used is True

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_magic_link_success(self):
        user = _user("verify@example.com")
        app = _app("VerifyApp")
        instance, raw_token = MagicLinkToken.generate(user=user, application=app)

        service = MagicLinkService()
        success, data, error = service.verify_magic_link(
            token=raw_token,
            application=app,
            ip_address="127.0.0.1"
        )
        assert success is True
        assert data is not None
        assert 'access_token' in data
        assert error == ''

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=False)
    def test_verify_magic_link_disabled(self):
        service = MagicLinkService()
        success, data, error = service.verify_magic_link(token="anytoken")
        assert success is False
        assert data is None
        assert 'not enabled' in error

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_magic_link_invalid_token(self):
        service = MagicLinkService()
        success, data, error = service.verify_magic_link(
            token="invalid-token-xyz",
            ip_address="127.0.0.1"
        )
        assert success is False
        assert data is None
        assert 'Invalid' in error

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_magic_link_single_use(self):
        """Token should be consumed after first use."""
        user = _user("singleuse@example.com")
        app = _app("SingleUseApp")
        instance, raw_token = MagicLinkToken.generate(user=user, application=app)

        service = MagicLinkService()
        # First use — should succeed
        success1, _, _ = service.verify_magic_link(token=raw_token, application=app, ip_address="127.0.0.1")
        assert success1 is True

        # Second use — should fail
        success2, _, error2 = service.verify_magic_link(token=raw_token, application=app, ip_address="127.0.0.1")
        assert success2 is False
        assert 'Invalid' in error2

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_magic_link_inactive_user(self):
        user = _user("inactivecheck@example.com")
        app = _app("InactiveApp")
        instance, raw_token = MagicLinkToken.generate(user=user, application=app)
        user.is_active = False
        user.save()

        service = MagicLinkService()
        success, data, error = service.verify_magic_link(token=raw_token, application=app, ip_address="127.0.0.1")
        assert success is False
        assert 'disabled' in error.lower()


# ===========================================================================
# MagicLinkRequestView Tests
# ===========================================================================

@pytest.mark.django_db
class TestMagicLinkRequestView:

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_returns_200_for_valid_email(self):
        user = _user("view_req@example.com")
        app = _app("ReqViewApp")
        with patch('tenxyte.services.magic_link_service.MagicLinkService.request_magic_link', return_value=(True, '')):
            resp = _post(MagicLinkRequestView, '/magic-link/request/', {'email': 'view_req@example.com'}, app=app)
        assert resp.status_code == 200
        assert 'message' in resp.data

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_returns_400_for_missing_email(self):
        app = _app("ReqViewApp2")
        resp = _post(MagicLinkRequestView, '/magic-link/request/', {}, app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'EMAIL_REQUIRED'

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_returns_503_on_service_failure(self):
        app = _app("ReqViewApp3")
        with patch('tenxyte.services.magic_link_service.MagicLinkService.request_magic_link', return_value=(False, 'Failed to send')):
            resp = _post(MagicLinkRequestView, '/magic-link/request/', {'email': 'x@example.com'}, app=app)
        assert resp.status_code == 503

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_request_returns_200_for_unknown_email(self):
        """Security: should not reveal if email exists."""
        app = _app("ReqViewApp4")
        with patch('tenxyte.services.magic_link_service.MagicLinkService.request_magic_link', return_value=(True, '')):
            resp = _post(MagicLinkRequestView, '/magic-link/request/', {'email': 'unknown@example.com'}, app=app)
        assert resp.status_code == 200


# ===========================================================================
# MagicLinkVerifyView Tests
# ===========================================================================

@pytest.mark.django_db
class TestMagicLinkVerifyView:

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_returns_200_with_tokens(self):
        user = _user("view_verify@example.com")
        app = _app("VerifyViewApp")
        instance, raw_token = MagicLinkToken.generate(user=user, application=app)

        factory = APIRequestFactory()
        with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
            req = factory.get(f'/magic-link/verify/?token={raw_token}')
            req.application = app
            resp = MagicLinkVerifyView.as_view()(req)

        assert resp.status_code == 200
        assert 'access_token' in resp.data

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_returns_400_for_missing_token(self):
        app = _app("VerifyViewApp2")
        resp = _get(MagicLinkVerifyView, '/magic-link/verify/', '', app=app)
        assert resp.status_code == 400
        assert resp.data['code'] == 'TOKEN_REQUIRED'

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_returns_401_for_invalid_token(self):
        app = _app("VerifyViewApp3")
        resp = _get(MagicLinkVerifyView, '/magic-link/verify/', 'token=badtoken', app=app)
        assert resp.status_code == 401
        assert resp.data['code'] == 'MAGIC_LINK_INVALID'

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_returns_401_for_used_token(self):
        user = _user("usedtoken@example.com")
        app = _app("VerifyViewApp4")
        instance, raw_token = MagicLinkToken.generate(user=user, application=app)
        instance.consume()

        factory = APIRequestFactory()
        with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
            req = factory.get(f'/magic-link/verify/?token={raw_token}')
            req.application = app
            resp = MagicLinkVerifyView.as_view()(req)

        assert resp.status_code == 401

    @override_settings(TENXYTE_MAGIC_LINK_ENABLED=True)
    def test_verify_returns_401_for_expired_token(self):
        user = _user("expiredtoken@example.com")
        app = _app("VerifyViewApp5")
        instance, raw_token = MagicLinkToken.generate(user=user, application=app)
        instance.expires_at = timezone.now() - timedelta(minutes=1)
        instance.save()

        factory = APIRequestFactory()
        with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True):
            req = factory.get(f'/magic-link/verify/?token={raw_token}')
            req.application = app
            resp = MagicLinkVerifyView.as_view()(req)

        assert resp.status_code == 401
