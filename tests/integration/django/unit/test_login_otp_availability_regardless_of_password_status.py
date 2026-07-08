"""
Property-based test for OTP login availability regardless of initial-password status.

Spec: .kiro/specs/passwordless-phone/

Property 20: L'authentification OTP reste disponible indépendamment de la définition d'un mot de passe
    Pour tout compte utilisateur, que has_usable_password soit True ou False, un
    Login_OTP_Code valide peut être utilisé pour s'authentifier via
    Login_OTP_Verify_View et recevoir une réponse de succès (HTTP 200 avec des
    jetons). Le flux de connexion OTP ne dépend pas du flag has_usable_password
    et ne le consulte pas.

Validates: Requirements 7.2
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


def _make_user(nonce: int, has_usable_password: bool):
    """Crée un compte sain (actif, non banni, non verrouillé, MFA désactivée)
    avec le flag has_usable_password demandé.

    - has_usable_password=True  : compte classique avec mot de passe défini.
    - has_usable_password=False : Passwordless_Account (mot de passe aléatoire
      inutilisable, comme après auto-registration via Login_OTP_Request_View).
    """
    user = User.objects.create(
        email=f"otp-avail-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="OTPAvail",
        last_name="Test",
        is_active=True,
    )
    user.set_password("RandomStoredP@ss123!")
    user.has_usable_password = has_usable_password
    user.save()
    return user


def _post_login_otp_verify(phone_country_code: str, phone_number: str, otp_code: str):
    """POST directement à LoginOTPVerifyView (sans routing URL)."""
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
class TestLoginOTPAvailabilityRegardlessOfPasswordStatus:
    """
    Validates: Requirements 7.2

    Property 20: pour tout compte utilisateur, que has_usable_password soit True
    ou False, un Login_OTP_Code valide peut être utilisé pour s'authentifier via
    Login_OTP_Verify_View et recevoir une réponse de succès HTTP 200 avec des
    jetons. Le flux de connexion OTP ignore totalement le flag has_usable_password.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(has_usable_password=st.booleans())
    def test_valid_otp_login_succeeds_regardless_of_has_usable_password(self, has_usable_password):
        """
        Pour tout compte (passwordless ou avec mot de passe), un Login_OTP_Code
        valide permet de s'authentifier via Login_OTP_Verify_View et de recevoir
        une réponse HTTP 200 avec access_token et refresh_token.

        Le flag has_usable_password n'affecte pas la disponibilité du flux OTP.
        """
        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password)

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 200, (
            f"Expected HTTP 200 for has_usable_password={has_usable_password}, "
            f"got {resp.status_code}: {resp.data}"
        )
        assert "access_token" in resp.data, (
            f"Expected access_token in response for has_usable_password={has_usable_password}: {resp.data}"
        )
        assert "refresh_token" in resp.data, (
            f"Expected refresh_token in response for has_usable_password={has_usable_password}: {resp.data}"
        )
        assert resp.data.get("token_type") == "Bearer"

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(has_usable_password=st.booleans())
    def test_otp_verify_view_does_not_modify_has_usable_password_flag(self, has_usable_password):
        """
        Une vérification OTP réussie ne modifie pas le flag has_usable_password :
        sa valeur avant et après la connexion OTP reste identique.

        Le Login_OTP_Verify_View ne doit pas toucher à has_usable_password
        (seule SetInitialPasswordView le passe à True, et uniquement sur demande
        explicite de l'utilisateur).
        """
        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password)
        has_usable_password_before = user.has_usable_password

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 200, (
            f"Expected HTTP 200 for has_usable_password={has_usable_password}, "
            f"got {resp.status_code}: {resp.data}"
        )

        user.refresh_from_db()
        assert user.has_usable_password == has_usable_password_before, (
            f"has_usable_password was unexpectedly changed by Login_OTP_Verify_View "
            f"(was {has_usable_password_before}, now {user.has_usable_password})"
        )

    # ──────────────────────────────────────────────────────────────────
    # Exemples concrets (non-hypothesis, pour la lisibilité des rapports)
    # ──────────────────────────────────────────────────────────────────

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_passwordless_account_can_login_via_otp(self):
        """
        Exemple concret : un Passwordless_Account (has_usable_password=False,
        créé typiquement via auto-registration) peut se connecter via OTP et
        obtenir des jetons sans jamais avoir défini de mot de passe.
        """
        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password=False)
        assert user.has_usable_password is False

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 200
        assert "access_token" in resp.data
        assert "refresh_token" in resp.data

        # Le flag has_usable_password n'a pas été modifié par la connexion OTP.
        user.refresh_from_db()
        assert user.has_usable_password is False

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_account_with_password_can_still_login_via_otp(self):
        """
        Exemple concret : un compte classique (has_usable_password=True) garde
        la possibilité de se connecter via OTP — les deux voies de connexion
        sont disponibles simultanément après l'opération Set_Initial_Password.
        Cela valide Requirement 7.8 (accessibilité future) en plus de 7.2.
        """
        nonce = _secrets.randbelow(10**8)
        user = _make_user(nonce, has_usable_password=True)
        assert user.has_usable_password is True

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)

        assert resp.status_code == 200
        assert "access_token" in resp.data
        assert "refresh_token" in resp.data

        # Le flag has_usable_password est resté True — la connexion OTP n'y
        # touche pas.
        user.refresh_from_db()
        assert user.has_usable_password is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_set_initial_password_does_not_block_subsequent_otp_login(self):
        """
        Exemple concret : un compte qui a défini son premier mot de passe via
        Set_Initial_Password_Operation (has_usable_password passe à True) peut
        toujours se connecter via OTP — la connexion OTP n'est pas bloquée par
        le fait d'avoir un mot de passe.

        Ce test simule directement la transition d'état (has_usable_password
        False → True) et vérifie que le flux OTP fonctionne des deux côtés
        de cette transition.
        """
        nonce = _secrets.randbelow(10**8)

        # Phase 1 : compte passwordless — OTP login fonctionne.
        user = _make_user(nonce, has_usable_password=False)
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)
        resp_before = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code)
        assert resp_before.status_code == 200

        # Phase 2 : simuler Set_Initial_Password_Operation (has_usable_password → True).
        user.has_usable_password = True
        user.save(update_fields=["has_usable_password"])

        # Phase 3 : après avoir défini un mot de passe, OTP login fonctionne
        # toujours.
        _otp2, raw_code2 = otp_service.generate_login_otp(user)
        resp_after = _post_login_otp_verify(user.phone_country_code, user.phone_number, raw_code2)
        assert resp_after.status_code == 200, (
            f"OTP login should remain available after setting a password, "
            f"got {resp_after.status_code}: {resp_after.data}"
        )
        assert "access_token" in resp_after.data
