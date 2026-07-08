"""
Property-based test for Login_OTP_Request_View rejecting malformed requests
without any side effect.

Spec: .kiro/specs/passwordless-phone/

Property 6: Rejet des requêtes malformées sans effet de bord
    Pour toute charge de requête à `Login_OTP_Request_View` (fonctionnalité
    activée) dans laquelle `phone_country_code` et/ou `phone_number` sont
    absents, vides, ou mal formés, la vue répond par une erreur de
    validation et aucun `Login_OTP_Code` n'est généré.

Validates: Requirements 2.3
"""

from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import get_user_model, OTPCode
from tenxyte.views.login_otp_views import LoginOTPRequestView

User = get_user_model()


# ---------------------------------------------------------------------------
# Strategies producing payloads that are guaranteed to fail
# `LoginOTPRequestSerializer` validation.
#
# `LoginOTPRequestSerializer` only enforces field presence, non-blankness,
# and `max_length` (5 for `phone_country_code`, 20 for `phone_number`) - it
# does NOT enforce a digits-only format. A "non-numeric" string of valid
# length would therefore coincidentally pass validation, so it is
# deliberately excluded here. Every branch below is guaranteed invalid via
# a missing key, `None`, an empty string, a non-coercible type (bool/list/
# dict), or a length exceeding `max_length`.
# ---------------------------------------------------------------------------

_country_code_bad_value = st.one_of(
    st.none(),
    st.just(""),
    st.booleans(),
    st.lists(st.text(max_size=3), min_size=1, max_size=3),
    st.dictionaries(st.text(max_size=3), st.text(max_size=3), max_size=3),
    st.text(min_size=6, max_size=15),  # exceeds max_length=5
)

_phone_number_bad_value = st.one_of(
    st.none(),
    st.just(""),
    st.booleans(),
    st.lists(st.text(max_size=3), min_size=1, max_size=3),
    st.dictionaries(st.text(max_size=3), st.text(max_size=3), max_size=3),
    st.text(min_size=21, max_size=35),  # exceeds max_length=20
)

_country_code_valid_value = st.text(alphabet="0123456789", min_size=1, max_size=5)
_phone_number_valid_value = st.text(alphabet="0123456789", min_size=1, max_size=20)

_malformed_payload = st.one_of(
    # Both fields missing entirely.
    st.just({}),
    # Only phone_country_code present (and malformed); phone_number missing.
    st.builds(lambda v: {"phone_country_code": v}, _country_code_bad_value),
    # Only phone_number present (and malformed); phone_country_code missing.
    st.builds(lambda v: {"phone_number": v}, _phone_number_bad_value),
    # phone_country_code missing; phone_number present but valid (still
    # invalid overall since phone_country_code is required).
    st.builds(lambda v: {"phone_number": v}, _phone_number_valid_value),
    # phone_number missing; phone_country_code present but valid (still
    # invalid overall since phone_number is required).
    st.builds(lambda v: {"phone_country_code": v}, _country_code_valid_value),
    # Both present: phone_country_code malformed, phone_number valid.
    st.builds(
        lambda cc, pn: {"phone_country_code": cc, "phone_number": pn},
        _country_code_bad_value,
        _phone_number_valid_value,
    ),
    # Both present: phone_country_code valid, phone_number malformed.
    st.builds(
        lambda cc, pn: {"phone_country_code": cc, "phone_number": pn},
        _country_code_valid_value,
        _phone_number_bad_value,
    ),
    # Both present and both malformed.
    st.builds(
        lambda cc, pn: {"phone_country_code": cc, "phone_number": pn},
        _country_code_bad_value,
        _phone_number_bad_value,
    ),
)


def _post_malformed(payload):
    """POST to LoginOTPRequestView directly (no URL routing needed)."""
    factory = APIRequestFactory()
    req = factory.post("/auth/login/otp/request/", data=payload, format="json")
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return LoginOTPRequestView.as_view()(req)


@pytest.mark.django_db
class TestLoginOTPRequestViewMalformedRequestsRejected:
    """
    Validates: Requirements 2.3

    Pour toute charge de requête malformée (phone_country_code et/ou
    phone_number absents, vides, ou mal formés) envoyée à
    Login_OTP_Request_View lorsque la fonctionnalité est activée :
    - la réponse est 400 (erreur de validation)
    - aucun OTPCode de type "login" n'est créé
    - aucun nouvel utilisateur n'est créé
    """

    @pytest.mark.django_db
    @override_settings(TENXYTE_OTP_LOGIN_ENABLED=True, TENXYTE_APPLICATION_AUTH_ENABLED=False)
    @hyp_settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(payload=_malformed_payload)
    def test_malformed_payload_rejected_without_side_effect(self, payload):
        user_count_before = User.objects.count()
        login_otp_count_before = OTPCode.objects.filter(otp_type="login").count()

        with patch("tenxyte.services.otp_service.OTPService.send_phone_otp") as mock_send:
            response = _post_malformed(payload)

        assert response.status_code == 400

        mock_send.assert_not_called()

        user_count_after = User.objects.count()
        login_otp_count_after = OTPCode.objects.filter(otp_type="login").count()

        assert user_count_after == user_count_before
        assert login_otp_count_after == login_otp_count_before
