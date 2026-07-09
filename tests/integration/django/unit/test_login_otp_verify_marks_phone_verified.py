"""
Property-based test for Login_OTP_Verify_View marking the phone as verified
on a successful login.

Spec: .kiro/specs/passwordless-phone/

Property 14: Le login OTP réussi marque le téléphone comme vérifié
    Pour tout compte, avec `is_phone_verified` initialement vrai ou faux,
    une vérification de `Login_OTP_Code` réussie (code correct, statut de
    compte sain, 2FA satisfaite si requise) laisse le compte avec
    `is_phone_verified=True`.

Validates: Requirements 3.10
"""

import secrets as _secrets
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model
from tenxyte.services.otp_service import OTPService
from tenxyte.views.login_otp_views import LoginOTPVerifyView

User = get_user_model()


def _make_user(nonce: int, is_phone_verified: bool, is_email_verified: bool, has_usable_password: bool):
    """Crée un compte sain (actif, non banni, non verrouillé, MFA
    désactivée) avec un couple (phone_country_code, phone_number) unique
    dérivé du nonce, et des attributs initiaux qui ne doivent pas affecter
    le résultat de la vérification."""
    user = User.objects.create(
        email=f"login-otp-verify-mark-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="Login",
        last_name="OTPMark",
        is_phone_verified=is_phone_verified,
        is_email_verified=is_email_verified,
        is_active=True,
    )
    user.set_password("TestPassword123!")
    user.has_usable_password = has_usable_password
    user.save()
    return user


def _post_login_otp_verify(phone_country_code: str, phone_number: str, otp_code: str):
    """POST to LoginOTPVerifyView directly (no URL routing needed)."""
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
        view = LoginOTPVerifyView.as_view()
        return view(req)


@pytest.mark.django_db
class TestLoginOTPVerifySuccessMarksPhoneVerified:
    """
    Validates: Requirements 3.10

    Pour tout compte, quelle que soit la valeur initiale de
    is_phone_verified (et d'autres attributs sans effet sur le résultat,
    comme is_email_verified ou has_usable_password), une vérification de
    Login_OTP_Code réussie (code correct, statut de compte sain, aucune
    2FA requise) doit laisser le compte avec is_phone_verified=True.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        initial_is_phone_verified=st.booleans(),
        initial_is_email_verified=st.booleans(),
        initial_has_usable_password=st.booleans(),
    )
    def test_successful_verification_leaves_phone_verified_true(
        self, initial_is_phone_verified, initial_is_email_verified, initial_has_usable_password
    ):
        """
        Quelle que soit la valeur initiale de is_phone_verified (et des
        autres attributs non pertinents), une vérification réussie du
        Login_OTP_Code laisse le compte avec is_phone_verified=True.
        """
        nonce = _secrets.randbelow(10**8)
        user = _make_user(
            nonce,
            initial_is_phone_verified,
            initial_is_email_verified,
            initial_has_usable_password,
        )

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        # Sanity check: this is indeed the success path (healthy account,
        # correct code, no MFA required), so a token pair is issued.
        assert resp.status_code == 200
        assert "access_token" in resp.data

        user.refresh_from_db()
        assert user.is_phone_verified is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_example_starting_unverified(self, user_with_phone):
        """
        Exemple concret : un compte dont is_phone_verified vaut initialement
        False se retrouve avec is_phone_verified=True après une vérification
        réussie."""
        assert user_with_phone.is_phone_verified is False

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user_with_phone)

        resp = _post_login_otp_verify(
            user_with_phone.phone_country_code, user_with_phone.phone_number, raw_code
        )

        assert resp.status_code == 200
        user_with_phone.refresh_from_db()
        assert user_with_phone.is_phone_verified is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_example_starting_already_verified(self):
        """
        Exemple concret : un compte dont is_phone_verified vaut déjà True
        reste True après une vérification réussie (idempotence)."""
        user = _make_user(_secrets.randbelow(10**8), True, False, True)

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.is_phone_verified is True
