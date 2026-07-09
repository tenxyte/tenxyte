"""
Property-based test for dual login availability after setting the first password.

Spec: .kiro/specs/passwordless-phone/

Property 25: Double disponibilité après création du premier mot de passe
    Lorsque qu'un Passwordless_Account complète Set_Initial_Password_Operation
    avec succès :
    1. Le compte peut ensuite s'authentifier via l'endpoint de connexion par
       mot de passe existant (/login/phone/ ou /login/email/).
    2. Le compte peut toujours s'authentifier via Login_OTP_Verify_View.

    Les deux voies de connexion doivent rester disponibles simultanément après
    la définition du premier mot de passe.

Validates: Requirements 7.8
"""

import secrets as _secrets
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, Application
from tenxyte.services.otp_service import OTPService
from tenxyte.views.auth_views import LoginEmailView, LoginPhoneView
from tenxyte.views.login_otp_views import LoginOTPVerifyView
from tenxyte.views.password_views import SetInitialPasswordView
from tests.integration.django.test_helpers import get_jwt_service

User = get_user_model()

# A strong password that satisfies all complexity rules (≥12 chars,
# uppercase, lowercase, digit, special character).
STRONG_PASSWORD = "DualLogin!Str0ng99"


# ─────────────────────────────────────────────────────────────────────
# Test-scoped factory helpers
# ─────────────────────────────────────────────────────────────────────


def _make_app(nonce: int) -> Application:
    app, _ = Application.create_application(name=f"DualLoginPropApp{nonce}")
    return app


def _make_passwordless_user(nonce: int, use_email: bool) -> User:
    """Create a Passwordless_Account with both an email and a phone number.

    - has_usable_password=False  (Passwordless_Account)
    - active, not banned, not locked, MFA disabled

    Both email and phone are always set so that either login path is usable
    after Set_Initial_Password_Operation succeeds.
    """
    user = User.objects.create(
        email=f"dual-login-prop-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="DualLogin",
        last_name="Prop",
        is_active=True,
    )
    # Store a random unusable password (mirrors auto-registration behaviour).
    user.set_password(_secrets.token_urlsafe(32))
    user.has_usable_password = False
    user.save()
    return user


def _jwt_for(user: User, app: Application) -> str:
    jwt_service = get_jwt_service()
    return jwt_service.generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str=_secrets.token_urlsafe(16),
    )["access_token"]


# ─────────────────────────────────────────────────────────────────────
# View caller helpers (direct view calls, no URL routing)
# ─────────────────────────────────────────────────────────────────────


def _do_set_initial_password(token: str, app: Application, otp_code: str, new_password: str):
    """POST directly to SetInitialPasswordView (bypasses URL routing)."""
    factory = APIRequestFactory()
    req = factory.post(
        "/auth/password/set-initial/",
        data={"otp_code": otp_code, "new_password": new_password},
        format="json",
    )
    req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    req.application = app
    with patch(
        "tenxyte.services.breach_check_service.breach_check_service.check_password",
        return_value=(True, ""),
    ):
        return SetInitialPasswordView.as_view()(req)


def _do_login_phone(phone_country_code: str, phone_number: str, password: str):
    """POST directly to LoginPhoneView."""
    factory = APIRequestFactory()
    req = factory.post(
        "/auth/login/phone/",
        data={
            "phone_country_code": phone_country_code,
            "phone_number": phone_number,
            "password": password,
        },
        format="json",
    )
    req.application = None
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginPhoneView.as_view()(req)


def _do_login_email(email: str, password: str):
    """POST directly to LoginEmailView."""
    factory = APIRequestFactory()
    req = factory.post(
        "/auth/login/email/",
        data={"email": email, "password": password},
        format="json",
    )
    req.application = None
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginEmailView.as_view()(req)


def _do_login_otp_verify(phone_country_code: str, phone_number: str, otp_code: str):
    """POST directly to LoginOTPVerifyView."""
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


# ─────────────────────────────────────────────────────────────────────
# Property tests
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDualLoginAfterSetInitialPasswordProperty:
    """
    **Validates: Requirements 7.8**

    Property 25: Double disponibilité après création du premier mot de passe.

    Après que Set_Initial_Password_Operation ait réussi pour un
    Passwordless_Account, les deux voies de connexion (mot de passe classique
    ET OTP téléphonique) sont disponibles simultanément.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(use_email_path=st.booleans())
    def test_password_based_login_available_after_set_initial_password(self, use_email_path):
        """
        Pour tout Passwordless_Account ayant complété Set_Initial_Password_Operation,
        la connexion par mot de passe (email ou téléphone selon use_email_path)
        doit réussir avec HTTP 200 et des tokens valides.

        Req 7.8 – partie 1 : le compte peut s'authentifier via l'endpoint de
        connexion par mot de passe existant.
        """
        nonce = _secrets.randbelow(10**8)
        app = _make_app(nonce)
        user = _make_passwordless_user(nonce, use_email=use_email_path)
        token = _jwt_for(user, app)

        assert user.has_usable_password is False

        # Step 1: complete Set_Initial_Password_Operation.
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)
        resp_set = _do_set_initial_password(token, app, raw_code, STRONG_PASSWORD)
        assert resp_set.status_code == 200, (
            f"Set_Initial_Password_Operation failed ({resp_set.status_code}): {resp_set.data}"
        )

        user.refresh_from_db()
        assert user.has_usable_password is True, (
            "has_usable_password should be True after Set_Initial_Password_Operation"
        )

        # Step 2: verify the password-based login path works.
        if use_email_path:
            resp_login = _do_login_email(user.email, STRONG_PASSWORD)
        else:
            resp_login = _do_login_phone(user.phone_country_code, user.phone_number, STRONG_PASSWORD)

        assert resp_login.status_code == 200, (
            f"Password-based login failed after Set_Initial_Password_Operation "
            f"(use_email_path={use_email_path}, status={resp_login.status_code}): {resp_login.data}"
        )
        assert "access_token" in resp_login.data, (
            f"No access_token in password-based login response "
            f"(use_email_path={use_email_path}): {resp_login.data}"
        )
        assert "refresh_token" in resp_login.data, (
            f"No refresh_token in password-based login response "
            f"(use_email_path={use_email_path}): {resp_login.data}"
        )

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(use_email_path=st.booleans())
    def test_otp_login_still_available_after_set_initial_password(self, use_email_path):
        """
        Pour tout Passwordless_Account ayant complété Set_Initial_Password_Operation,
        la connexion par OTP doit encore fonctionner avec HTTP 200 et des tokens valides.

        Req 7.8 – partie 2 : le compte peut toujours s'authentifier via
        Login_OTP_Verify_View après la définition de son premier mot de passe.

        Le paramètre use_email_path est conservé pour que les deux propriétés
        aient exactement la même signature (et que Hypothesis explore les deux
        combinaisons dans les deux propriétés), même si la connexion OTP
        se fait toujours par téléphone.
        """
        nonce = _secrets.randbelow(10**8)
        app = _make_app(nonce)
        user = _make_passwordless_user(nonce, use_email=use_email_path)
        token = _jwt_for(user, app)

        assert user.has_usable_password is False

        # Step 1: complete Set_Initial_Password_Operation.
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)
        resp_set = _do_set_initial_password(token, app, raw_code, STRONG_PASSWORD)
        assert resp_set.status_code == 200, (
            f"Set_Initial_Password_Operation failed ({resp_set.status_code}): {resp_set.data}"
        )

        user.refresh_from_db()
        assert user.has_usable_password is True

        # Step 2: request a new OTP (the one used above is now consumed).
        _otp2, raw_code2 = otp_service.generate_login_otp(user)

        # Step 3: verify OTP login still works after password was set.
        resp_otp = _do_login_otp_verify(user.phone_country_code, user.phone_number, raw_code2)

        assert resp_otp.status_code == 200, (
            f"OTP login failed after Set_Initial_Password_Operation "
            f"(use_email_path={use_email_path}, status={resp_otp.status_code}): {resp_otp.data}"
        )
        assert "access_token" in resp_otp.data, (
            f"No access_token in OTP login response after setting password "
            f"(use_email_path={use_email_path}): {resp_otp.data}"
        )
        assert "refresh_token" in resp_otp.data, (
            f"No refresh_token in OTP login response after setting password "
            f"(use_email_path={use_email_path}): {resp_otp.data}"
        )

    # ─────────────────────────────────────────────────────────────────
    # Concrete examples (non-Hypothesis, for legibility in reports)
    # ─────────────────────────────────────────────────────────────────

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_both_login_paths_available_after_set_initial_password(self):
        """
        Exemple concret complet : un Passwordless_Account qui complète
        Set_Initial_Password_Operation peut ensuite :
        1. Se connecter via /login/phone/ avec le nouveau mot de passe.
        2. Se connecter via /login/email/ avec le nouveau mot de passe.
        3. Se connecter via /login/otp/verify/ avec un nouvel OTP.

        Les trois voies fonctionnent simultanément — ni la définition du
        premier mot de passe, ni une connexion par OTP ne bloquent l'autre.
        """
        nonce = _secrets.randbelow(10**8)
        app = _make_app(nonce)
        user = _make_passwordless_user(nonce, use_email=True)
        token = _jwt_for(user, app)

        assert user.has_usable_password is False

        # --- Set_Initial_Password_Operation ---
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)
        resp_set = _do_set_initial_password(token, app, raw_code, STRONG_PASSWORD)
        assert resp_set.status_code == 200
        assert resp_set.data.get("message") == "Password set successfully"

        user.refresh_from_db()
        assert user.has_usable_password is True
        assert user.check_password(STRONG_PASSWORD) is True

        # --- Login via /login/phone/ ---
        resp_phone = _do_login_phone(user.phone_country_code, user.phone_number, STRONG_PASSWORD)
        assert resp_phone.status_code == 200, (
            f"Phone login failed: {resp_phone.data}"
        )
        assert "access_token" in resp_phone.data

        # --- Login via /login/email/ ---
        resp_email = _do_login_email(user.email, STRONG_PASSWORD)
        assert resp_email.status_code == 200, (
            f"Email login failed: {resp_email.data}"
        )
        assert "access_token" in resp_email.data

        # --- Login via /login/otp/verify/ ---
        _otp2, raw_code2 = otp_service.generate_login_otp(user)
        resp_otp = _do_login_otp_verify(user.phone_country_code, user.phone_number, raw_code2)
        assert resp_otp.status_code == 200, (
            f"OTP login failed after setting password: {resp_otp.data}"
        )
        assert "access_token" in resp_otp.data

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_otp_login_then_set_password_then_otp_login_again(self):
        """
        Exemple concret vérifiant la séquence complète dans l'ordre réaliste :
        1. Connexion OTP initiale (compte passwordless) → HTTP 200.
        2. Définition du premier mot de passe (Set_Initial_Password_Operation) → HTTP 200.
        3. Connexion par mot de passe (via /login/phone/) → HTTP 200.
        4. Connexion OTP à nouveau → HTTP 200.

        Valide Requirement 7.8 : les deux voies restent disponibles
        simultanément après l'étape 2.
        """
        nonce = _secrets.randbelow(10**8)
        app = _make_app(nonce)
        user = _make_passwordless_user(nonce, use_email=False)
        token = _jwt_for(user, app)

        otp_service = OTPService()

        # Step 1: OTP login before password is set.
        _otp1, raw1 = otp_service.generate_login_otp(user)
        resp1 = _do_login_otp_verify(user.phone_country_code, user.phone_number, raw1)
        assert resp1.status_code == 200, f"Initial OTP login failed: {resp1.data}"

        # Step 2: Set the initial password.
        _otp2, raw2 = otp_service.generate_login_otp(user)
        resp2 = _do_set_initial_password(token, app, raw2, STRONG_PASSWORD)
        assert resp2.status_code == 200, f"Set_Initial_Password_Operation failed: {resp2.data}"
        user.refresh_from_db()
        assert user.has_usable_password is True

        # Step 3: Password-based login now works.
        resp3 = _do_login_phone(user.phone_country_code, user.phone_number, STRONG_PASSWORD)
        assert resp3.status_code == 200, (
            f"Password-based login failed after setting password: {resp3.data}"
        )
        assert "access_token" in resp3.data

        # Step 4: OTP login still works after password was set.
        _otp4, raw4 = otp_service.generate_login_otp(user)
        resp4 = _do_login_otp_verify(user.phone_country_code, user.phone_number, raw4)
        assert resp4.status_code == 200, (
            f"OTP login failed after setting password: {resp4.data}"
        )
        assert "access_token" in resp4.data
