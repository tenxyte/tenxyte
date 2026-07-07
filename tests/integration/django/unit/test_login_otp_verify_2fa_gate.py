"""
Property-based test for the 2FA gate on token issuance in
Login_OTP_Verify_View.

Spec: .kiro/specs/passwordless-phone/

Property 15: La porte 2FA n'émet un jeton que si le code TOTP est valide
    Pour tout compte avec un type de MFA différent de none, un
    Login_OTP_Code correct, et un statut de compte sain,
    Login_OTP_Verify_View n'émet un jeton que si un totp_code valide est
    fourni ; en l'absence de totp_code ou avec un totp_code invalide, la
    réponse est 401 (2FA_REQUIRED ou INVALID_2FA_CODE) et aucun jeton n'est
    émis.

Validates: Requirements 3.11, 3.12
"""

import secrets as _secrets
from unittest.mock import patch

import pyotp
import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, RefreshToken
from tenxyte.services.otp_service import OTPService
from tenxyte.views.login_otp_views import LoginOTPVerifyView

User = get_user_model()


def _make_user_with_mfa(nonce: int):
    """Crée un compte sain (actif, non banni, non verrouillé) avec un type
    de MFA différent de none (TOTP activé avec un secret valide)."""
    secret = pyotp.random_base32()
    user = User.objects.create(
        email=f"login-otp-2fa-gate-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="Login",
        last_name="TwoFAGate",
        is_active=True,
    )
    user.set_password("TestPassword123!")
    user.is_2fa_enabled = True
    user.totp_secret = secret
    user.save()
    return user, secret


def _post_login_otp_verify(phone_country_code: str, phone_number: str, otp_code: str, totp_code=None):
    factory = APIRequestFactory()
    data = {
        "phone_country_code": phone_country_code,
        "phone_number": phone_number,
        "otp_code": otp_code,
    }
    if totp_code is not None:
        data["totp_code"] = totp_code
    req = factory.post("/auth/login/otp/verify/", data=data, format="json")
    req.application = None
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        view = LoginOTPVerifyView.as_view()
        return view(req)


@pytest.mark.django_db
class TestLoginOTPVerify2FAGate:
    """
    Validates: Requirements 3.11, 3.12

    Pour tout compte avec un type de MFA différent de none, un
    Login_OTP_Code correct, et un statut de compte sain,
    Login_OTP_Verify_View ne doit émettre un jeton que si un totp_code
    valide est fourni. En l'absence de totp_code ou avec un totp_code
    invalide, la réponse doit être 401 (2FA_REQUIRED ou INVALID_2FA_CODE)
    et aucun jeton ne doit être émis.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(totp_case=st.sampled_from(["missing", "invalid", "valid"]))
    def test_2fa_gate_blocks_token_unless_valid_totp_code(self, totp_case):
        nonce = _secrets.randbelow(10**8)
        user, secret = _make_user_with_mfa(nonce)

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        refresh_token_count_before = RefreshToken.objects.count()

        if totp_case == "missing":
            resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

            assert resp.status_code == 401
            assert resp.data["code"] == "2FA_REQUIRED"
        elif totp_case == "invalid":
            valid_now = pyotp.TOTP(secret).now()
            wrong_totp_code = "000000" if valid_now != "000000" else "111111"

            resp = _post_login_otp_verify(
                user.phone_country_code, user.phone_number, raw_code, totp_code=wrong_totp_code
            )

            assert resp.status_code == 401
            assert resp.data["code"] == "INVALID_2FA_CODE"
        else:  # "valid"
            valid_totp_code = pyotp.TOTP(secret).now()

            resp = _post_login_otp_verify(
                user.phone_country_code, user.phone_number, raw_code, totp_code=valid_totp_code
            )

            assert resp.status_code == 200
            assert "access_token" in resp.data

        # No token is ever issued in the missing/invalid cases, and the
        # refresh token count only grows in the valid case.
        if totp_case in ("missing", "invalid"):
            assert "access_token" not in resp.data
            assert "refresh_token" not in resp.data
            assert RefreshToken.objects.count() == refresh_token_count_before
        else:
            assert RefreshToken.objects.count() == refresh_token_count_before + 1

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_example_missing_totp_code_returns_2fa_required(self):
        user, _secret = _make_user_with_mfa(_secrets.randbelow(10**8))

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 401
        assert resp.data["code"] == "2FA_REQUIRED"
        assert "access_token" not in resp.data

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_example_invalid_totp_code_returns_invalid_2fa_code(self):
        user, secret = _make_user_with_mfa(_secrets.randbelow(10**8))

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        valid_now = pyotp.TOTP(secret).now()
        wrong_totp_code = "000000" if valid_now != "000000" else "111111"

        resp = _post_login_otp_verify(
            user.phone_country_code, user.phone_number, raw_code, totp_code=wrong_totp_code
        )

        assert resp.status_code == 401
        assert resp.data["code"] == "INVALID_2FA_CODE"
        assert "access_token" not in resp.data

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_example_valid_totp_code_issues_token(self):
        user, secret = _make_user_with_mfa(_secrets.randbelow(10**8))

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        valid_totp_code = pyotp.TOTP(secret).now()

        resp = _post_login_otp_verify(
            user.phone_country_code, user.phone_number, raw_code, totp_code=valid_totp_code
        )

        assert resp.status_code == 200
        assert "access_token" in resp.data
        assert resp.data["requires_2fa"] is True
