"""
Property-based test for anti-enumeration on Login_OTP_Request_View's
response when no account matches the requested phone.

Spec: .kiro/specs/passwordless-phone/

Property 10: Anti-énumération sur la demande d'OTP de connexion
    Pour tout couple (`phone_country_code`, `phone_number`) ne correspondant
    à aucun utilisateur non supprimé, lorsque `TENXYTE_OTP_LOGIN_AUTO_REGISTER`
    est désactivé, la réponse HTTP 200 de `Login_OTP_Request_View` a le même
    ensemble de clés et les mêmes types de valeurs que la réponse retournée
    pour un compte existant (Property 8), tout en ne créant ni compte, ni
    `Login_OTP_Code`, ni envoi réel.

Validates: Requirements 2.7
"""

import itertools
from datetime import datetime
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, OTPCode
from tenxyte.services.otp_service import OTPService
from tenxyte.views.login_otp_views import LoginOTPRequestView

User = get_user_model()

# Monotonic counter guaranteeing that every generated phone number is
# unique across Hypothesis examples within a single test invocation, so
# that no example ever accidentally collides with a previously created
# (or pre-existing) user.
_nonce_counter = itertools.count()


def _post_login_otp_request(phone_country_code: str, phone_number: str):
    factory = APIRequestFactory()
    req = factory.post(
        "/auth/login/otp/request/",
        data={"phone_country_code": phone_country_code, "phone_number": phone_number},
        format="json",
    )
    req.application = None
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginOTPRequestView.as_view()(req)


@pytest.mark.django_db
class TestLoginOTPRequestAntiEnumeration:
    """
    Validates: Requirements 2.7

    Pour tout couple (phone_country_code, phone_number) ne correspondant à
    aucun utilisateur non supprimé, avec TENXYTE_OTP_LOGIN_AUTO_REGISTER
    désactivé, la réponse doit avoir la même forme (clés et types) que la
    réponse retournée pour un compte existant, sans créer de compte, sans
    créer de Login_OTP_Code, et sans jamais invoquer l'envoi réel du code.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        country_code_digits=st.text(alphabet="0123456789", min_size=1, max_size=4),
        phone_prefix=st.text(alphabet="0123456789", min_size=3, max_size=8),
    )
    @override_settings(
        TENXYTE_OTP_LOGIN_ENABLED=True,
        TENXYTE_OTP_LOGIN_AUTO_REGISTER=False,
        TENXYTE_APPLICATION_AUTH_ENABLED=False,
    )
    def test_anti_enumeration_response_matches_existing_account_shape(
        self, country_code_digits, phone_prefix
    ):
        nonce = next(_nonce_counter)
        phone_country_code = country_code_digits
        phone_number = f"{phone_prefix}{nonce:08d}"[:20]

        # Fresh phone: no non-deleted user should exist with this pair.
        assert not User.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        ).exists()

        users_before = User.objects.count()
        otps_before = OTPCode.objects.count()

        with patch.object(OTPService, "send_phone_otp", return_value=True) as mock_send:
            resp = _post_login_otp_request(phone_country_code, phone_number)

        # Response is a 200 with exactly the same key set and value types
        # as the existing-account success response (Property 8).
        assert resp.status_code == 200
        assert set(resp.data.keys()) == {"message", "otp_id", "expires_at", "channel"}
        assert resp.data["message"] == "OTP sent"
        assert resp.data["channel"] == "sms"
        assert isinstance(resp.data["otp_id"], str)
        assert isinstance(resp.data["expires_at"], str)
        # expires_at must be a valid ISO datetime string.
        datetime.fromisoformat(resp.data["expires_at"])

        # No account, no Login_OTP_Code was created.
        assert User.objects.count() == users_before
        assert OTPCode.objects.count() == otps_before
        assert not User.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        ).exists()

        # OTP sending was never invoked.
        mock_send.assert_not_called()

    @pytest.mark.django_db
    @override_settings(
        TENXYTE_OTP_LOGIN_ENABLED=True,
        TENXYTE_OTP_LOGIN_AUTO_REGISTER=False,
        TENXYTE_APPLICATION_AUTH_ENABLED=False,
    )
    def test_anti_enumeration_concrete_example(self):
        """
        Exemple concret : une requête pour un téléphone n'existant pas,
        avec auto-register désactivé, renvoie 200 avec une réponse de
        même forme que pour un compte existant, sans créer ni compte ni
        Login_OTP_Code, et sans envoi réel.
        """
        phone_country_code = "33"
        phone_number = "699999999"

        assert not User.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        ).exists()

        users_before = User.objects.count()
        otps_before = OTPCode.objects.count()

        with patch.object(OTPService, "send_phone_otp", return_value=True) as mock_send:
            resp = _post_login_otp_request(phone_country_code, phone_number)

        assert resp.status_code == 200
        assert set(resp.data.keys()) == {"message", "otp_id", "expires_at", "channel"}
        assert resp.data["message"] == "OTP sent"
        assert resp.data["channel"] == "sms"
        assert User.objects.count() == users_before
        assert OTPCode.objects.count() == otps_before
        mock_send.assert_not_called()
