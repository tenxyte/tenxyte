"""
Property-based test for auto-registration creating a properly initialized
passwordless account via Login_OTP_Request_View.

Spec: .kiro/specs/passwordless-phone/

Property 9: L'auto-enregistrement crée un compte passwordless correctement
initialisé
    Pour tout couple (`phone_country_code`, `phone_number`) ne correspondant
    à aucun utilisateur non supprimé, lorsque `TENXYTE_OTP_LOGIN_AUTO_REGISTER`
    est activé, une requête valide crée exactement un nouvel utilisateur avec
    ce téléphone, `is_phone_verified=False`, `has_usable_password=False`, et
    génère/envoie un `Login_OTP_Code` pour ce nouvel utilisateur.

Validates: Requirements 2.6, 6.2
"""

import itertools
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, OTPCode
from tenxyte.services.otp_service import OTPService
from tenxyte.views.login_otp_views import LoginOTPRequestView

User = get_user_model()

# Monotonic counter (plain Python state, unaffected by DB transaction
# rollback) guaranteeing that every generated phone number is unique across
# Hypothesis examples within a single test invocation, on top of the fact
# that the test starts from an empty DB for that phone.
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
class TestLoginOTPRequestAutoRegistration:
    """
    Validates: Requirements 2.6, 6.2

    Pour tout couple (phone_country_code, phone_number) frais (ne
    correspondant à aucun utilisateur non supprimé), avec
    TENXYTE_OTP_LOGIN_AUTO_REGISTER activé, la requête doit créer exactement
    un nouvel utilisateur correctement initialisé (is_phone_verified=False,
    has_usable_password=False) et générer/envoyer un Login_OTP_Code pour ce
    nouvel utilisateur.
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
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_OTP_LOGIN_AUTO_REGISTER=True, APPLICATION_AUTH_ENABLED=False)
    def test_auto_register_creates_properly_initialized_passwordless_account(
        self, country_code_digits, phone_prefix
    ):
        nonce = next(_nonce_counter)
        phone_country_code = country_code_digits
        phone_number = f"{phone_prefix}{nonce:08d}"[:20]

        # Fresh phone: no non-deleted user should exist with this pair yet.
        assert not User.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        ).exists()

        with patch.object(OTPService, "send_phone_otp", return_value=True) as mock_send:
            response = _post_login_otp_request(phone_country_code, phone_number)

        # Response shape: HTTP 200 with message, otp_id, expires_at, channel.
        assert response.status_code == 200
        assert response.data["message"] == "OTP sent"
        assert "otp_id" in response.data
        assert "expires_at" in response.data
        assert response.data["channel"] == "sms"

        # Exactly one new user was created with this phone, properly
        # initialized as a Passwordless_Account.
        matching_users = User.objects.filter(
            phone_country_code=phone_country_code, phone_number=phone_number, is_deleted=False
        )
        assert matching_users.count() == 1
        new_user = matching_users.first()
        assert new_user.is_phone_verified is False
        assert new_user.has_usable_password is False

        # Exactly one new unused login OTP exists for that new user.
        login_otps = OTPCode.objects.filter(user=new_user, otp_type="login", is_used=False)
        assert login_otps.count() == 1

        # OTP sending was invoked for that new user.
        mock_send.assert_called_once()
        called_user = mock_send.call_args.args[0]
        assert called_user.pk == new_user.pk
