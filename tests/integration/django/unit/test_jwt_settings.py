"""
Tests for uncovered lines in conf/jwt.py — JWT settings properties.
Coverage target: lines 44, 49, 54, 77, 90, 95
"""

from tenxyte.conf import auth_settings


class TestJWTSettings:

    def test_jwt_algorithm(self):
        """Line 44."""
        assert isinstance(auth_settings.JWT_ALGORITHM, str)

    def test_jwt_private_key(self):
        """Line 49."""
        val = auth_settings.JWT_PRIVATE_KEY
        assert val is None or isinstance(val, str)

    def test_jwt_public_key(self):
        """Line 54."""
        val = auth_settings.JWT_PUBLIC_KEY
        assert val is None or isinstance(val, str)

    def test_token_blacklist_enabled(self):
        """Line 77."""
        assert isinstance(auth_settings.TOKEN_BLACKLIST_ENABLED, bool)

    def test_jwt_previous_secret_key(self):
        """Line 90."""
        val = auth_settings.JWT_PREVIOUS_SECRET_KEY
        assert val is None or isinstance(val, str)

    def test_jwt_previous_public_key(self):
        """Line 95."""
        val = auth_settings.JWT_PREVIOUS_PUBLIC_KEY
        assert val is None or isinstance(val, str)
