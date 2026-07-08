"""
Property-based test for the ALREADY_HAS_PASSWORD guard on SetInitialPasswordView.

Spec: .kiro/specs/passwordless-phone/

Property 24: Un compte déjà doté d'un mot de passe ne peut pas utiliser
`Set_Initial_Password_Operation`
    Pour tout compte utilisateur dont has_usable_password=True, tout appel à
    SetInitialPasswordView doit être rejeté avec HTTP 400 et le code
    ALREADY_HAS_PASSWORD, quelle que soit la combinaison de valeurs fournies
    pour otp_code et new_password (OTP valide ou non, mot de passe valide ou
    non). L'état du compte (hash du mot de passe, has_usable_password) ne
    doit pas changer.

Validates: Requirements 7.7
"""

import secrets as _secrets

import pytest
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, Application
from tenxyte.services.otp_service import OTPService
from tenxyte.views.password_views import SetInitialPasswordView
from tests.integration.django.test_helpers import get_jwt_service

User = get_user_model()

STORED_PASSWORD = "InitialPassword123!"


def _app(nonce: int):
    app, _ = Application.create_application(name=f"AlreadyHasPwdApp{nonce}")
    return app


def _user_with_password(nonce: int):
    """Crée un compte avec has_usable_password=True (cas classique : l'utilisateur
    a déjà un mot de passe défini par lui-même). SetInitialPasswordView doit
    rejeter systématiquement tout appel pour ce type de compte."""
    user = User.objects.create(
        email=f"already-pwd-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"7{nonce:08d}",
        first_name="Already",
        last_name="HasPassword",
        is_active=True,
    )
    user.set_password(STORED_PASSWORD)
    # has_usable_password = True est la valeur par défaut, mais on la fixe
    # explicitement pour s'assurer que le scénario de test est bien celui attendu.
    user.has_usable_password = True
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
class TestSetInitialPasswordAlreadyHasPasswordProperty:
    """
    Validates: Requirements 7.7

    Property 24: pour tout compte avec has_usable_password=True, tout appel à
    POST /password/set-initial/ renvoie toujours 400 ALREADY_HAS_PASSWORD,
    quelle que soit la combinaison de supply_otp / supply_password fournie,
    sans jamais modifier l'état du compte.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        supply_otp=st.booleans(),
        supply_password=st.booleans(),
    )
    def test_account_with_password_always_rejected_with_already_has_password(
        self, supply_otp, supply_password
    ):
        """
        Un compte avec has_usable_password=True est toujours rejeté par
        SetInitialPasswordView avec HTTP 400 et code ALREADY_HAS_PASSWORD,
        indépendamment de :
        - la présence ou non d'un Login OTP valide (supply_otp),
        - la présence ou non d'un new_password (supply_password).

        L'état du compte (hash du mot de passe, has_usable_password) ne change
        jamais suite à l'appel.
        """
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _user_with_password(nonce)
        token = _jwt(user, app)

        # Capture de l'état avant appel
        password_hash_before = user.password
        has_usable_password_before = user.has_usable_password
        assert has_usable_password_before is True

        # Construction de la payload selon les stratégies booléennes
        payload = {}
        if supply_otp:
            otp_service = OTPService()
            _otp, raw_code = otp_service.generate_login_otp(user)
            payload["otp_code"] = raw_code
        else:
            # Fournir un code factice (format valide pour le serializer)
            payload["otp_code"] = "000000"

        if supply_password:
            payload["new_password"] = "NewValidP@ss456!"
        else:
            # Fournir un mot de passe minimal
            payload["new_password"] = "AnyPass1!"

        factory = APIRequestFactory()
        req = factory.post("/auth/password/set-initial/", payload, format="json")
        req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        req.application = app

        resp = SetInitialPasswordView.as_view()(req)

        # La vue DOIT rejeter avec 400 ALREADY_HAS_PASSWORD (Requirement 7.7)
        # avant toute validation de serializer ou vérification d'OTP.
        assert resp.status_code == 400, (
            f"Expected HTTP 400, got {resp.status_code}. "
            f"supply_otp={supply_otp}, supply_password={supply_password}. "
            f"Response data: {resp.data}"
        )
        assert resp.data.get("code") == "ALREADY_HAS_PASSWORD", (
            f"Expected code ALREADY_HAS_PASSWORD, got {resp.data.get('code')!r}. "
            f"supply_otp={supply_otp}, supply_password={supply_password}. "
            f"Full response: {resp.data}"
        )

        # L'état du compte ne doit pas avoir changé
        user.refresh_from_db()
        assert user.password == password_hash_before, (
            "Le hash du mot de passe ne doit pas changer après un appel rejeté."
        )
        assert user.has_usable_password is True, (
            "has_usable_password doit rester True après un appel rejeté."
        )
        assert user.has_usable_password == has_usable_password_before
