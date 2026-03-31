"""
Tests for Breach Password Check (HaveIBeenPwned k-anonymity).

Coverage targets:
- services/breach_check_service.py
- Integration in RegisterView and ChangePasswordView
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from tenxyte.services.breach_check_service import BreachCheckService, breach_check_service
from tenxyte.models import User, Application
from tests.integration.django.test_helpers import get_jwt_service
from tenxyte.views.auth_views import RegisterView
from tenxyte.views.password_views import ChangePasswordView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="BreachApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email="breach@example.com", password="OldPass123!"):
    u = User.objects.create(email=email, is_active=True)
    u.set_password(password)
    u.save()
    return u


def _jwt(user, app):
    jwt_service = get_jwt_service()
    return jwt_service.generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh"
    )["access_token"]


def _hibp_response(suffix: str, count: int = 5000) -> str:
    """Build a fake HIBP API response containing the given suffix."""
    return f"{suffix}:{count}\nOTHERSUFFIX123:1\n"


# ===========================================================================
# BreachCheckService Unit Tests
# ===========================================================================

class TestBreachCheckService:

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_is_pwned_returns_true_for_known_password(self):
        import hashlib
        password = "password123"
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()  # lgtm[py/weak-sensitive-data-hashing] codeql[py/weak-sensitive-data-hashing]
        suffix = sha1[5:]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = _hibp_response(suffix, count=9000)
        mock_resp.raise_for_status = MagicMock()

        service = BreachCheckService()
        with patch('requests.get', return_value=mock_resp):
            is_pwned, count = service.is_pwned(password)

        assert is_pwned is True
        assert count == 9000

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_is_pwned_returns_false_for_safe_password(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "AAAAABBBBB:1\nCCCCCDDDDD:2\n"
        mock_resp.raise_for_status = MagicMock()

        service = BreachCheckService()
        with patch('requests.get', return_value=mock_resp):
            is_pwned, count = service.is_pwned("Sup3rS3cur3P@ssw0rd!")

        assert is_pwned is False
        assert count == 0

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=False)
    def test_is_pwned_skips_when_disabled(self):
        service = BreachCheckService()
        with patch('requests.get') as mock_get:
            is_pwned, count = service.is_pwned("anypassword")
        mock_get.assert_not_called()
        assert is_pwned is False
        assert count == 0

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_is_pwned_returns_false_on_timeout(self):
        import requests as req_lib
        service = BreachCheckService()
        with patch('requests.get', side_effect=req_lib.Timeout()):
            is_pwned, count = service.is_pwned("anypassword")
        assert is_pwned is False
        assert count == 0

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_is_pwned_returns_false_on_request_error(self):
        import requests as req_lib
        service = BreachCheckService()
        with patch('requests.get', side_effect=req_lib.RequestException("network error")):
            is_pwned, count = service.is_pwned("anypassword")
        assert is_pwned is False
        assert count == 0

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_check_password_returns_error_when_pwned_and_reject(self):
        service = BreachCheckService()
        with patch.object(service, 'is_pwned', return_value=(True, 5000)):
            ok, error = service.check_password("badpassword")
        assert ok is False
        assert '5,000' in error
        assert 'breaches' in error.lower()

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=False)
    def test_check_password_returns_ok_in_warn_mode(self):
        service = BreachCheckService()
        with patch.object(service, 'is_pwned', return_value=(True, 5000)):
            ok, error = service.check_password("badpassword")
        assert ok is True
        assert error == ''

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_check_password_returns_ok_for_safe_password(self):
        service = BreachCheckService()
        with patch.object(service, 'is_pwned', return_value=(False, 0)):
            ok, error = service.check_password("SafeP@ssw0rd!")
        assert ok is True
        assert error == ''

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=False)
    def test_check_password_always_ok_when_disabled(self):
        service = BreachCheckService()
        ok, error = service.check_password("password")
        assert ok is True
        assert error == ''

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_only_prefix_sent_to_api(self):
        """Verify k-anonymity: only first 5 chars of SHA-1 are sent."""
        import hashlib
        password = "testpassword"
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()  # lgtm[py/weak-sensitive-data-hashing] codeql[py/weak-sensitive-data-hashing]
        expected_prefix = sha1[:5]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""
        mock_resp.raise_for_status = MagicMock()

        service = BreachCheckService()
        with patch('requests.get', return_value=mock_resp) as mock_get:
            service.is_pwned(password)

        called_url = mock_get.call_args[0][0]
        assert expected_prefix in called_url
        assert sha1[5:] not in called_url  # full hash suffix NOT sent


# ===========================================================================
# Integration: RegisterView + Breach Check
# ===========================================================================

@pytest.mark.django_db
class TestRegisterViewBreachCheck:

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_register_rejects_breached_password(self):
        app = _app("RegBreachApp")
        factory = APIRequestFactory()
        with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True), \
             patch.object(breach_check_service, 'check_password',
                   return_value=(False, 'This password has appeared in 5,000 data breaches.')):
            req = factory.post('/register/', {
                'email': 'newuser@example.com',
                'password': 'ValidP@ss123!',
                'first_name': 'Test',
                'last_name': 'User',
            }, format='json')
            req.application = app
            resp = RegisterView.as_view()(req)

        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.data}"
        assert resp.data.get('code') == 'PASSWORD_BREACHED', f"Unexpected data: {resp.data}"
        assert 'breaches' in resp.data.get('error', '').lower()

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_register_allows_safe_password(self):
        app = _app("RegSafeApp")
        factory = APIRequestFactory()
        with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True), \
             patch.object(breach_check_service, 'check_password', return_value=(True, '')), \
             patch('tenxyte.services.otp_service.OTPService.send_email_otp', return_value=True):
            req = factory.post('/register/', {
                'email': 'safeuser@example.com',
                'password': 'SafeP@ssw0rd!',
                'first_name': 'Safe',
                'last_name': 'User',
            }, format='json')
            req.application = app
            resp = RegisterView.as_view()(req)

        assert resp.status_code == 201

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=False)
    def test_register_skips_check_when_disabled(self):
        app = _app("RegDisabledApp")
        factory = APIRequestFactory()
        with patch('rest_framework.throttling.SimpleRateThrottle.allow_request', return_value=True), \
             patch.object(breach_check_service, 'check_password', return_value=(True, '')), \
             patch('tenxyte.services.otp_service.OTPService.send_email_otp', return_value=True):
            req = factory.post('/register/', {
                'email': 'nodisabled@example.com',
                'password': 'AnyPass123!',
                'first_name': 'No',
                'last_name': 'Check',
            }, format='json')
            req.application = app
            resp = RegisterView.as_view()(req)

        assert resp.status_code == 201


# ===========================================================================
# Integration: ChangePasswordView + Breach Check
# ===========================================================================

@pytest.mark.django_db
class TestChangePasswordViewBreachCheck:

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_change_password_rejects_breached_password(self):
        app = _app("ChgBreachApp")
        user = _user("chg_breach@example.com", "OldPass123!")
        token = _jwt(user, app)

        factory = APIRequestFactory()
        with patch.object(breach_check_service, 'check_password',
                   return_value=(False, 'This password has appeared in 3,000 data breaches.')):
            req = factory.post('/password/change/', {
                'current_password': 'OldPass123!',
                'new_password': 'ValidP@ss456!',
            }, format='json')
            req.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            req.application = app
            resp = ChangePasswordView.as_view()(req)

        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.data}"
        assert resp.data.get('code') == 'PASSWORD_BREACHED', f"Unexpected data: {resp.data}"

    @override_settings(TENXYTE_BREACH_CHECK_ENABLED=True, TENXYTE_BREACH_CHECK_REJECT=True)
    def test_change_password_allows_safe_password(self):
        app = _app("ChgSafeApp")
        user = _user("chg_safe@example.com", "OldPass123!")
        token = _jwt(user, app)

        factory = APIRequestFactory()
        with patch.object(breach_check_service, 'check_password', return_value=(True, '')):
            req = factory.post('/password/change/', {
                'current_password': 'OldPass123!',
                'new_password': 'NewSafeP@ss456!',
            }, format='json')
            req.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            req.application = app
            resp = ChangePasswordView.as_view()(req)

        assert resp.status_code == 200
        assert resp.data['message'] == 'Password changed successfully'
