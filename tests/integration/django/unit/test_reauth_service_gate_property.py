"""
Property-based test for the reauthentication gate.

Spec: .kiro/specs/passwordless-phone/

Property 17: Porte de réauthentification des actions sensibles
    Pour tout compte (passwordless ou non), ReauthService.verify accepte soit
    le mot de passe actuel correct, soit un Login_OTP_Code frais et valide,
    comme preuve d'identité, indépendamment de has_usable_password ; si
    aucune preuve valide n'est fournie, l'appel échoue avec REAUTH_REQUIRED.

Validates: Requirements 6.4, 6.5
"""

import pytest
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st

from tenxyte.models import get_user_model
from tenxyte.services.otp_service import OTPService
from tenxyte.services.reauth_service import ReauthService

User = get_user_model()

CORRECT_PASSWORD = "TestPassword123!"


def _make_user(nonce: int, has_usable_password: bool):
    """Crée un utilisateur avec téléphone, mot de passe connu, et le flag
    has_usable_password demandé (Passwordless_Account ou compte classique)."""
    user = User.objects.create(
        email=f"reauth-gate-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="Reauth",
        last_name="Gate",
    )
    user.set_password(CORRECT_PASSWORD)
    user.has_usable_password = has_usable_password
    user.save()
    return user


@pytest.mark.django_db
class TestReauthServiceGateProperty:
    """
    Validates: Requirements 6.4, 6.5

    Property 17: pour tout compte (passwordless ou non), ReauthService.verify
    accepte le mot de passe correct OU un Login_OTP_Code frais valide,
    indépendamment de has_usable_password ; sans aucune preuve valide,
    l'appel échoue avec REAUTH_REQUIRED.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(has_usable_password=st.booleans())
    def test_valid_otp_succeeds_regardless_of_has_usable_password(self, has_usable_password):
        """
        Un Login_OTP_Code frais et valide est accepté comme preuve d'identité
        que le compte soit passwordless (has_usable_password=False) ou non
        (has_usable_password=True).
        """
        import secrets as _secrets

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password)
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)
        service = ReauthService(otp_service=otp_service)

        success, error_code, error_message = service.verify(user, otp_code=raw_code)

        assert success is True
        assert error_code == ""
        assert error_message == ""

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(has_usable_password=st.booleans())
    def test_correct_password_succeeds_regardless_of_has_usable_password(self, has_usable_password):
        """
        Le mot de passe actuel correct est accepté comme preuve d'identité
        que le compte soit passwordless ou non (même si has_usable_password
        est False, ReauthService.verify ne consulte pas ce flag: c'est la
        garde en amont, câblée dans les vues, qui restreint l'usage du mot de
        passe pour un Passwordless_Account).
        """
        import secrets as _secrets

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password)
        service = ReauthService()

        success, error_code, error_message = service.verify(user, password=CORRECT_PASSWORD)

        assert success is True
        assert error_code == ""
        assert error_message == ""

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        has_usable_password=st.booleans(),
        wrong_otp_code=st.text(alphabet="0123456789", min_size=1, max_size=6),
    )
    def test_no_proof_at_all_fails_with_reauth_required(self, has_usable_password, wrong_otp_code):
        """
        Sans aucune preuve fournie (ni password, ni otp_code), l'appel échoue
        toujours avec REAUTH_REQUIRED, indépendamment de has_usable_password.
        """
        import secrets as _secrets

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password)
        service = ReauthService()

        success, error_code, error_message = service.verify(user)

        assert success is False
        assert error_code == "REAUTH_REQUIRED"
        assert error_message

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        has_usable_password=st.booleans(),
        wrong_password=st.text(min_size=1, max_size=20).filter(lambda s: s != CORRECT_PASSWORD),
    )
    def test_password_precedence_wrong_password_ignores_valid_otp(self, has_usable_password, wrong_password):
        """
        Reflète la logique réelle de verify(): le mot de passe est vérifié en
        priorité s'il est non vide. Un mot de passe incorrect fait échouer
        l'appel avec INVALID_PASSWORD même si un otp_code valide est fourni
        en même temps (le code n'est consulté que si password est vide).
        """
        import secrets as _secrets

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password)
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)
        service = ReauthService(otp_service=otp_service)

        success, error_code, error_message = service.verify(
            user, password=wrong_password, otp_code=raw_code
        )

        assert success is False
        assert error_code == "INVALID_PASSWORD"
        assert error_message

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        has_usable_password=st.booleans(),
        wrong_otp_code=st.text(alphabet="0123456789", min_size=1, max_size=6),
    )
    def test_empty_password_invalid_otp_fails_with_otp_invalid(self, has_usable_password, wrong_otp_code):
        """
        Si password est vide et qu'un otp_code non vide mais invalide est
        fourni, l'appel échoue avec OTP_INVALID (pas REAUTH_REQUIRED), ce qui
        reflète la précédence réelle: otp_code n'est consulté que si password
        est vide, et un otp_code non vide déclenche toujours une vérification
        OTP plutôt qu'un REAUTH_REQUIRED générique.
        """
        import secrets as _secrets

        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password)
        otp_service = OTPService()
        # Générer un code valide pour s'assurer que wrong_otp_code (aléatoire)
        # n'est presque sûrement pas le bon code, sans dépendre de collision.
        otp_service.generate_login_otp(user)
        service = ReauthService(otp_service=otp_service)

        success, error_code, error_message = service.verify(
            user, password="", otp_code=wrong_otp_code
        )

        # Le code fourni est extrêmement improbable d'être le bon (l'espace
        # des codes OTP réels est bien plus grand/complexe que ce texte
        # numérique arbitraire), donc la vérification OTP doit échouer.
        assert success is False
        assert error_code == "OTP_INVALID"
        assert error_message
