"""
Property-based test for Login_OTP_Verify_View having no effect when the
feature is disabled.

Spec: .kiro/specs/passwordless-phone/

Property 11: Effet nul de `Login_OTP_Verify_View` quand la fonctionnalité est
désactivée
    Pour toute charge de requête (valide, malformée ou vide) envoyée à
    Login_OTP_Verify_View lorsque TENXYTE_OTP_LOGIN_ENABLED est désactivé,
    aucune vérification de code OTP n'est effectuée, aucun flag utilisateur
    n'est modifié, et aucun jeton n'est émis.

Validates: Requirements 3.1
"""

from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, OTPCode, RefreshToken
from tenxyte.views.login_otp_views import LoginOTPVerifyView

User = get_user_model()


# ---------------------------------------------------------------------------
# Payload strategies: valid-looking, malformed, and empty request bodies.
# ---------------------------------------------------------------------------

_valid_payload = st.fixed_dictionaries(
    {
        "phone_country_code": st.text(alphabet="0123456789", min_size=1, max_size=3),
        "phone_number": st.text(alphabet="0123456789", min_size=6, max_size=14),
        "otp_code": st.text(alphabet="0123456789", min_size=6, max_size=6),
    }
)

_malformed_payload = st.dictionaries(
    keys=st.text(min_size=1, max_size=10),
    values=st.one_of(
        st.text(max_size=20),
        st.integers(),
        st.booleans(),
        st.none(),
        st.lists(st.text(max_size=5), max_size=3),
    ),
    max_size=5,
)

_empty_payload = st.just({})

_request_payload = st.one_of(_valid_payload, _malformed_payload, _empty_payload)


def _post_disabled(payload):
    """POST to LoginOTPVerifyView directly (no URL routing needed)."""
    factory = APIRequestFactory()
    req = factory.post("/auth/login/otp/verify/", data=payload, format="json")
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginOTPVerifyView.as_view()(req)


@pytest.mark.django_db
class TestLoginOTPVerifyViewDisabledHasNoEffect:
    """
    Validates: Requirements 3.1

    Pour toute charge de requête (valide, malformée ou vide) envoyée à
    Login_OTP_Verify_View lorsque TENXYTE_OTP_LOGIN_ENABLED est désactivé :
    - la réponse est 404 avec le code FEATURE_DISABLED
    - aucune vérification de code OTP n'est effectuée (aucun OTPCode marqué
      utilisé, aucun décompte de tentatives modifié)
    - aucun flag utilisateur n'est modifié (is_phone_verified, etc.)
    - aucun jeton (RefreshToken) n'est émis
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(payload=_request_payload)
    def test_disabled_feature_has_no_side_effect(self, payload):
        user_count_before = User.objects.count()
        login_otp_count_before = OTPCode.objects.filter(otp_type="login").count()
        used_login_otp_count_before = OTPCode.objects.filter(otp_type="login", is_used=True).count()
        phone_verified_count_before = User.objects.filter(is_phone_verified=True).count()
        refresh_token_count_before = RefreshToken.objects.count()

        with (
            patch("tenxyte.services.otp_service.OTPService.verify_login_otp") as mock_verify,
            patch("tenxyte.services.otp_service.OTPService.send_phone_otp") as mock_send,
        ):
            response = _post_disabled(payload)

        assert response.status_code == 404
        assert response.data["code"] == "FEATURE_DISABLED"

        mock_verify.assert_not_called()
        mock_send.assert_not_called()

        user_count_after = User.objects.count()
        login_otp_count_after = OTPCode.objects.filter(otp_type="login").count()
        used_login_otp_count_after = OTPCode.objects.filter(otp_type="login", is_used=True).count()
        phone_verified_count_after = User.objects.filter(is_phone_verified=True).count()
        refresh_token_count_after = RefreshToken.objects.count()

        assert user_count_after == user_count_before
        assert login_otp_count_after == login_otp_count_before
        assert used_login_otp_count_after == used_login_otp_count_before
        assert phone_verified_count_after == phone_verified_count_before
        assert refresh_token_count_after == refresh_token_count_before
