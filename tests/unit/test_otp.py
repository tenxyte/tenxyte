"""
Tests unitaires pour le service OTP.
"""
import pytest
from datetime import timedelta
from unittest.mock import Mock, patch
from django.utils import timezone

from tenxyte.services.otp_service import OTPService
from tenxyte.models import User, OTPCode


class TestOTPService:
    """Tests pour OTPService."""

    @pytest.mark.django_db
    def test_generate_email_verification_otp(self, user):
        """Test de génération d'OTP pour vérification email."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        assert otp is not None
        assert otp.user == user
        assert otp.otp_type == 'email_verification'
        assert len(raw_code) == 6
        assert len(otp.code) == 64  # SHA-256 hex digest
        assert otp.is_used is False

    @pytest.mark.django_db
    def test_generate_phone_verification_otp(self, user_with_phone):
        """Test de génération d'OTP pour vérification téléphone."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_phone_verification_otp(user_with_phone)

        assert otp is not None
        assert otp.user == user_with_phone
        assert otp.otp_type == 'phone_verification'
        assert len(raw_code) == 6
        assert len(otp.code) == 64  # SHA-256 hex digest
        assert otp.is_used is False

    @pytest.mark.django_db
    def test_generate_password_reset_otp(self, user):
        """Test de génération d'OTP pour reset password."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_password_reset_otp(user)

        assert otp is not None
        assert otp.user == user
        assert otp.otp_type == 'password_reset'
        assert len(raw_code) == 6

    @pytest.mark.django_db
    def test_verify_email_otp_valid(self, user):
        """Test de vérification d'un OTP email valide."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        is_valid, error = otp_service.verify_email_otp(user, raw_code)

        assert is_valid is True
        assert error == ''
        # Vérifier que l'email est marqué comme vérifié
        user.refresh_from_db()
        assert user.is_email_verified is True

    @pytest.mark.django_db
    def test_verify_email_otp_invalid_code(self, user):
        """Test avec code invalide."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        is_valid, error = otp_service.verify_email_otp(user, "999999")

        assert is_valid is False
        assert error != ''

    @pytest.mark.django_db
    def test_verify_email_otp_expired(self, user):
        """Test avec OTP expiré."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        # Forcer l'expiration
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()

        is_valid, error = otp_service.verify_email_otp(user, raw_code)

        assert is_valid is False

    @pytest.mark.django_db
    def test_verify_phone_otp_valid(self, user_with_phone):
        """Test de vérification d'un OTP phone valide."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_phone_verification_otp(user_with_phone)

        is_valid, error = otp_service.verify_phone_otp(user_with_phone, raw_code)

        assert is_valid is True
        assert error == ''
        # Vérifier que le téléphone est marqué comme vérifié
        user_with_phone.refresh_from_db()
        assert user_with_phone.is_phone_verified is True

    @pytest.mark.django_db
    def test_verify_password_reset_otp(self, user):
        """Test de vérification d'OTP reset password."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_password_reset_otp(user)

        is_valid, error = otp_service.verify_password_reset_otp(user, raw_code)

        assert is_valid is True
        assert error == ''

    @pytest.mark.django_db
    @patch('tenxyte.services.email_service.get_email_backend')
    def test_send_email_otp(self, mock_get_backend, user):
        """Test d'envoi d'OTP par email."""
        mock_backend = Mock()
        mock_backend.send_email.return_value = True
        mock_get_backend.return_value = mock_backend

        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        result = otp_service.send_email_otp(user, raw_code, otp.otp_type)

        assert result is True
        mock_backend.send_email.assert_called_once()

    @pytest.mark.django_db
    @patch('tenxyte.backends.sms.get_sms_backend')
    def test_send_phone_otp(self, mock_get_backend, user_with_phone):
        """Test d'envoi d'OTP par SMS."""
        mock_backend = Mock()
        mock_backend.send_sms.return_value = True
        mock_get_backend.return_value = mock_backend

        otp_service = OTPService()
        otp, raw_code = otp_service.generate_phone_verification_otp(user_with_phone)

        result = otp_service.send_phone_otp(user_with_phone, raw_code)

        assert result is True
        mock_backend.send_sms.assert_called_once()

    @pytest.mark.django_db
    def test_send_phone_otp_no_phone(self, user):
        """Test d'envoi SMS sans numéro de téléphone."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        result = otp_service.send_phone_otp(user, raw_code)

        assert result is False

    @pytest.mark.django_db
    def test_invalidate_old_codes(self, user):
        """Test d'invalidation des anciens codes lors de la génération."""
        otp_service = OTPService()

        # Créer un premier OTP
        otp1, raw_code1 = otp_service.generate_email_verification_otp(user)
        otp1_id = otp1.id

        # Créer un second OTP (devrait invalider le premier)
        otp2, raw_code2 = otp_service.generate_email_verification_otp(user)

        # Vérifier que le premier est invalidé
        otp1.refresh_from_db()
        assert otp1.is_used is True
        assert otp2.is_used is False

    @pytest.mark.django_db
    def test_verify_with_too_many_attempts(self, user):
        """Test avec trop de tentatives."""
        otp_service = OTPService()
        otp, raw_code = otp_service.generate_email_verification_otp(user)

        # Forcer le nombre de tentatives au maximum
        otp.attempts = otp.max_attempts
        otp.save()

        is_valid, error = otp_service.verify_email_otp(user, raw_code)

        assert is_valid is False
        assert 'many attempts' in error.lower()
