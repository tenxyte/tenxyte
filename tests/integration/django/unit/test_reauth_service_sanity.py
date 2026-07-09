"""
Sanity check ponctuel pour ReauthService.verify (task 11.1).

Les tests de propriétés formels (Property 17, Property 18) sont couverts
par les tâches 11.2/11.3. Ce fichier vérifie uniquement les 5 chemins
d'exemple décrits dans le design (mot de passe correct/incorrect, OTP
valide/invalide, aucune preuve fournie).
"""

import pytest

from tenxyte.services.otp_service import OTPService
from tenxyte.services.reauth_service import ReauthService


@pytest.mark.django_db
class TestReauthServiceSanity:
    def test_correct_password_succeeds(self, user):
        service = ReauthService()

        success, error_code, error_message = service.verify(user, password="TestPassword123!")

        assert success is True
        assert error_code == ""
        assert error_message == ""

    def test_incorrect_password_fails_with_invalid_password(self, user):
        service = ReauthService()

        success, error_code, error_message = service.verify(user, password="WrongPassword!")

        assert success is False
        assert error_code == "INVALID_PASSWORD"
        assert error_message

    def test_valid_login_otp_succeeds_without_password(self, user_with_phone):
        otp_service = OTPService()
        _otp, raw_code = otp_service.generate_login_otp(user_with_phone)
        service = ReauthService(otp_service=otp_service)

        success, error_code, error_message = service.verify(user_with_phone, otp_code=raw_code)

        assert success is True
        assert error_code == ""
        assert error_message == ""

    def test_invalid_login_otp_fails_with_otp_invalid(self, user_with_phone):
        otp_service = OTPService()
        otp_service.generate_login_otp(user_with_phone)
        service = ReauthService(otp_service=otp_service)

        success, error_code, error_message = service.verify(user_with_phone, otp_code="000000")

        assert success is False
        assert error_code == "OTP_INVALID"
        assert error_message

    def test_no_password_no_otp_fails_with_reauth_required(self, user):
        service = ReauthService()

        success, error_code, error_message = service.verify(user)

        assert success is False
        assert error_code == "REAUTH_REQUIRED"
        assert error_message
