"""
Property-based test for anti-enumeration on Login_OTP_Verify_View's
response when no account matches the requested phone, versus an existing
account receiving an incorrect code.

Spec: .kiro/specs/passwordless-phone/

Property 12: Anti-énumération sur la vérification — réponse générique
identique
    Pour tout couple téléphone ne correspondant à aucun compte non supprimé,
    et pour tout compte existant recevant un code incorrect,
    Login_OTP_Verify_View répond avec le même code HTTP 401 et la même forme
    de corps (code: "OTP_INVALID"), et n'émet aucun jeton dans les deux cas.

Validates: Requirements 3.4, 3.6
"""

import itertools
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model
from tenxyte.services.otp_service import OTPService
from tenxyte.views.login_otp_views import LoginOTPVerifyView

User = get_user_model()

# Monotonic counter guaranteeing that every generated phone number/OTP code
# is unique across Hypothesis examples within a single test invocation, so
# no example accidentally collides with a previously created (or
# pre-existing) user/code.
_nonce_counter = itertools.count()


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
    req.application = None
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginOTPVerifyView.as_view()(req)


def _make_user(nonce: int):
    user = User.objects.create(
        email=f"login-otp-verify-antienum-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"7{nonce:08d}",
        first_name="Verify",
        last_name="AntiEnum",
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


@pytest.mark.django_db
class TestLoginOTPVerifyAntiEnumeration:
    """
    Validates: Requirements 3.4, 3.6

    Pour tout couple (phone_country_code, phone_number) ne correspondant à
    aucun utilisateur non supprimé, la réponse de Login_OTP_Verify_View doit
    être strictement identique (code HTTP 401, même clés de corps, même
    valeur "code": "OTP_INVALID") à la réponse obtenue pour un compte
    existant recevant un code incorrect. Aucun jeton n'est émis dans les
    deux cas.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        country_code_digits=st.text(alphabet="0123456789", min_size=1, max_size=4),
        phone_prefix=st.text(alphabet="0123456789", min_size=3, max_size=8),
        wrong_code=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    @override_settings(
        TENXYTE_OTP_LOGIN_ENABLED=True,
        TENXYTE_APPLICATION_AUTH_ENABLED=False,
    )
    def test_nonexistent_account_matches_existing_account_wrong_code_shape(
        self, country_code_digits, phone_prefix, wrong_code
    ):
        nonce = next(_nonce_counter)

        # --- Case A: no non-deleted account exists for this phone. ---
        nonexistent_phone_country_code = country_code_digits
        nonexistent_phone_number = f"{phone_prefix}{nonce:08d}"[:20]

        assert not User.objects.filter(
            phone_country_code=nonexistent_phone_country_code,
            phone_number=nonexistent_phone_number,
            is_deleted=False,
        ).exists()

        resp_nonexistent = _post_login_otp_verify(
            nonexistent_phone_country_code, nonexistent_phone_number, wrong_code
        )

        # --- Case B: an existing account receives an incorrect code. ---
        user = _make_user(nonce)
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        actual_wrong_code = wrong_code
        if actual_wrong_code == raw_code:
            actual_wrong_code = "0" * 6 if raw_code != "0" * 6 else "1" * 6

        resp_existing_wrong_code = _post_login_otp_verify(
            user.phone_country_code, user.phone_number, actual_wrong_code
        )

        # Both responses share the exact same HTTP status and body shape.
        assert resp_nonexistent.status_code == 401
        assert resp_existing_wrong_code.status_code == 401
        assert resp_nonexistent.status_code == resp_existing_wrong_code.status_code

        assert set(resp_nonexistent.data.keys()) == {"error", "code"}
        assert set(resp_existing_wrong_code.data.keys()) == {"error", "code"}
        assert resp_nonexistent.data.keys() == resp_existing_wrong_code.data.keys()

        assert resp_nonexistent.data["code"] == "OTP_INVALID"
        assert resp_existing_wrong_code.data["code"] == "OTP_INVALID"

        # No token is ever issued in either response.
        for resp in (resp_nonexistent, resp_existing_wrong_code):
            assert "access_token" not in resp.data
            assert "refresh_token" not in resp.data

    @pytest.mark.django_db
    @override_settings(
        TENXYTE_OTP_LOGIN_ENABLED=True,
        TENXYTE_APPLICATION_AUTH_ENABLED=False,
    )
    def test_concrete_example_nonexistent_vs_wrong_code(self):
        """
        Exemple concret : un téléphone n'existant pas et un compte existant
        recevant un code incorrect renvoient exactement la même réponse
        (401, {"error": ..., "code": "OTP_INVALID"}), sans jeton émis.
        """
        resp_nonexistent = _post_login_otp_verify("33", "600000001", "123456")

        user = User.objects.create(
            email="verify-antienum-concrete@example.com",
            phone_country_code="33",
            phone_number="600000002",
            first_name="Concrete",
            last_name="AntiEnum",
        )
        user.set_password("TestPassword123!")
        user.save()

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)
        wrong_code = "000000" if raw_code != "000000" else "111111"

        resp_existing_wrong_code = _post_login_otp_verify("33", "600000002", wrong_code)

        assert resp_nonexistent.status_code == 401
        assert resp_existing_wrong_code.status_code == 401
        assert set(resp_nonexistent.data.keys()) == {"error", "code"}
        assert set(resp_existing_wrong_code.data.keys()) == {"error", "code"}
        assert resp_nonexistent.data["code"] == "OTP_INVALID"
        assert resp_existing_wrong_code.data["code"] == "OTP_INVALID"
        assert "access_token" not in resp_nonexistent.data
        assert "access_token" not in resp_existing_wrong_code.data
