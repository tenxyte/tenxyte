"""
Tests unitaires pour le service JWT.
"""
import pytest
from datetime import datetime, timedelta

from tenxyte.services import JWTService


@pytest.mark.django_db
class TestJWTService:
    """Tests pour JWTService."""

    def test_generate_access_token(self):
        """Test de génération d'access token."""
        jwt_service = JWTService()

        token, jti, expires_at = jwt_service.generate_access_token(
            user_id="123",
            application_id="app_456"
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        assert jti is not None
        assert expires_at is not None

    def test_decode_token(self):
        """Test de décodage de token."""
        jwt_service = JWTService()

        # Générer un token
        token, jti, expires_at = jwt_service.generate_access_token(
            user_id="123",
            application_id="app_456"
        )

        # Décoder le token
        payload = jwt_service.decode_token(token)

        assert payload is not None
        assert payload['user_id'] == "123"
        assert payload['app_id'] == "app_456"
        assert payload['type'] == 'access'

    def test_decode_invalid_token(self):
        """Test de décodage de token invalide."""
        jwt_service = JWTService()

        payload = jwt_service.decode_token("invalid_token")

        assert payload is None

    def test_is_token_valid(self):
        """Test de validation de token."""
        jwt_service = JWTService()

        # Token valide
        token, jti, expires_at = jwt_service.generate_access_token(
            user_id="123",
            application_id="app_456"
        )
        assert jwt_service.is_token_valid(token) is True

        # Token invalide
        assert jwt_service.is_token_valid("invalid_token") is False

    def test_get_user_id_from_token(self):
        """Test d'extraction de l'ID utilisateur."""
        jwt_service = JWTService()

        token, jti, expires_at = jwt_service.generate_access_token(
            user_id="user_123",
            application_id="app_456"
        )

        user_id = jwt_service.get_user_id_from_token(token)
        assert user_id == "user_123"

    def test_get_application_id_from_token(self):
        """Test d'extraction de l'ID application."""
        jwt_service = JWTService()

        token, jti, expires_at = jwt_service.generate_access_token(
            user_id="123",
            application_id="app_789"
        )

        app_id = jwt_service.get_application_id_from_token(token)
        assert app_id == "app_789"

    def test_generate_token_pair(self):
        """Test de génération de paire de tokens."""
        jwt_service = JWTService()

        tokens = jwt_service.generate_token_pair(
            user_id="123",
            application_id="app_456",
            refresh_token_str="refresh_abc123"
        )

        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
        assert 'token_type' in tokens
        assert 'expires_in' in tokens

        assert tokens['token_type'] == 'Bearer'
        assert tokens['refresh_token'] == 'refresh_abc123'
        assert tokens['expires_in'] > 0

    def test_extra_claims(self):
        """Test avec claims supplémentaires."""
        jwt_service = JWTService()

        token, jti, expires_at = jwt_service.generate_access_token(
            user_id="123",
            application_id="app_456",
            extra_claims={'role': 'admin', 'level': 5}
        )

        payload = jwt_service.decode_token(token)

        assert payload['role'] == 'admin'
        assert payload['level'] == 5

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
             jwt_service = JWTService()
             
             assert jwt_service.is_asymmetric is True
             assert jwt_service.algorithm == 'RS256'
             
             # Générer un token
             token, jti, exp = jwt_service.generate_access_token(user_id="rs256_user", application_id="app_123")
             
             # Le token a été encodé avec success
             assert token is not None
             
             # Valider et décoder
             payload = jwt_service.decode_token(token)
             assert payload is not None
             assert payload['user_id'] == "rs256_user"
