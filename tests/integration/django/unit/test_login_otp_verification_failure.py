"""
Property-based test for Login OTP verification failure without authentication
effect.

Spec: .kiro/specs/passwordless-phone/

Property 4: Tout échec de vérification est signalé sans authentifier
    Pour tout `Login_OTP_Code` et tout code fourni qui ne correspond pas, ou
    pour tout code correct présenté après expiration ou après épuisement des
    tentatives autorisées, `verify_login_otp` retourne un échec avec un
    message descriptif, et aucun effet d'authentification n'a lieu (le code
    n'est pas marqué comme utilisé par un succès, aucun flag utilisateur
    n'est modifié).

Validates: Requirements 1.5
"""

import secrets as _secrets

import pytest
from datetime import timedelta
from django.utils import timezone
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st

from tenxyte.models import get_user_model
from tenxyte.services.otp_service import OTPService

User = get_user_model()


def _make_user(nonce: int):
    user = User.objects.create(
        email=f"login-otp-fail-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="Login",
        last_name="OTPFail",
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


def _user_flags(user):
    """Snapshot of user flags that verify_login_otp must never mutate."""
    user.refresh_from_db()
    return {
        "is_phone_verified": user.is_phone_verified,
        "is_email_verified": user.is_email_verified,
        "has_usable_password": user.has_usable_password,
        "is_active": user.is_active,
    }


@pytest.mark.django_db
class TestLoginOTPVerificationFailureWrongCode:
    """
    Validates: Requirements 1.5

    Pour tout code fourni qui ne correspond pas au code brut généré,
    verify_login_otp doit échouer avec un message descriptif, sans marquer
    le code comme utilisé et sans modifier aucun flag utilisateur.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        wrong_code=st.text(alphabet="0123456789", min_size=6, max_size=6),
    )
    def test_incorrect_code_fails_without_auth_effect(self, wrong_code):
        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce)
        otp_service = OTPService()

        otp, raw_code = otp_service.generate_login_otp(user)

        # Ensure the generated wrong_code genuinely differs from the real one.
        if wrong_code == raw_code:
            wrong_code = "0" if raw_code != "0" * 6 else "1" * 6

        before_flags = _user_flags(user)

        is_valid, error = otp_service.verify_login_otp(user, wrong_code)

        assert is_valid is False
        assert error != ""

        otp.refresh_from_db()
        assert otp.is_used is False

        after_flags = _user_flags(user)
        assert after_flags == before_flags


@pytest.mark.django_db
class TestLoginOTPVerificationFailureExpired:
    """
    Validates: Requirements 1.5

    Pour un Login_OTP_Code expiré, même le code correct doit échouer, sans
    marquer le code comme utilisé et sans modifier aucun flag utilisateur.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        expired_minutes_ago=st.integers(min_value=1, max_value=10000),
    )
    def test_expired_code_fails_even_when_correct(self, expired_minutes_ago):
        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce)
        otp_service = OTPService()

        otp, raw_code = otp_service.generate_login_otp(user)
        otp.expires_at = timezone.now() - timedelta(minutes=expired_minutes_ago)
        otp.save(update_fields=["expires_at"])

        before_flags = _user_flags(user)

        is_valid, error = otp_service.verify_login_otp(user, raw_code)

        assert is_valid is False
        assert error != ""

        otp.refresh_from_db()
        assert otp.is_used is False

        after_flags = _user_flags(user)
        assert after_flags == before_flags


@pytest.mark.django_db
class TestLoginOTPVerificationFailureMaxAttempts:
    """
    Validates: Requirements 1.5

    Pour un Login_OTP_Code dont les tentatives sont déjà épuisées, même le
    code correct doit échouer, sans marquer le code comme utilisé et sans
    modifier aucun flag utilisateur.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        extra_attempts=st.integers(min_value=0, max_value=5),
    )
    def test_exhausted_attempts_fails_even_when_correct(self, extra_attempts):
        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce)
        otp_service = OTPService()

        otp, raw_code = otp_service.generate_login_otp(user)
        otp.attempts = otp.max_attempts + extra_attempts
        otp.save(update_fields=["attempts"])

        before_flags = _user_flags(user)

        is_valid, error = otp_service.verify_login_otp(user, raw_code)

        assert is_valid is False
        assert error != ""

        otp.refresh_from_db()
        assert otp.is_used is False

        after_flags = _user_flags(user)
        assert after_flags == before_flags


@pytest.mark.django_db
class TestLoginOTPVerificationFailureConcreteExamples:
    """Exemples concrets complémentaires aux tests basés sur les propriétés."""

    @pytest.mark.django_db
    def test_no_code_generated_yet(self, user_with_phone):
        otp_service = OTPService()
        before_flags = _user_flags(user_with_phone)

        is_valid, error = otp_service.verify_login_otp(user_with_phone, "123456")

        assert is_valid is False
        assert error != ""
        assert _user_flags(user_with_phone) == before_flags

    @pytest.mark.django_db
    def test_wrong_code_then_correct_code_after_max_attempts_still_fails(self, user_with_phone):
        """
        Épuiser les tentatives avec des codes incorrects, puis présenter le
        bon code : la vérification doit échouer même si le code est correct,
        car les tentatives autorisées sont épuisées.
        """
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_login_otp(user_with_phone)

        for _ in range(otp.max_attempts):
            is_valid, _ = otp_service.verify_login_otp(user_with_phone, "000000")
            assert is_valid is False

        before_flags = _user_flags(user_with_phone)

        is_valid, error = otp_service.verify_login_otp(user_with_phone, raw_code)

        assert is_valid is False
        assert error != ""
        otp.refresh_from_db()
        assert otp.is_used is False
        assert _user_flags(user_with_phone) == before_flags
