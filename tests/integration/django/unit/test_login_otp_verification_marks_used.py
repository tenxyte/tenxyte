"""
Property-based test for successful Login OTP verification marking the code
as used.

Spec: .kiro/specs/passwordless-phone/

Property 3: Une vérification correcte marque le code comme utilisé et réussit
    Pour tout `Login_OTP_Code` fraîchement généré et son code brut correct,
    `verify_login_otp` retourne succès et le code est marqué `is_used=True` ;
    une vérification ultérieure avec le même code échoue toujours.

Validates: Requirements 1.4
"""

import pytest
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st

from tenxyte.models import get_user_model
from tenxyte.services.otp_service import OTPService

User = get_user_model()


def _make_user(nonce: int):
    user = User.objects.create(
        email=f"login-otp-verify-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"7{nonce:08d}",
        first_name="Login",
        last_name="OTPVerify",
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


@pytest.mark.django_db
class TestLoginOTPVerificationMarksUsed:
    """
    Validates: Requirements 1.4

    Pour tout Login_OTP_Code fraîchement généré et son code brut correct,
    verify_login_otp doit retourner succès et marquer le code is_used=True ;
    une vérification ultérieure avec le même code brut doit toujours échouer.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(nonce=st.integers(min_value=0, max_value=10**8 - 1))
    def test_correct_verification_marks_used_and_subsequent_verification_fails(self, nonce):
        """
        Une vérification correcte réussit et marque le code comme utilisé ;
        une seconde vérification avec le même code brut échoue toujours.
        """
        user = _make_user(nonce)
        otp_service = OTPService()

        otp, raw_code = otp_service.generate_login_otp(user)
        assert otp.is_used is False

        is_valid, error = otp_service.verify_login_otp(user, raw_code)

        assert is_valid is True
        assert error == ""

        otp.refresh_from_db()
        assert otp.is_used is True

        # A subsequent verification with the same raw code always fails,
        # since the OTP has been consumed (is_used=True), so no unused
        # login OTP is found for this user anymore.
        is_valid_again, error_again = otp_service.verify_login_otp(user, raw_code)

        assert is_valid_again is False
        assert error_again != ""

    @pytest.mark.django_db
    def test_verification_marks_used_concrete_example(self, user):
        """
        Exemple concret : la vérification réussie marque is_used=True et une
        vérification ultérieure avec le même code échoue.
        """
        otp_service = OTPService()

        otp, raw_code = otp_service.generate_login_otp(user)

        is_valid, error = otp_service.verify_login_otp(user, raw_code)
        assert is_valid is True
        assert error == ""

        otp.refresh_from_db()
        assert otp.is_used is True

        is_valid_again, error_again = otp_service.verify_login_otp(user, raw_code)
        assert is_valid_again is False
        assert error_again != ""
