"""
Property-based test for the configured Login OTP validity duration.

Spec: .kiro/specs/passwordless-phone/

Property 2: La durée de validité suit le réglage configuré
    Pour toute valeur configurée de `TENXYTE_OTP_LOGIN_VALIDITY_MINUTES` et
    tout utilisateur, le `Login_OTP_Code` généré a `expires_at` égal à
    `created_at` + la durée configurée (à la seconde près).

Validates: Requirements 1.2
"""

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st

from tenxyte.models import get_user_model
from tenxyte.services.otp_service import OTPService

User = get_user_model()


def _make_user(nonce: int):
    user = User.objects.create(
        email=f"login-otp-validity-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"7{nonce:08d}",
        first_name="Login",
        last_name="Validity",
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


@pytest.mark.django_db
class TestLoginOTPConfiguredValidityDuration:
    """
    Validates: Requirements 1.2

    Pour toute valeur configurée de TENXYTE_OTP_LOGIN_VALIDITY_MINUTES et
    tout utilisateur, le Login_OTP_Code généré doit avoir expires_at égal à
    created_at + la durée configurée, à la seconde près.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(validity_minutes=st.integers(min_value=1, max_value=120))
    def test_expires_at_matches_configured_validity_minutes(self, validity_minutes):
        """
        Pour une valeur arbitraire de TENXYTE_OTP_LOGIN_VALIDITY_MINUTES,
        le Login_OTP_Code généré a expires_at == created_at + validity_minutes
        (à la seconde près).
        """
        import secrets as _secrets

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce)
        otp_service = OTPService()

        with override_settings(TENXYTE_OTP_LOGIN_VALIDITY_MINUTES=validity_minutes):
            otp, _raw_code = otp_service.generate_login_otp(user)

        expected_delta_seconds = validity_minutes * 60
        actual_delta_seconds = (otp.expires_at - otp.created_at).total_seconds()

        assert round(actual_delta_seconds) == expected_delta_seconds

    @pytest.mark.django_db
    def test_default_validity_minutes_concrete_example(self, user):
        """
        Exemple concret : avec le réglage par défaut (10 minutes), le
        Login_OTP_Code généré expire 10 minutes après sa création.
        """
        otp_service = OTPService()

        with override_settings(TENXYTE_OTP_LOGIN_VALIDITY_MINUTES=10):
            otp, _raw_code = otp_service.generate_login_otp(user)

        actual_delta_seconds = (otp.expires_at - otp.created_at).total_seconds()
        assert round(actual_delta_seconds) == 10 * 60
