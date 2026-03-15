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
        user = type('MockUser', (object,), {'totp_secret': secret, 'id': 1})()

        # Générer un code valide
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Vérifier le code
        is_valid = totp_service.verify_code(user, valid_code)

        assert is_valid is True

    from unittest.mock import patch

    @patch('django.core.cache.cache.get')
    def test_verify_code_anti_replay(self, mock_cache_get):
        """Test anti-replay (VULN-007)."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()
        user = type('MockUser', (object,), {'totp_secret': secret, 'id': 1})()

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Simulate that code was already used
        mock_cache_get.return_value = True

        is_valid = totp_service.verify_code(user, valid_code)
        assert is_valid is False

    def test_verify_code_invalid(self):
        """Test de vérification d'un code invalide."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()
        user = type('MockUser', (object,), {'totp_secret': secret, 'id': 1})()

        is_valid = totp_service.verify_code(user, "000000")

        assert is_valid is False

    def test_verify_code_empty(self):
        """Test avec code vide."""
        totp_service = TOTPService()
        secret = totp_service.generate_secret()
        user = type('MockUser', (object,), {'totp_secret': secret, 'id': 1})()

        is_valid = totp_service.verify_code(user, "")

        assert is_valid is False

    def test_verify_code_no_secret(self):
        """Test avec secret vide."""
        totp_service = TOTPService()
        user = type('MockUser', (object,), {'totp_secret': None, 'id': 1})()

        is_valid = totp_service.verify_code(user, "123456")

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
            assert len(parts[0]) == 8
            assert len(parts[1]) == 8

        # Vérifier que les codes sont hashés
        for hashed in hashed_codes:
            assert isinstance(hashed, str)
            assert len(hashed) > 60  # Django make_password generates longer hashes
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

        assert 'issuer=' in uri.lower()

    def test_verify_code_exception(self):
        totp_service = TOTPService()
        user = type('MockUser', (object,), {'totp_secret': 'secret', 'id': 1})()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "get_totp", Exception("mocked exception"))
            assert totp_service.verify_code(user, "123456") is False

    def test_verify_backup_code_no_codes(self):
        totp_service = TOTPService()
        user = type('MockUser', (object,), {'backup_codes': None})()
        assert totp_service.verify_backup_code(user, "123") is False

    def test_confirm_2fa_errors(self):
        totp_service = TOTPService()
        class MockUser:
            totp_secret = None
            is_2fa_enabled = False

        user = MockUser()
        # No totp_secret
        success, msg = totp_service.confirm_2fa(user, "123456")
        assert not success

        # Already enabled
        user.totp_secret = "secret"
        user.is_2fa_enabled = True
        success, msg = totp_service.confirm_2fa(user, "123456")
        assert not success

        # Invalid code
        user.is_2fa_enabled = False
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: False)
            success, msg = totp_service.confirm_2fa(user, "123456")
            assert not success

    def test_disable_2fa_errors(self):
        totp_service = TOTPService()
        class MockUser:
            is_2fa_enabled = False
            totp_secret = "secret"
            backup_codes = []
        user = MockUser()

        success, msg = totp_service.disable_2fa(user, "123")
        assert not success

        user.is_2fa_enabled = True
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: False)
            m.setattr(totp_service, "verify_backup_code", lambda u, c: False)
            success, msg = totp_service.disable_2fa(user, "123")
            assert not success

    def test_disable_2fa_success_via_backup(self):
        totp_service = TOTPService()
        import hashlib
        code = "a1b2-c3d4"
        hashed = hashlib.sha256(code.encode()).hexdigest()

        class MockUser:
            id = 1
            is_2fa_enabled = True
            totp_secret = "secret"
            backup_codes = [hashed]
            def save(self, update_fields=None):
                pass

        user = MockUser()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: False)
            success, msg = totp_service.disable_2fa(user, code)
            assert success

    def test_verify_2fa(self):
        totp_service = TOTPService()
        class MockUser:
            is_2fa_enabled = False
            totp_secret = "secret"
        user = MockUser()

        # Not enabled
        success, msg = totp_service.verify_2fa(user, "123")
        assert success

        user.is_2fa_enabled = True
        # No code
        success, msg = totp_service.verify_2fa(user, "")
        assert not success

        # Valid TOTP
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: True)
            success, msg = totp_service.verify_2fa(user, "123")
            assert success

        # Valid Backup
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: False)
            m.setattr(totp_service, "verify_backup_code", lambda u, c: True)
            success, msg = totp_service.verify_2fa(user, "123")
            assert success

        # Invalid overall
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: False)
            m.setattr(totp_service, "verify_backup_code", lambda u, c: False)
            success, msg = totp_service.verify_2fa(user, "123")
            assert not success

    def test_regenerate_backup_codes(self):
        totp_service = TOTPService()
        class MockUser:
            id = 1
            is_2fa_enabled = False
            totp_secret = "secret"
            backup_codes = []
            def save(self, update_fields=None):
                pass
        user = MockUser()

        # Not enabled
        success, codes, msg = totp_service.regenerate_backup_codes(user, "123")
        assert not success

        user.is_2fa_enabled = True
        # Invalid code
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: False)
            success, codes, msg = totp_service.regenerate_backup_codes(user, "123")
            assert not success

        # Success
        with pytest.MonkeyPatch().context() as m:
            m.setattr(totp_service, "verify_code", lambda s, c: True)
            success, codes, msg = totp_service.regenerate_backup_codes(user, "123")
            assert success
            assert len(codes) > 0

    @patch('os.environ.get')
    def test_totp_key_initialization_and_decryption(self, mock_env_get):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode('utf-8')
        mock_env_get.return_value = key

        totp_service = TOTPService()
        assert totp_service.totp_key is not None

        secret = "mysecret"
        encrypted = totp_service.totp_key.encrypt(secret.encode("utf-8")).decode("utf-8")
        user = type('MockUser', (object,), {'totp_secret': encrypted, 'id': 1})()

        assert totp_service._get_decrypted_secret(user) == secret

        user_bad = type('MockUser', (object,), {'totp_secret': "invalid_encrypted_data", 'id': 2})()
        assert totp_service._get_decrypted_secret(user_bad) is None

    def test_verify_backup_code_formats(self):
        totp_service = TOTPService()
        from django.contrib.auth.hashers import make_password

        raw_code = "a1b2c3d4e5f6g7h8"
        formatted_code = "a1b2c3d4-e5f6g7h8"
        hashed = make_password(formatted_code)

        class MockUser:
            id = 1
            backup_codes = [hashed]
            def save(self, update_fields=None):
                pass

        user = MockUser()

        assert totp_service.verify_backup_code(user, raw_code) is True
        assert len(user.backup_codes) == 0

        user.backup_codes = [hashed]
        assert totp_service.verify_backup_code(user, "wrongcode") is False

    @patch('os.environ.get')
    def test_setup_2fa(self, mock_env_get):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode('utf-8')
        mock_env_get.return_value = key

        totp_service = TOTPService()

        class MockUser:
            id = 1
            email = "test@example.com"
            totp_secret = None
            backup_codes = []
            def save(self, update_fields=None):
                pass

        user = MockUser()
        result = totp_service.setup_2fa(user)

        assert 'secret' in result
        assert 'qr_code' in result
        assert 'backup_codes' in result
        assert user.totp_secret is not None
        assert user.totp_secret != result['secret']

        mock_env_get.return_value = None
        totp_service_no_enc = TOTPService()

        user2 = MockUser()
        result2 = totp_service_no_enc.setup_2fa(user2)
        assert user2.totp_secret == result2['secret']

    def test_confirm_2fa_success(self):
        totp_service = TOTPService()

        class MockUser:
            id = 1
            totp_secret = "secret"
            is_2fa_enabled = False
            def save(self, update_fields=None):
                pass

        user = MockUser()

        from unittest.mock import patch as _patch
        with _patch.object(totp_service, 'verify_code', return_value=True):
            success, msg = totp_service.confirm_2fa(user, "123456")

        assert success is True
        assert msg == ""
        assert user.is_2fa_enabled is True
