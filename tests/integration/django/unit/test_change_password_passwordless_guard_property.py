"""
Property-based test for the passwordless guard on ChangePasswordView.

Spec: .kiro/specs/passwordless-phone/

Property 19: Un compte passwordless ne peut jamais définir son mot de passe
via le changement de mot de passe existant
    Pour tout Passwordless_Account (has_usable_password=False), quel que soit
    le contenu de la requête envoyée à POST /password/change/ (mot de passe
    actuel valide ou non, Login_OTP_Code frais valide ou non, les deux, ou
    aucun des deux, plus un nouveau mot de passe quelconque), la réponse est
    toujours 400 avec le code PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD,
    ReauthService n'est jamais consulté, et l'état du compte (hash du mot de
    passe, has_usable_password) ne change jamais.

Validates: Requirements 6.7
"""

import secrets as _secrets

import pytest
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory
from unittest.mock import patch

from tenxyte.models import get_user_model, Application
from tenxyte.services.otp_service import OTPService
from tenxyte.services.reauth_service import ReauthService
from tenxyte.views.password_views import ChangePasswordView
from tests.integration.django.test_helpers import get_jwt_service

User = get_user_model()

STORED_PASSWORD = "CurrentP@ssw0rd123!"


def _app(nonce: int):
    app, _ = Application.create_application(name=f"PwdlessGuardApp{nonce}")
    return app


def _passwordless_user(nonce: int):
    """Crée un Passwordless_Account : has_usable_password=False, avec un
    mot de passe stocké aléatoire (jamais destiné à être utilisé) et un
    numéro de téléphone pour permettre la génération d'un Login_OTP_Code."""
    user = User.objects.create(
        email=f"pwdless-guard-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="Passwordless",
        last_name="Guard",
        is_active=True,
    )
    user.set_password(STORED_PASSWORD)
    user.has_usable_password = False
    user.save()
    return user


def _jwt(user, app):
    jwt_service = get_jwt_service()
    return jwt_service.generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str=_secrets.token_urlsafe(16),
    )["access_token"]


@pytest.mark.django_db
class TestChangePasswordPasswordlessGuardProperty:
    """
    Validates: Requirements 6.7

    Property 19: pour tout Passwordless_Account, POST /password/change/
    renvoie toujours 400 PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD, quel
    que soit le contenu de la requête, sans jamais modifier le mot de passe
    ni le flag has_usable_password.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        supply_current_password=st.booleans(),
        supply_valid_otp=st.booleans(),
        new_password=st.text(min_size=8, max_size=30),
    )
    def test_passwordless_account_always_rejected_regardless_of_payload(
        self, supply_current_password, supply_valid_otp, new_password
    ):
        """
        Un Passwordless_Account envoyant n'importe quelle combinaison de
        preuves (mot de passe actuel valide, Login_OTP_Code frais valide,
        les deux, ou aucun des deux) reçoit toujours 400 avec le code
        PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD, sans consultation de
        ReauthService, et sans aucune modification de l'état du compte.
        """
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _passwordless_user(nonce)
        token = _jwt(user, app)

        password_hash_before = user.password
        has_usable_password_before = user.has_usable_password

        payload = {"new_password": new_password}
        if supply_current_password:
            payload["current_password"] = STORED_PASSWORD
        if supply_valid_otp:
            otp_service = OTPService()
            _otp, raw_code = otp_service.generate_login_otp(user)
            payload["otp_code"] = raw_code

        factory = APIRequestFactory()
        req = factory.post("/password/change/", payload, format="json")
        req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        req.application = app

        with patch.object(ReauthService, "verify") as mock_verify:
            resp = ChangePasswordView.as_view()(req)

        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.data}"
        assert resp.data.get("code") == "PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD", (
            f"Unexpected response data: {resp.data}"
        )
        mock_verify.assert_not_called()

        user.refresh_from_db()
        assert user.password == password_hash_before
        assert user.has_usable_password is False
        assert user.has_usable_password == has_usable_password_before
