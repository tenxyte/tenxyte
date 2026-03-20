"""Tests unitaires pour le service JWT core."""
import pytest
import secrets
from tenxyte.core.jwt_service import JWTService
from tenxyte.adapters.django import get_django_settings
from tenxyte.adapters.django.cache_service import DjangoCacheService


@pytest.mark.django_db
class TestJWTService:
    """Tests pour JWTService."""

    def test_generate_access_token(self):
        """Test de génération d'access token."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        token_pair = jwt_service.generate_token_pair(
            user_id="123",
            application_id="app_456",
            refresh_token_str=secrets.token_urlsafe(32)
        )

        assert token_pair.access_token is not None
        assert isinstance(token_pair.access_token, str)
        assert len(token_pair.access_token) > 0

    def test_decode_token(self):
        """Test de décodage de token."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        # Générer un token
        token_pair = jwt_service.generate_token_pair(
            user_id="123",
            application_id="app_456",
            refresh_token_str=secrets.token_urlsafe(32)
        )

        # Décoder le token
        decoded = jwt_service.decode_token(token_pair.access_token)

        assert decoded is not None
        assert decoded.is_valid is True
        assert decoded.user_id == "123"
        assert decoded.app_id == "app_456"
        assert decoded.type == 'access'

    def test_decode_invalid_token(self):
        """Test de décodage de token invalide."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        decoded = jwt_service.decode_token("invalid_token")

        assert decoded is None or decoded.is_valid is False

    def test_is_token_valid(self):
        """Test de validation de token."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        # Token valide
        token_pair = jwt_service.generate_token_pair(
            user_id="123",
            application_id="app_456",
            refresh_token_str=secrets.token_urlsafe(32)
        )
        decoded = jwt_service.decode_token(token_pair.access_token)
        assert decoded is not None and decoded.is_valid is True

        # Token invalide
        decoded_invalid = jwt_service.decode_token("invalid_token")
        assert decoded_invalid is None or decoded_invalid.is_valid is False

    def test_get_user_id_from_token(self):
        """Test d'extraction de l'ID utilisateur."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        token_pair = jwt_service.generate_token_pair(
            user_id="user_123",
            application_id="app_456",
            refresh_token_str=secrets.token_urlsafe(32)
        )

        decoded = jwt_service.decode_token(token_pair.access_token)
        assert decoded.user_id == "user_123"

    def test_get_application_id_from_token(self):
        """Test d'extraction de l'ID application."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        token_pair = jwt_service.generate_token_pair(
            user_id="123",
            application_id="app_789",
            refresh_token_str=secrets.token_urlsafe(32)
        )

        decoded = jwt_service.decode_token(token_pair.access_token)
        assert decoded.app_id == "app_789"

    def test_generate_token_pair(self):
        """Test de génération de paire de tokens."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        token_pair = jwt_service.generate_token_pair(
            user_id="123",
            application_id="app_456",
            refresh_token_str="refresh_abc123"
        )

        assert token_pair.access_token is not None
        assert token_pair.refresh_token == 'refresh_abc123'
        assert isinstance(token_pair.access_token, str)
        assert len(token_pair.access_token) > 0

    def test_extra_claims(self):
        """Test avec claims supplémentaires."""
        jwt_service = JWTService(
            settings=get_django_settings(),
            blacklist_service=DjangoCacheService()
        )

        token_pair = jwt_service.generate_token_pair(
            user_id="123",
            application_id="app_456",
            refresh_token_str=secrets.token_urlsafe(32),
            extra_claims={'role': 'admin', 'level': 5}
        )

        decoded = jwt_service.decode_token(token_pair.access_token)

        assert decoded.claims.get('role') == 'admin'
        assert decoded.claims.get('level') == 5

    @pytest.mark.skip(reason="Patching Django settings for RS256 requires different approach")
    def test_rs256_asymmetric_keys(self):
        """Test de génération et validation avec paires de clés RS256."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from unittest.mock import patch, PropertyMock

        # Generate RSA key pair on the fly
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        with patch('tenxyte.conf.TenxyteSettings.JWT_ALGORITHM', new_callable=PropertyMock, return_value='RS256'), \
             patch('tenxyte.conf.TenxyteSettings.JWT_PRIVATE_KEY', new_callable=PropertyMock, return_value=private_pem), \
             patch('tenxyte.conf.TenxyteSettings.JWT_PUBLIC_KEY', new_callable=PropertyMock, return_value=public_pem):
             
             # Instance de JWTService avec clés asymétriques
             jwt_service = JWTService(
                 settings=get_django_settings(),
                 blacklist_service=DjangoCacheService()
             )
             
             assert jwt_service.is_asymmetric is True
             
             # Générer un token
             token_pair = jwt_service.generate_token_pair(
                 user_id="rs256_user",
                 application_id="app_123",
                 refresh_token_str=secrets.token_urlsafe(32)
             )
             
             # Le token a été encodé avec success
             assert token_pair.access_token is not None
             
             # Valider et décoder
             decoded = jwt_service.decode_token(token_pair.access_token)
             assert decoded is not None
             assert decoded.is_valid is True
             assert decoded.user_id == "rs256_user"
