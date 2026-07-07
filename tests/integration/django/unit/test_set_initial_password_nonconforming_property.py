"""
Property-based test for non-conforming password leaving state unchanged in
Set_Initial_Password_Operation.

Spec: .kiro/specs/passwordless-phone/

Property 23: Un mot de passe non conforme ne modifie aucun état
    Pour tout Passwordless_Account avec un OTP_Reauth_Challenge valide mais
    un new_password qui échoue à la validation de complexité (trop court,
    classes de caractères manquantes, etc.), Set_Initial_Password_Operation
    doit rejeter la requête (HTTP 400, erreur de validation) en laissant
    has_usable_password=False et le hash du mot de passe inchangé.

Validates: Requirements 7.6
"""

import secrets as _secrets
import re

import pytest
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, Application
from tenxyte.services.otp_service import OTPService
from tenxyte.views.password_views import SetInitialPasswordView
from tests.integration.django.test_helpers import get_jwt_service

User = get_user_model()

# A stored password on the account (aléatoire/inutilisable, never exposed)
_STORED_RANDOM_PASSWORD = "rAnD0m-Unusable-Pwd!"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(nonce: int):
    app, _ = Application.create_application(name=f"SIPNonConformApp{nonce}")
    return app


def _passwordless_user(nonce: int):
    """
    Crée un Passwordless_Account :
    - has_usable_password=False
    - mot de passe stocké aléatoire (inutilisable)
    - téléphone pour la génération d'un Login_OTP_Code
    """
    user = User.objects.create(
        email=f"sip-nonconform-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="SIP",
        last_name="NonConform",
        is_active=True,
    )
    user.set_password(_STORED_RANDOM_PASSWORD)
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


def _fresh_otp(user) -> str:
    """Génère un Login OTP frais pour l'utilisateur et retourne le code brut."""
    otp_service = OTPService()
    _otp, raw_code = otp_service.generate_login_otp(user)
    return raw_code


def _is_nonconforming(password: str) -> bool:
    """
    Vérifie si un mot de passe est non conforme selon la logique du validateur
    (utilisé uniquement pour filtrer les générateurs d'hypothèse).
    Critères : longueur, majuscule, minuscule, chiffre, caractère spécial,
    unicité, mots de passe courants, séquences.
    """
    from tenxyte.validators import validate_password
    is_valid, _ = validate_password(password)
    return not is_valid


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# 1. Mots de passe trop courts (< 8 caractères) — garantis non conformes sur
#    le seul critère de longueur, sans filtrage supplémentaire.
_too_short_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Po")),
    min_size=1,
    max_size=7,
)

# 2. Mots de passe purement en minuscules (>= 8 chars) — manquent majuscule,
#    chiffre et caractère spécial → non conformes.
_lowercase_only_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz",
    min_size=8,
    max_size=30,
).filter(_is_nonconforming)

# 3. Mots de passe purement numériques (>= 8 chars) — manquent majuscule,
#    minuscule et caractère spécial → non conformes.
_digits_only_strategy = st.text(
    alphabet="0123456789",
    min_size=8,
    max_size=30,
).filter(_is_nonconforming)

# 4. Mots de passe sans caractère spécial (lettres + chiffres uniquement) —
#    manque au moins le critère "caractère spécial" → non conformes.
_no_special_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=8,
    max_size=30,
).filter(_is_nonconforming)

# Stratégie combinée couvrant les quatre catégories ci-dessus.
_nonconforming_password_strategy = st.one_of(
    _too_short_strategy,
    _lowercase_only_strategy,
    _digits_only_strategy,
    _no_special_strategy,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSetInitialPasswordNonConformingProperty:
    """
    Validates: Requirements 7.6

    Property 23: pour tout Passwordless_Account avec un OTP_Reauth_Challenge
    valide et un new_password non conforme, POST /password/set-initial/ répond
    400 avec une erreur de validation, sans modifier has_usable_password ni le
    hash du mot de passe.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(new_password=_nonconforming_password_strategy)
    def test_nonconforming_password_rejected_state_unchanged(self, new_password):
        """
        Un mot de passe non conforme doit toujours être rejeté (HTTP 400,
        erreur de validation), quel que soit le type de non-conformité (trop
        court, purement numérique, purement en minuscules, sans caractère
        spécial, etc.), même si un OTP_Reauth_Challenge valide est fourni.

        L'état du Passwordless_Account (has_usable_password=False, hash du
        mot de passe) ne doit pas être modifié.
        """
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _passwordless_user(nonce)
        token = _jwt(user, app)

        # Snapshot de l'état avant la requête
        password_hash_before = user.password
        has_usable_before = user.has_usable_password

        # OTP frais et valide fourni avec la requête
        raw_otp_code = _fresh_otp(user)

        factory = APIRequestFactory()
        req = factory.post(
            "/password/set-initial/",
            {"otp_code": raw_otp_code, "new_password": new_password},
            format="json",
        )
        req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        req.application = app

        resp = SetInitialPasswordView.as_view()(req)

        # La requête doit être rejetée avec une erreur de validation
        assert resp.status_code == 400, (
            f"Expected 400 for non-conforming password {new_password!r}, "
            f"got {resp.status_code}: {resp.data}"
        )

        # Le code d'erreur ne doit PAS être ALREADY_HAS_PASSWORD ni OTP_INVALID
        # (l'OTP était valide, c'est bien le mot de passe qui est invalide)
        error_code = resp.data.get("code")
        assert error_code not in ("ALREADY_HAS_PASSWORD", "OTP_INVALID", "OTP_REQUIRED"), (
            f"Unexpected error code {error_code!r} for non-conforming password; "
            f"response data: {resp.data}"
        )

        # L'état du compte ne doit pas avoir changé
        user.refresh_from_db()
        assert user.has_usable_password is False, (
            "has_usable_password must remain False after a rejected non-conforming password"
        )
        assert user.password == password_hash_before, (
            "Password hash must not change after a rejected non-conforming password"
        )
        assert user.has_usable_password == has_usable_before


@pytest.mark.django_db
class TestSetInitialPasswordNonConformingConcreteExamples:
    """
    Exemples concrets complémentaires aux tests basés sur les propriétés.
    Chaque exemple cible un type de non-conformité spécifique.
    """

    def _setup(self):
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _passwordless_user(nonce)
        token = _jwt(user, app)
        return app, user, token

    def _post(self, user, app, token, new_password):
        otp_code = _fresh_otp(user)
        factory = APIRequestFactory()
        req = factory.post(
            "/password/set-initial/",
            {"otp_code": otp_code, "new_password": new_password},
            format="json",
        )
        req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        req.application = app
        return SetInitialPasswordView.as_view()(req)

    @pytest.mark.django_db
    def test_too_short_password_rejected(self):
        """Un mot de passe de moins de 8 caractères est rejeté (400)."""
        app, user, token = self._setup()
        pw_before = user.password

        resp = self._post(user, app, token, "Abc1!")
        assert resp.status_code == 400

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == pw_before

    @pytest.mark.django_db
    def test_purely_numeric_password_rejected(self):
        """Un mot de passe purement numérique est rejeté (manque uppercase,
        lowercase et caractère spécial)."""
        app, user, token = self._setup()
        pw_before = user.password

        resp = self._post(user, app, token, "12345678")
        assert resp.status_code == 400

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == pw_before

    @pytest.mark.django_db
    def test_purely_lowercase_password_rejected(self):
        """Un mot de passe purement en minuscules est rejeté (manque uppercase,
        chiffre et caractère spécial)."""
        app, user, token = self._setup()
        pw_before = user.password

        resp = self._post(user, app, token, "abcdefghij")
        assert resp.status_code == 400

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == pw_before

    @pytest.mark.django_db
    def test_missing_special_char_password_rejected(self):
        """Un mot de passe sans caractère spécial est rejeté."""
        app, user, token = self._setup()
        pw_before = user.password

        resp = self._post(user, app, token, "Abcdef1234")
        assert resp.status_code == 400

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == pw_before

    @pytest.mark.django_db
    def test_empty_password_rejected(self):
        """Un mot de passe vide est rejeté."""
        app, user, token = self._setup()
        pw_before = user.password

        otp_code = _fresh_otp(user)
        factory = APIRequestFactory()
        req = factory.post(
            "/password/set-initial/",
            {"otp_code": otp_code, "new_password": ""},
            format="json",
        )
        req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        req.application = app
        resp = SetInitialPasswordView.as_view()(req)

        assert resp.status_code == 400

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == pw_before
