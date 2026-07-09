"""
Property-based test for ReauthService's backward-compatible current-password
path (task 11.3).

Spec: .kiro/specs/passwordless-phone/

Property 18: Compatibilité ascendante du mot de passe actuel
    Pour tout compte, quelle que soit la valeur de has_usable_password,
    appeler ReauthService.verify(user, password=<mot de passe actuel
    correct>) réussit (True, "", "") exactement comme le ferait
    user.check_password() aujourd'hui, et un mot de passe incorrect échoue
    avec INVALID_PASSWORD. Le chemin mot de passe ne doit jamais consulter
    OTPService, même si un otp_code est fourni en plus.

Validates: Requirements 6.6, 8.4
"""

import secrets as _secrets

import pytest
from hypothesis import HealthCheck, given, settings as hyp_settings, strategies as st

from tenxyte.models import get_user_model
from tenxyte.services.reauth_service import ReauthService

User = get_user_model()

# Printable, non-space ASCII characters make for realistic-ish passwords
# without needing to worry about hashing/encoding edge cases.
_password_chars = st.characters(min_codepoint=33, max_codepoint=126)


def _make_user(nonce: int, has_usable_password: bool, password: str):
    """Crée un compte avec un mot de passe donné et une valeur de
    has_usable_password arbitraire (qui ne doit pas influencer le chemin
    mot de passe de ReauthService)."""
    user = User.objects.create(
        email=f"reauth-backward-compat-{nonce}@example.com",
        first_name="Reauth",
        last_name="BackwardCompat",
        is_active=True,
    )
    user.set_password(password)
    user.has_usable_password = has_usable_password
    user.save()
    return user


class _ExplodingOTPService:
    """Stand-in OTPService that fails the test if ever consulted.

    Used to prove that ReauthService.verify's current-password path
    returns before ever touching OTP logic, per Requirements 6.6 and 8.4.
    """

    def verify_login_otp(self, user, code):
        raise AssertionError(
            "OTPService.verify_login_otp must not be called when a password "
            "is supplied to ReauthService.verify (password path must return "
            "before consulting otp_code)"
        )


@pytest.mark.django_db
class TestReauthServiceBackwardCompatibleCurrentPassword:
    """
    Property 18: Compatibilité ascendante du mot de passe actuel

    Validates: Requirements 6.6, 8.4
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        correct_password=st.text(alphabet=_password_chars, min_size=8, max_size=32),
        wrong_suffix=st.text(alphabet=_password_chars, min_size=1, max_size=8),
        has_usable_password=st.booleans(),
    )
    def test_current_password_path_matches_check_password(
        self, correct_password, wrong_suffix, has_usable_password
    ):
        """
        Pour tout compte (has_usable_password vrai ou faux) et tout mot de
        passe généré :
        - le mot de passe correct réussit exactement comme check_password
          le ferait aujourd'hui, sans jamais consulter OTPService, même si
          un otp_code est fourni ;
        - un mot de passe incorrect échoue avec INVALID_PASSWORD, là aussi
          sans jamais consulter OTPService.
        """
        nonce = _secrets.randbelow(10**9)
        user = _make_user(nonce, has_usable_password, correct_password)

        service = ReauthService(otp_service=_ExplodingOTPService())

        # Sanity: matches Django's own check_password behaviour first.
        assert user.check_password(correct_password) is True

        # Correct current password succeeds exactly as check_password does
        # today, regardless of has_usable_password, and never touches OTP
        # logic even though a (bogus) otp_code is also supplied.
        success, error_code, error_message = service.verify(
            user, password=correct_password, otp_code="000000"
        )
        assert success is True
        assert error_code == ""
        assert error_message == ""

        # An incorrect current password is guaranteed different from the
        # correct one because wrong_suffix has min_size=1.
        wrong_password = correct_password + wrong_suffix
        assert user.check_password(wrong_password) is False

        success, error_code, error_message = service.verify(
            user, password=wrong_password, otp_code="000000"
        )
        assert success is False
        assert error_code == "INVALID_PASSWORD"
        assert error_message
