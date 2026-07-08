"""
Property-based test for Login OTP generation invalidation.

Spec: .kiro/specs/passwordless-phone/

Property 1: Génération de Login OTP invalide les codes précédents
    Pour tout utilisateur, générer un nouveau `Login_OTP_Code` invalide (marque
    `is_used=True`) tout `Login_OTP_Code` non utilisé précédemment généré pour
    ce même utilisateur, et le nouveau code est utilisable.

Validates: Requirements 1.1
"""

import pytest
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st

from tenxyte.models import get_user_model, OTPCode
from tenxyte.services.otp_service import OTPService

User = get_user_model()


def _make_user(nonce: int):
    user = User.objects.create(
        email=f"login-otp-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="Login",
        last_name="OTP",
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


@pytest.mark.django_db
class TestLoginOTPGenerationInvalidation:
    """
    Validates: Requirements 1.1

    Pour tout utilisateur et tout nombre de générations précédentes, générer
    un nouveau Login_OTP_Code doit invalider (is_used=True) tous les
    Login_OTP_Code non utilisés précédemment générés pour ce même utilisateur,
    et le nouveau code doit rester utilisable (verify_login_otp réussit avec
    son code brut).
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(prior_generations=st.integers(min_value=1, max_value=10))
    def test_new_login_otp_invalidates_prior_unused_codes(self, prior_generations):
        """
        Pour un utilisateur avec N générations précédentes de login OTP, la
        génération d'un nouveau code invalide tous les codes précédents non
        utilisés et le nouveau code reste utilisable.
        """
        import secrets as _secrets

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce)
        otp_service = OTPService()

        previous_otps = []
        for _ in range(prior_generations):
            otp, _raw = otp_service.generate_login_otp(user)
            previous_otps.append(otp)

        new_otp, new_raw_code = otp_service.generate_login_otp(user)

        # All previously generated (now-prior) unused login OTP codes must be
        # invalidated (is_used=True).
        for prior_otp in previous_otps:
            prior_otp.refresh_from_db()
            assert prior_otp.is_used is True

        # Exactly one login OTP for this user remains unused: the new one.
        unused_login_otps = OTPCode.objects.filter(
            user=user, otp_type="login", is_used=False
        )
        assert unused_login_otps.count() == 1
        assert unused_login_otps.first().pk == new_otp.pk

        # The new code is usable: verify_login_otp succeeds with its raw code.
        is_valid, error = otp_service.verify_login_otp(user, new_raw_code)
        assert is_valid is True
        assert error == ""

    @pytest.mark.django_db
    def test_single_prior_code_invalidated_concrete_example(self, user):
        """
        Exemple concret : une seule génération précédente est invalidée par
        la génération suivante, et le nouveau code est utilisable.
        """
        otp_service = OTPService()

        first_otp, _first_raw = otp_service.generate_login_otp(user)
        second_otp, second_raw = otp_service.generate_login_otp(user)

        first_otp.refresh_from_db()
        assert first_otp.is_used is True
        assert second_otp.is_used is False

        is_valid, error = otp_service.verify_login_otp(user, second_raw)
        assert is_valid is True
        assert error == ""
