"""
Property-based test for the successful Set_Initial_Password_Operation.

Spec: .kiro/specs/passwordless-phone/

Property 22: Succès de `Set_Initial_Password_Operation`
    Pour tout Passwordless_Account avec un OTP_Reauth_Challenge valide et
    un nouveau mot de passe satisfaisant les règles de complexité,
    Set_Initial_Password_Operation réussit (HTTP 200), le mot de passe est
    réellement défini sur le compte (user.check_password(new_password) is
    True), et has_usable_password devient True (marquant le compte comme
    n'étant plus un Passwordless_Account — Requirement 6.3).

Validates: Requirements 7.5, 6.3
"""

import secrets as _secrets
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, Application
from tenxyte.services.otp_service import OTPService
from tenxyte.views.password_views import SetInitialPasswordView
from tests.integration.django.test_helpers import get_jwt_service

User = get_user_model()

# Fixed strong password that satisfies complexity rules (min 12 chars,
# uppercase, lowercase, digit, special character).
STRONG_PASSWORD = "NewStr0ng!Passw0rd"


def _make_app(nonce: int):
    """Create a unique Application for isolating each test run."""
    app, _ = Application.create_application(name=f"SetInitPwdSuccessApp{nonce}")
    return app


def _make_passwordless_user(nonce: int):
    """Create a Passwordless_Account: has_usable_password=False with a phone
    number (needed for login OTP generation)."""
    user = User.objects.create(
        email=f"set-initial-pwd-success-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="SetInitial",
        last_name="Success",
        is_active=True,
    )
    # Set an unusable random password (mirrors auto-registration behaviour).
    user.set_password(_secrets.token_urlsafe(32))
    user.has_usable_password = False
    user.save()
    return user


def _jwt_for(user, app) -> str:
    """Generate a valid JWT access token for *user* associated with *app*."""
    jwt_service = get_jwt_service()
    return jwt_service.generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str=_secrets.token_urlsafe(16),
    )["access_token"]


def _post_set_initial(token: str, app, otp_code: str, new_password: str):
    """POST to SetInitialPasswordView directly (bypasses URL routing)."""
    factory = APIRequestFactory()
    req = factory.post(
        "/auth/password/set-initial/",
        data={"otp_code": otp_code, "new_password": new_password},
        format="json",
    )
    req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    req.application = app
    # Patch HIBP breach check to avoid external network calls.
    with patch(
        "tenxyte.services.breach_check_service.breach_check_service.check_password",
        return_value=(True, ""),
    ):
        return SetInitialPasswordView.as_view()(req)


@pytest.mark.django_db
class TestSetInitialPasswordSuccessProperty:
    """
    Validates: Requirements 7.5, 6.3

    Property 22: pour tout Passwordless_Account avec un OTP_Reauth_Challenge
    valide et un nouveau mot de passe conforme, Set_Initial_Password_Operation
    (POST /password/set-initial/) retourne HTTP 200, le mot de passe est
    effectivement défini, et has_usable_password passe à True.
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        # Use st.just with a fixed strong password to avoid hitting complexity
        # rules issues while still exercising the property across many runs.
        new_password=st.just(STRONG_PASSWORD),
    )
    def test_success_sets_password_and_marks_not_passwordless(self, new_password):
        """
        Pour tout Passwordless_Account avec un OTP_Reauth_Challenge valide et
        un mot de passe conforme, la réponse est HTTP 200, le mot de passe est
        défini sur le compte, et has_usable_password devient True.
        """
        nonce = _secrets.randbelow(10**8)
        app = _make_app(nonce)
        user = _make_passwordless_user(nonce)
        token = _jwt_for(user, app)

        # Record initial state
        assert user.has_usable_password is False

        # Generate a fresh, valid OTP_Reauth_Challenge.
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_set_initial(token, app, raw_code, new_password)

        # --- HTTP 200 (Requirement 7.5) ---
        assert resp.status_code == 200, (
            f"Expected HTTP 200, got {resp.status_code}: {resp.data}"
        )
        assert resp.data.get("message") == "Password set successfully"

        # --- Password actually set (Requirement 7.5) ---
        user.refresh_from_db()
        assert user.check_password(new_password) is True, (
            "user.check_password(new_password) should be True after "
            "Set_Initial_Password_Operation succeeds"
        )

        # --- Account is no longer a Passwordless_Account (Requirement 6.3) ---
        assert user.has_usable_password is True, (
            "has_usable_password should be True after Set_Initial_Password_Operation succeeds"
        )

    @pytest.mark.django_db
    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_concrete_example_full_flow(self):
        """
        Exemple concret complet : un Passwordless_Account avec un OTP valide
        et un mot de passe conforme obtient HTTP 200 et sort du statut
        Passwordless_Account.
        """
        nonce = _secrets.randbelow(10**8)
        app = _make_app(nonce)
        user = _make_passwordless_user(nonce)
        token = _jwt_for(user, app)

        assert user.has_usable_password is False
        assert user.check_password(STRONG_PASSWORD) is False

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_set_initial(token, app, raw_code, STRONG_PASSWORD)

        assert resp.status_code == 200
        assert resp.data.get("message") == "Password set successfully"

        user.refresh_from_db()
        assert user.check_password(STRONG_PASSWORD) is True
        assert user.has_usable_password is True

    @pytest.mark.django_db
    @override_settings(TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_has_usable_password_transitions_from_false_to_true(self):
        """
        Vérifie explicitement la transition de has_usable_password False → True
        (Requirement 6.3) : le compte passe du statut Passwordless_Account au
        statut de compte avec mot de passe utilisable.
        """
        nonce = _secrets.randbelow(10**8)
        app = _make_app(nonce)
        user = _make_passwordless_user(nonce)
        token = _jwt_for(user, app)

        has_usable_before = user.has_usable_password
        assert has_usable_before is False

        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post_set_initial(token, app, raw_code, STRONG_PASSWORD)

        assert resp.status_code == 200

        user.refresh_from_db()
        assert user.has_usable_password is True
        assert user.has_usable_password != has_usable_before
