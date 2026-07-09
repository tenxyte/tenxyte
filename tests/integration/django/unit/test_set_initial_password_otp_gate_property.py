"""
Property-based test for the OTP gate of SetInitialPasswordView.

Spec: .kiro/specs/passwordless-phone/

Property 21: Porte OTP de `Set_Initial_Password_Operation`
    Pour tout Passwordless_Account, si Set_Initial_Password_Operation est
    demandée sans un OTP_Reauth_Challenge valide (code manquant, code expiré
    ou déjà utilisé, mauvais code), la requête doit être rejetée (HTTP 400,
    code `OTP_REQUIRED` ou `OTP_INVALID`), aucun mot de passe ne doit être
    défini et `has_usable_password` doit rester False.

Validates: Requirements 7.3, 7.4
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

# A password that always satisfies the complexity rules
VALID_NEW_PASSWORD = "NewSecureP@ss123!"


def _app(nonce: int):
    app, _ = Application.create_application(name=f"OtpGateApp{nonce}")
    return app


def _passwordless_user(nonce: int):
    """Create a Passwordless_Account with a phone number so login OTP can be
    generated. has_usable_password=False is the defining mark."""
    user = User.objects.create(
        email=f"otp-gate-{nonce}@example.com",
        phone_country_code="33",
        phone_number=f"6{nonce:08d}",
        first_name="OtpGate",
        last_name="Test",
        is_active=True,
    )
    # Store a random unusable password (typical for Passwordless_Account)
    user.set_password(_secrets.token_urlsafe(32))
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


def _post_set_initial(token, app, payload: dict):
    """Fire a POST /password/set-initial/ request and return the DRF Response."""
    factory = APIRequestFactory()
    req = factory.post("/password/set-initial/", payload, format="json")
    req.META["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    req.application = app
    return SetInitialPasswordView.as_view()(req)


@pytest.mark.django_db
class TestSetInitialPasswordOTPGateProperty:
    """
    Validates: Requirements 7.3, 7.4

    Property 21: for any Passwordless_Account, Set_Initial_Password_Operation
    requests that lack a valid OTP_Reauth_Challenge must be rejected with
    HTTP 400 (code OTP_REQUIRED or OTP_INVALID). No password must be set and
    has_usable_password must remain False.
    """

    # ------------------------------------------------------------------ #
    # Case 1 – no otp_code field in the payload                           #
    # ------------------------------------------------------------------ #

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(new_password=st.just(VALID_NEW_PASSWORD))
    def test_missing_otp_code_field_rejected(self, new_password):
        """
        When no otp_code field is included in the request body,
        the view must reject with HTTP 400.  The serializer enforces the
        required otp_code field (min/max_length=6), so the rejection
        comes from serializer validation — status 400, no password set,
        has_usable_password stays False.
        """
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _passwordless_user(nonce)
        token = _jwt(user, app)

        password_hash_before = user.password

        # Payload intentionally omits otp_code
        resp = _post_set_initial(token, app, {"new_password": new_password})

        assert resp.status_code == 400, (
            f"Expected 400 for missing otp_code, got {resp.status_code}: {resp.data}"
        )

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == password_hash_before

    # ------------------------------------------------------------------ #
    # Case 2 – wrong otp_code (6-digit string that doesn't match)         #
    # ------------------------------------------------------------------ #

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(wrong_code=st.text(alphabet="0123456789", min_size=6, max_size=6))
    def test_wrong_otp_code_rejected_with_otp_invalid(self, wrong_code):
        """
        When a valid login OTP exists for the user but an incorrect 6-digit
        code is supplied, the view must reject with HTTP 400 and code
        OTP_INVALID.  No password is set, has_usable_password stays False.
        """
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _passwordless_user(nonce)
        token = _jwt(user, app)

        # Generate a real login OTP so there is a code to fail against
        otp_service = OTPService()
        _otp, real_code = otp_service.generate_login_otp(user)

        password_hash_before = user.password

        # Build a payload whose otp_code is NOT the real code.
        # (In the tiny probability that wrong_code == real_code, the OTP
        # would be consumed and the test would not reach the assertion below.
        # We rely on Hypothesis shrinking and the enormous key-space to make
        # this astronomically unlikely; the property holds for all wrong codes.)
        assume_wrong = wrong_code != real_code
        if not assume_wrong:
            # Skip this example rather than fail; hypothesis will move on.
            return

        resp = _post_set_initial(
            token, app, {"otp_code": wrong_code, "new_password": VALID_NEW_PASSWORD}
        )

        assert resp.status_code == 400, (
            f"Expected 400 for wrong otp_code, got {resp.status_code}: {resp.data}"
        )
        assert resp.data.get("code") in ("OTP_INVALID", "OTP_REQUIRED"), (
            f"Expected OTP_INVALID or OTP_REQUIRED, got: {resp.data}"
        )

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == password_hash_before

    # ------------------------------------------------------------------ #
    # Case 3 – used / expired OTP (the code was already consumed)         #
    # ------------------------------------------------------------------ #

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(dummy=st.none())
    def test_used_otp_code_rejected_with_otp_invalid(self, dummy):
        """
        When a login OTP has already been consumed (is_used=True), presenting
        its raw code must be rejected with HTTP 400 and code OTP_INVALID.
        No password is set, has_usable_password stays False.
        """
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _passwordless_user(nonce)
        token = _jwt(user, app)

        otp_service = OTPService()
        otp, raw_code = otp_service.generate_login_otp(user)

        # Mark the OTP as already used (simulates a consumed / expired code)
        otp.is_used = True
        otp.save(update_fields=["is_used"])

        password_hash_before = user.password

        resp = _post_set_initial(
            token, app, {"otp_code": raw_code, "new_password": VALID_NEW_PASSWORD}
        )

        assert resp.status_code == 400, (
            f"Expected 400 for used otp_code, got {resp.status_code}: {resp.data}"
        )
        assert resp.data.get("code") in ("OTP_INVALID", "OTP_REQUIRED"), (
            f"Expected OTP_INVALID or OTP_REQUIRED, got: {resp.data}"
        )

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == password_hash_before

    # ------------------------------------------------------------------ #
    # Case 4 – no login OTP exists at all (OTP_REQUIRED path)             #
    # ------------------------------------------------------------------ #

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(supplied_code=st.text(alphabet="0123456789", min_size=6, max_size=6))
    def test_no_login_otp_exists_rejected_with_otp_required(self, supplied_code):
        """
        When no login OTP has ever been generated for the account, any
        supplied code must be rejected with HTTP 400 and code OTP_REQUIRED.
        No password is set, has_usable_password stays False.
        """
        nonce = _secrets.randbelow(10**8)
        app = _app(nonce)
        user = _passwordless_user(nonce)
        token = _jwt(user, app)

        # Ensure no login OTP exists for this user
        from tenxyte.models import OTPCode
        OTPCode.objects.filter(user=user, otp_type="login").delete()

        password_hash_before = user.password

        resp = _post_set_initial(
            token, app, {"otp_code": supplied_code, "new_password": VALID_NEW_PASSWORD}
        )

        assert resp.status_code == 400, (
            f"Expected 400 when no login OTP exists, got {resp.status_code}: {resp.data}"
        )
        assert resp.data.get("code") == "OTP_REQUIRED", (
            f"Expected OTP_REQUIRED when no login OTP exists, got: {resp.data}"
        )

        user.refresh_from_db()
        assert user.has_usable_password is False
        assert user.password == password_hash_before
