"""
Property-based test for the success response shape of Login_OTP_Verify_View
matching the success response shape of /login/phone/.

Spec: .kiro/specs/passwordless-phone/

Property 16: La réponse de succès a la même forme que `/login/phone/`
    Pour tout compte complétant intégralement le flux Login_OTP_Verify_View
    avec succès (code correct, statut sain, 2FA satisfaite si nécessaire),
    la réponse HTTP 200 contient exactement le même ensemble de clés et
    types que la réponse de succès de authenticate_by_phone_with_core
    (access_token, refresh_token, token_type, expires_in,
    refresh_expires_in, user, requires_2fa, session_id, device_id), et un
    nouvel enregistrement RefreshToken valide est persisté.

Validates: Requirements 3.13
"""

import secrets as _secrets
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, RefreshToken
from tenxyte.services.otp_service import OTPService
from tenxyte.views.auth_views import LoginPhoneView
from tenxyte.views.login_otp_views import LoginOTPVerifyView

User = get_user_model()

_TEST_PASSWORD = "TestPassword123!"

# Benign account attributes that must not affect the shape of the response.
_name_strategy = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=15
)
_device_info_strategy = st.one_of(
    st.just(""),
    st.sampled_from(
        [
            "v=1|os=windows;osv=11|device=desktop|arch=x64",
            "v=1|os=android;osv=14|device=mobile|arch=arm64",
            "v=1|os=ios;osv=17|device=mobile",
            "v=1|os=linux|device=server|arch=x64",
        ]
    ),
)


def _make_otp_account(nonce: int, first_name: str, last_name: str):
    """Compte sain destiné à se connecter via Login_OTP_Verify_View."""
    user = User.objects.create(
        email=f"login-otp-shape-otp-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name=first_name,
        last_name=last_name,
        is_active=True,
    )
    # A usable password is irrelevant to the OTP login path, but is set so
    # the account looks like a typical account (not a passwordless-only one).
    user.set_password(_TEST_PASSWORD)
    user.save()
    return user


def _make_phone_password_account(nonce: int, first_name: str, last_name: str):
    """Compte sain équivalent destiné à se connecter via /login/phone/."""
    user = User.objects.create(
        email=f"login-otp-shape-phone-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"7{nonce:08d}",
        first_name=first_name,
        last_name=last_name,
        is_active=True,
    )
    user.set_password(_TEST_PASSWORD)
    user.save()
    return user


def _post_login_otp_verify(phone_country_code: str, phone_number: str, otp_code: str, device_info: str = ""):
    factory = APIRequestFactory()
    data = {
        "phone_country_code": phone_country_code,
        "phone_number": phone_number,
        "otp_code": otp_code,
    }
    if device_info:
        data["device_info"] = device_info
    req = factory.post("/auth/login/otp/verify/", data=data, format="json")
    req.application = None
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginOTPVerifyView.as_view()(req)


def _post_login_phone(phone_country_code: str, phone_number: str, password: str, device_info: str = ""):
    factory = APIRequestFactory()
    data = {
        "phone_country_code": phone_country_code,
        "phone_number": phone_number,
        "password": password,
    }
    if device_info:
        data["device_info"] = device_info
    req = factory.post("/auth/login/phone/", data=data, format="json")
    req.application = None
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginPhoneView.as_view()(req)


@pytest.mark.django_db
class TestLoginOTPVerifyResponseShapeMatchesLoginPhone:
    """
    Validates: Requirements 3.13

    Pour tout compte complétant intégralement le flux
    Login_OTP_Verify_View avec succès, la réponse HTTP 200 contient
    exactement le même ensemble de clés et types que la réponse de succès
    de /login/phone/ pour un compte équivalent, et un nouvel enregistrement
    RefreshToken valide est persisté.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        first_name=_name_strategy,
        last_name=_name_strategy,
        device_info=_device_info_strategy,
    )
    def test_success_response_shape_matches_login_phone(self, first_name, last_name, device_info):
        nonce = _secrets.randbelow(10**8)

        otp_user = _make_otp_account(nonce, first_name, last_name)
        phone_user = _make_phone_password_account(nonce, first_name, last_name)

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(otp_user)

        otp_user_refresh_token_count_before = RefreshToken.objects.filter(user_id=otp_user.id).count()

        resp_otp = _post_login_otp_verify(
            otp_user.phone_country_code, otp_user.phone_number, raw_code, device_info
        )
        resp_phone = _post_login_phone(
            phone_user.phone_country_code, phone_user.phone_number, _TEST_PASSWORD, device_info
        )

        # Sanity check: both are indeed successful token-issuing responses.
        assert resp_otp.status_code == 200
        assert resp_phone.status_code == 200

        otp_keys = set(resp_otp.data.keys())
        phone_keys = set(resp_phone.data.keys())
        assert otp_keys == phone_keys

        for key in phone_keys:
            assert type(resp_otp.data[key]) is type(resp_phone.data[key]), (
                f"Type mismatch for key '{key}': "
                f"{type(resp_otp.data[key])!r} != {type(resp_phone.data[key])!r}"
            )

        # A new, valid RefreshToken record was persisted for the OTP login.
        assert (
            RefreshToken.objects.filter(user_id=otp_user.id).count()
            == otp_user_refresh_token_count_before + 1
        )
        new_refresh_token = RefreshToken.objects.filter(user_id=otp_user.id).latest("created_at")
        assert new_refresh_token.is_revoked is False
        assert new_refresh_token.expires_at is not None

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_example_response_shape_matches_login_phone(self):
        nonce = _secrets.randbelow(10**8)

        otp_user = _make_otp_account(nonce, "Alice", "Example")
        phone_user = _make_phone_password_account(nonce, "Alice", "Example")

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(otp_user)

        otp_user_refresh_token_count_before = RefreshToken.objects.filter(user_id=otp_user.id).count()

        resp_otp = _post_login_otp_verify(otp_user.phone_country_code, otp_user.phone_number, raw_code)
        resp_phone = _post_login_phone(phone_user.phone_country_code, phone_user.phone_number, _TEST_PASSWORD)

        assert resp_otp.status_code == 200
        assert resp_phone.status_code == 200

        expected_keys = {
            "access_token",
            "refresh_token",
            "token_type",
            "expires_in",
            "refresh_expires_in",
            "user",
            "requires_2fa",
            "session_id",
            "device_id",
        }
        assert expected_keys.issubset(resp_otp.data.keys())
        assert set(resp_otp.data.keys()) == set(resp_phone.data.keys())

        for key in resp_phone.data.keys():
            assert type(resp_otp.data[key]) is type(resp_phone.data[key])

        assert (
            RefreshToken.objects.filter(user_id=otp_user.id).count()
            == otp_user_refresh_token_count_before + 1
        )
