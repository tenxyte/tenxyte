"""
Django Crypto Service for Tenxyte Core.

Implements the CryptoService protocol using Django's cryptography utilities.
"""

from typing import Optional
import hashlib
import hmac
import secrets


class DjangoCryptoService:
    """
    Cryptographic service implementation for Django.

    Provides secure hashing, encryption, and random generation using
    Python's standard library (available in Django context).

    Example:
        from tenxyte.adapters.django.crypto_service import DjangoCryptoService

        crypto = DjangoCryptoService()
        hashed = crypto.hash_password("secret123")
        is_valid = crypto.verify_password("secret123", hashed)
    """

    def __init__(self, settings=None):
        """Initialize crypto service.

        Args:
            settings: Optional settings object (for compatibility with Core interface)
        """
        self.settings = settings
        pass

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        import bcrypt

        # Pre-hash with SHA256 for bcrypt length compatibility
        pre_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()  # lgtm[py/weak-sensitive-data-hashing] codeql[py/weak-sensitive-data-hashing]
        return bcrypt.hashpw(pre_hash.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password
            hashed: Previously hashed password

        Returns:
            True if password matches
        """
        import bcrypt

        pre_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()  # lgtm[py/weak-sensitive-data-hashing] codeql[py/weak-sensitive-data-hashing]
        return bcrypt.checkpw(pre_hash.encode("utf-8"), hashed.encode("utf-8"))

    def generate_random_string(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure random string.

        Args:
            length: Length of string to generate

        Returns:
            Random hexadecimal string
        """
        return secrets.token_hex(length // 2 + 1)[:length]

    def generate_token(self, length: int = 32) -> str:
        """
        Generate a secure random token.

        Args:
            length: Token length in bytes

        Returns:
            URL-safe base64-encoded token
        """
        return secrets.token_urlsafe(length)

    def hash_sha256(self, data: str) -> str:
        """
        Create SHA256 hash of data.

        Args:
            data: String to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def hmac_sign(self, data: str, key: str) -> str:
        """
        Create HMAC signature of data.

        Args:
            data: Data to sign
            key: Secret key

        Returns:
            Hexadecimal HMAC signature
        """
        return hmac.new(key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()

    def hmac_verify(self, data: str, signature: str, key: str) -> bool:
        """
        Verify HMAC signature.

        Args:
            data: Original data
            signature: Expected signature
            key: Secret key

        Returns:
            True if signature is valid
        """
        expected = self.hmac_sign(data, key)
        return hmac.compare_digest(expected, signature)

    def encrypt_aes(self, data: str, key: str) -> str:
        """
        Encrypt data using Fernet (AES-128 in CBC mode with HMAC).

        Args:
            data: Data to encrypt
            key: Encryption key (base64-encoded 32-byte key)

        Returns:
            Encrypted data (base64-encoded)
        """
        from cryptography.fernet import Fernet

        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.encrypt(data.encode()).decode()

    def decrypt_aes(self, data: str, key: str) -> Optional[str]:
        """
        Decrypt Fernet-encrypted data.

        Args:
            data: Encrypted data (base64-encoded)
            key: Encryption key

        Returns:
            Decrypted string or None if failed
        """
        try:
            from cryptography.fernet import Fernet

            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.decrypt(data.encode()).decode()
        except Exception:
            return None

    def generate_key(self) -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded 32-byte key
        """
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode()
