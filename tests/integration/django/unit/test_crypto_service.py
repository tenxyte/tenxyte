"""
Tests for DjangoCryptoService - targeting 100% coverage of
src/tenxyte/adapters/django/crypto_service.py
"""
import pytest
from tenxyte.adapters.django.crypto_service import DjangoCryptoService


@pytest.fixture
def crypto():
    return DjangoCryptoService()


# ── __init__ ────────────────────────────────────────────────────────────────

def test_init_no_settings():
    """DjangoCryptoService() with no args sets settings to None (line 34)."""
    svc = DjangoCryptoService()
    assert svc.settings is None


def test_init_with_settings():
    """DjangoCryptoService(settings=...) stores the object (line 34)."""
    fake = object()
    svc = DjangoCryptoService(settings=fake)
    assert svc.settings is fake


# ── generate_random_string ───────────────────────────────────────────────────

def test_generate_random_string_default(crypto):
    """generate_random_string() returns a 32-char hex string (line 85)."""
    result = crypto.generate_random_string()
    assert isinstance(result, str)
    assert len(result) == 32


def test_generate_random_string_custom_length(crypto):
    """generate_random_string(length) respects the requested length."""
    for length in (8, 16, 64):
        result = crypto.generate_random_string(length)
        assert len(result) == length


# ── generate_token ───────────────────────────────────────────────────────────

def test_generate_token(crypto):
    """generate_token() returns a URL-safe base64 token (line 97)."""
    token = crypto.generate_token()
    assert isinstance(token, str)
    assert len(token) > 0

    token_short = crypto.generate_token(length=16)
    assert isinstance(token_short, str)
    # Two calls should (almost certainly) differ
    assert crypto.generate_token() != crypto.generate_token()


# ── hash_sha256 ──────────────────────────────────────────────────────────────

def test_hash_sha256(crypto):
    """hash_sha256() produces a 64-char hex digest (line 109)."""
    digest = crypto.hash_sha256("hello")
    assert isinstance(digest, str)
    assert len(digest) == 64
    # Deterministic
    assert digest == crypto.hash_sha256("hello")
    # Different inputs differ
    assert digest != crypto.hash_sha256("world")


# ── hmac_sign / hmac_verify ──────────────────────────────────────────────────

def test_hmac_sign(crypto):
    """hmac_sign() returns a deterministic hex signature (line 122)."""
    sig = crypto.hmac_sign("data", "secret")
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex digest
    assert sig == crypto.hmac_sign("data", "secret")


def test_hmac_verify_valid(crypto):
    """hmac_verify() returns True for a correct signature (line 140-141)."""
    sig = crypto.hmac_sign("payload", "key123")
    assert crypto.hmac_verify("payload", sig, "key123") is True


def test_hmac_verify_invalid(crypto):
    """hmac_verify() returns False for a tampered signature."""
    assert crypto.hmac_verify("payload", "badsignature" * 5, "key123") is False


# ── encrypt_aes / decrypt_aes ────────────────────────────────────────────────

@pytest.fixture
def fernet_key(crypto):
    """A valid Fernet key for encrypt/decrypt tests."""
    return crypto.generate_key()


def test_encrypt_decrypt_aes(crypto, fernet_key):
    """encrypt_aes → decrypt_aes round-trip (lines 154-157, 170-174)."""
    plaintext = "sensitive data"
    encrypted = crypto.encrypt_aes(plaintext, fernet_key)

    assert isinstance(encrypted, str)
    assert encrypted != plaintext

    decrypted = crypto.decrypt_aes(encrypted, fernet_key)
    assert decrypted == plaintext


def test_encrypt_aes_with_bytes_key(crypto, fernet_key):
    """encrypt_aes() also accepts a str key (isinstance branch, line 156)."""
    encrypted = crypto.encrypt_aes("hello", fernet_key)
    assert isinstance(encrypted, str)


def test_decrypt_aes_invalid_data(crypto, fernet_key):
    """decrypt_aes() returns None on bad data (exception branch, line 175-176)."""
    result = crypto.decrypt_aes("not-valid-ciphertext", fernet_key)
    assert result is None


def test_decrypt_aes_wrong_key(crypto, fernet_key):
    """decrypt_aes() returns None when decrypting with wrong key."""
    encrypted = crypto.encrypt_aes("secret", fernet_key)
    wrong_key = crypto.generate_key()
    result = crypto.decrypt_aes(encrypted, wrong_key)
    assert result is None


# ── generate_key ─────────────────────────────────────────────────────────────

def test_generate_key(crypto):
    """generate_key() returns a Fernet-compatible base64 key (lines 185-186)."""
    key = crypto.generate_key()
    assert isinstance(key, str)
    # A Fernet key is 44 URL-safe base64 chars (32 bytes + padding)
    assert len(key) == 44
    # Two calls should differ
    assert crypto.generate_key() != crypto.generate_key()


# ── hash_password / verify_password ─────────────────────────────────────────

def test_hash_and_verify_password(crypto):
    """hash_password + verify_password round-trip."""
    password = "MySecretPassword!"
    hashed = crypto.hash_password(password)
    assert isinstance(hashed, str)
    assert hashed != password
    assert crypto.verify_password(password, hashed) is True
    assert crypto.verify_password("wrong", hashed) is False
