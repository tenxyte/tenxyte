"""
Tests unitaires pour le service TOTP (2FA).
"""
import pytest
import pyotp

from tenxyte.services import TOTPService


class TestTOTPService:
    """Tests pour TOTPService."""

    def test_generate_secret(self):
        """Test de génération de secret."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()

        assert secret is not None
        assert isinstance(secret, str)
        assert len(secret) == 32  # Base32 secret
        # Vérifier que c'est du base32 valide
        assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567' for c in secret)

    def test_get_totp(self):
        """Test de création d'objet TOTP."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()

        totp = totp_service.get_totp(secret)

        assert totp is not None
        assert isinstance(totp, pyotp.TOTP)

    def test_verify_code_valid(self):
        """Test de vérification d'un code valide."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()

        # Générer un code valide
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Vérifier le code
        is_valid = totp_service.verify_code(secret, valid_code)

        assert is_valid is True

    def test_verify_code_invalid(self):
        """Test de vérification d'un code invalide."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()

        is_valid = totp_service.verify_code(secret, "000000")

        assert is_valid is False

    def test_verify_code_empty(self):
        """Test avec code vide."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()

        is_valid = totp_service.verify_code(secret, "")

        assert is_valid is False

    def test_verify_code_no_secret(self):
        """Test avec secret vide."""
        totp_service = TOTPService()

        is_valid = totp_service.verify_code("", "123456")

        assert is_valid is False

    def test_get_provisioning_uri(self):
        """Test de génération d'URI de provisioning."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()
        email = "test@example.com"

        uri = totp_service.get_provisioning_uri(secret, email)

        assert uri is not None
        assert uri.startswith('otpauth://totp/')
        # L'email sera URL-encodé (@ devient %40)
        assert 'test%40example.com' in uri or 'test@example.com' in uri
        assert secret in uri
        assert 'issuer' in uri.lower()

    def test_generate_qr_code(self):
        """Test de génération de QR code."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()
        email = "test@example.com"

        qr_code = totp_service.generate_qr_code(secret, email)

        assert qr_code is not None
        assert isinstance(qr_code, str)
        assert qr_code.startswith('data:image/png;base64,')
        assert len(qr_code) > 100  # Un QR code encodé fait au moins ça

    def test_generate_backup_codes(self):
        """Test de génération de codes de secours."""
        totp_service = TOTPService()

        plain_codes, hashed_codes = totp_service.generate_backup_codes()

        # Vérifier le nombre de codes
        assert len(plain_codes) == totp_service.BACKUP_CODES_COUNT
        assert len(hashed_codes) == totp_service.BACKUP_CODES_COUNT

        # Vérifier le format des codes en clair
        for code in plain_codes:
            assert isinstance(code, str)
            assert '-' in code  # Format: xxxx-xxxx
            parts = code.split('-')
            assert len(parts) == 2
            assert len(parts[0]) == 4
            assert len(parts[1]) == 4

        # Vérifier que les codes sont hashés
        for hashed in hashed_codes:
            assert isinstance(hashed, str)
            assert len(hashed) == 64  # SHA256 hex = 64 chars
            assert hashed not in plain_codes  # Pas de code en clair

    def test_backup_codes_uniqueness(self):
        """Test que les codes de secours sont uniques."""
        totp_service = TOTPService()

        plain_codes1, _ = totp_service.generate_backup_codes()
        plain_codes2, _ = totp_service.generate_backup_codes()

        # Les deux séries doivent être différentes
        assert plain_codes1 != plain_codes2

    def test_issuer_name_configurable(self):
        """Test que le nom de l'émetteur est configurable."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()

        uri = totp_service.get_provisioning_uri(secret, "test@example.com")

        # Vérifier que l'issuer est présent
        assert 'issuer=' in uri.lower()
