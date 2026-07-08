"""
Property-based test for Login_OTP_Request_View blocking generation when a
required application is missing.

Spec: .kiro/specs/passwordless-phone/

Property 7: Application requise et absente bloque toute génération
    Pour toute charge de requête par ailleurs valide, si
    `APPLICATION_AUTH_ENABLED` est actif et qu'aucune application valide
    n'est résolue sur la requête, `Login_OTP_Request_View` répond par une
    erreur d'authentification d'application et aucun `Login_OTP_Code` n'est
    généré.

Validates: Requirements 2.4
"""

from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, OTPCode
from tenxyte.views.login_otp_views import LoginOTPRequestView

User = get_user_model()


# Otherwise-valid phone payloads: digits-only country code (1-4 digits, with
# or without a leading '+') and a plausible phone number (6-14 digits).
phone_country_code_strategy = st.builds(
    lambda has_plus, digits: ("+" if has_plus else "") + digits,
    has_plus=st.booleans(),
    digits=st.text(alphabet="0123456789", min_size=1, max_size=4),
)
phone_number_strategy = st.text(alphabet="0123456789", min_size=6, max_size=14)


@pytest.mark.django_db
class TestLoginOTPRequestMissingApplicationBlocksGeneration:
    """
    Validates: Requirements 2.4

    Pour toute charge de requête par ailleurs valide envoyée à
    Login_OTP_Request_View, si APPLICATION_AUTH_ENABLED est actif et qu'aucune
    application valide n'est résolue sur la requête, la vue doit répondre par
    une erreur d'authentification d'application (401, code APP_AUTH_REQUIRED)
    et ne doit générer aucun Login_OTP_Code ni créer aucun utilisateur.
    """

    @pytest.mark.django_db
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        phone_country_code=phone_country_code_strategy,
        phone_number=phone_number_strategy,
    )
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=True)
    def test_missing_application_blocks_generation(self, phone_country_code, phone_number):
        otp_count_before = OTPCode.objects.filter(otp_type="login").count()
        user_count_before = User.objects.count()

        factory = APIRequestFactory()
        request = factory.post(
            "/auth/login/otp/request/",
            {"phone_country_code": phone_country_code, "phone_number": phone_number},
            format="json",
        )
        # No `application` attribute is set on the request, simulating the
        # absence of a valid application (ApplicationAuthMiddleware not
        # having resolved one, e.g. missing/invalid X-Access-Key/-Secret).

        with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
            response = LoginOTPRequestView.as_view()(request)

        assert response.status_code == 401
        assert response.data.get("code") == "APP_AUTH_REQUIRED"

        otp_count_after = OTPCode.objects.filter(otp_type="login").count()
        user_count_after = User.objects.count()

        assert otp_count_after == otp_count_before
        assert user_count_after == user_count_before
