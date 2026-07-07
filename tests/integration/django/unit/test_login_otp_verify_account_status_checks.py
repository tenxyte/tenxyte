"""
Property-based test for Account_Status_Checks blocking token issuance in
Login_OTP_Verify_View with the expected HTTP status codes.

Spec: .kiro/specs/passwordless-phone/

Property 13: Les contrôles de statut de compte bloquent l'émission de jeton
avec le code HTTP attendu
    Pour tout compte dont le statut correspond à une combinaison de
    Account_Status_Checks en échec (banni, inactif, ou verrouillé) et un
    code OTP par ailleurs correct, Login_OTP_Verify_View répond 423 si le
    compte est verrouillé ou 401 pour toute autre raison d'échec, et
    n'émet aucun jeton dans tous les cas.

Validates: Requirements 3.8, 3.9
"""

import secrets as _secrets
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, RefreshToken
from tenxyte.services.otp_service import OTPService
from tenxyte.views.login_otp_views import LoginOTPVerifyView

User = get_user_model()


def _make_user(nonce: int):
    user = User.objects.create(
        email=f"login-otp-status-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="Login",
        last_name="Status",
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


def _post_login_otp_verify(phone_country_code: str, phone_number: str, otp_code: str):
    factory = APIRequestFactory()
    req = factory.post(
        "/auth/login/otp/verify/",
        data={
            "phone_country_code": phone_country_code,
            "phone_number": phone_number,
            "otp_code": otp_code,
        },
        format="json",
    )
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        view = LoginOTPVerifyView.as_view()
        return view(req)


# Any non-empty combination of failing Account_Status_Checks: locked,
# banned, and/or inactive. At least one flag is True.
_status_combo = st.tuples(st.booleans(), st.booleans(), st.booleans()).filter(any)


@pytest.mark.django_db
class TestLoginOTPVerifyAccountStatusChecksBlockTokenIssuance:
    """
    Validates: Requirements 3.8, 3.9

    Pour tout compte dont le statut correspond à une combinaison de
    Account_Status_Checks en échec (banni, inactif, ou verrouillé) et un
    code OTP par ailleurs correct, Login_OTP_Verify_View doit répondre 423
    si le compte est verrouillé, ou 401 pour toute autre raison d'échec, et
    ne doit émettre aucun jeton dans tous les cas.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(status_combo=_status_combo)
    def test_failing_status_checks_block_tokens_with_expected_code(self, status_combo):
        is_locked, is_banned, is_inactive = status_combo

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce)

        if is_locked:
            user.lock_account(30)
        if is_banned:
            user.is_banned = True
            user.save(update_fields=["is_banned"])
        if is_inactive:
            user.is_active = False
            user.save(update_fields=["is_active"])

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        refresh_token_count_before = RefreshToken.objects.count()

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        # Account_Status_Checks priority (identical to authenticate_by_phone_with_core):
        # locked takes precedence and yields 423; any other failing check
        # (banned, then inactive) yields 401.
        if is_locked:
            expected_status = 423
        else:
            expected_status = 401
        assert resp.status_code == expected_status

        # No token is ever issued in any failing combination.
        assert "access_token" not in resp.data
        assert "refresh_token" not in resp.data
        assert RefreshToken.objects.count() == refresh_token_count_before

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_locked_account_concrete_example(self):
        user = _make_user(_secrets.randbelow(10**8))
        user.lock_account(30)

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 423
        assert resp.data["code"] == "ACCOUNT_LOCKED"
        assert "access_token" not in resp.data

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_banned_account_concrete_example(self):
        user = _make_user(_secrets.randbelow(10**8))
        user.is_banned = True
        user.save(update_fields=["is_banned"])

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 401
        assert resp.data["code"] == "ACCOUNT_BANNED"
        assert "access_token" not in resp.data

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_inactive_account_concrete_example(self):
        user = _make_user(_secrets.randbelow(10**8))
        user.is_active = False
        user.save(update_fields=["is_active"])

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 401
        assert resp.data["code"] == "ACCOUNT_INACTIVE"
        assert "access_token" not in resp.data
