"""
Property-based test for Login_OTP_Request_View generating and sending a
code when the request targets an existing account.

Spec: .kiro/specs/passwordless-phone/

Property 8: Requête pour un compte existant génère et envoie un code pour ce compte
    Pour tout utilisateur non supprimé existant identifié par un couple
    (`phone_country_code`, `phone_number`), une requête valide à
    `Login_OTP_Request_View` avec ce couple génère exactement un nouveau
    `Login_OTP_Code` non utilisé pour cet utilisateur et déclenche l'envoi du
    code par le canal téléphonique.

Validates: Requirements 2.5
"""

import string
import secrets as _secrets
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, OTPCode
from tenxyte.services.otp_service import OTPService
from tenxyte.views.login_otp_views import LoginOTPRequestView

User = get_user_model()


def _make_user(nonce: int, country_code: str):
    """Crée un utilisateur existant (non supprimé) avec un couple
    (phone_country_code, phone_number) unique dérivé du nonce."""
    user = User.objects.create(
        email=f"login-otp-req-{nonce}@example.com",
        phone_country_code=country_code,
        phone_number=f"6{nonce:010d}",
        first_name="Login",
        last_name="Request",
    )
    user.set_password("TestPassword123!")
    user.save()
    return user


def _post_login_otp_request(phone_country_code: str, phone_number: str):
    factory = APIRequestFactory()
    req = factory.post(
        "/auth/login/otp/request/",
        data={"phone_country_code": phone_country_code, "phone_number": phone_number},
        format="json",
    )
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        view = LoginOTPRequestView.as_view()
        return view(req)


@pytest.mark.django_db
class TestLoginOTPRequestExistingAccountGeneratesAndSendsCode:
    """
    Validates: Requirements 2.5

    Pour tout utilisateur non supprimé existant identifié par un couple
    (phone_country_code, phone_number), une requête valide à
    Login_OTP_Request_View avec ce couple doit générer exactement un
    nouveau Login_OTP_Code non utilisé pour cet utilisateur et déclencher
    l'envoi du code par le canal téléphonique.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        country_code=st.text(alphabet=string.digits, min_size=1, max_size=3),
    )
    def test_existing_account_request_generates_and_sends_code(self, country_code):
        """
        Pour un utilisateur existant arbitraire identifié par un couple
        (phone_country_code, phone_number), une requête valide génère
        exactement un nouveau Login_OTP_Code non utilisé pour ce compte et
        déclenche l'envoi du code par SMS pour ce même compte.
        """
        nonce = _secrets.randbelow(10**9)
        user = _make_user(nonce, country_code)

        with override_settings(
            TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False
        ), patch(
            "tenxyte.views.login_otp_views.OTPService.send_phone_otp",
            return_value=True,
        ) as mock_send:
            resp = _post_login_otp_request(user.phone_country_code, user.phone_number)

        # Response shape and status.
        assert resp.status_code == 200
        assert set(resp.data.keys()) == {"message", "otp_id", "expires_at", "channel"}
        assert resp.data["message"] == "OTP sent"
        assert resp.data["channel"] == "sms"

        # Exactly one new unused login OTP now exists for this user.
        unused_login_otps = OTPCode.objects.filter(user=user, otp_type="login", is_used=False)
        assert unused_login_otps.count() == 1
        new_otp = unused_login_otps.first()
        assert resp.data["otp_id"] == str(new_otp.pk)

        # The OTP-sending mechanism was invoked exactly once, for this user,
        # with the raw code of the newly generated OTP.
        mock_send.assert_called_once()
        called_user, called_raw_code = mock_send.call_args[0]
        assert called_user.pk == user.pk

        otp_service = OTPService()
        is_valid, error = otp_service.verify_login_otp(user, called_raw_code)
        assert is_valid is True
        assert error == ""

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    def test_existing_account_request_concrete_example(self, user_with_phone):
        """
        Exemple concret : une requête pour un compte existant (fixture
        user_with_phone) génère un unique Login_OTP_Code et déclenche
        l'envoi du code par SMS pour ce compte.
        """
        with patch(
            "tenxyte.views.login_otp_views.OTPService.send_phone_otp",
            return_value=True,
        ) as mock_send:
            resp = _post_login_otp_request(
                user_with_phone.phone_country_code, user_with_phone.phone_number
            )

        assert resp.status_code == 200
        unused_login_otps = OTPCode.objects.filter(
            user=user_with_phone, otp_type="login", is_used=False
        )
        assert unused_login_otps.count() == 1
        mock_send.assert_called_once()
        called_user, _called_raw_code = mock_send.call_args[0]
        assert called_user.pk == user_with_phone.pk
