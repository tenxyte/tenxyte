import pytest
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import AuthenticationFailed
from django.test import RequestFactory
from tenxyte.authentication import JWTAuthentication, JWTAuthenticationScheme

from tenxyte.models import get_user_model

User = get_user_model()

@pytest.fixture
def rf():
    return RequestFactory()

@pytest.fixture
def auth():
    return JWTAuthentication()

@pytest.mark.django_db
class TestJWTAuthentication:
    def test_authenticate_no_header(self, rf, auth):
        request = rf.get('/')
        assert auth.authenticate(request) is None

    def test_authenticate_no_bearer(self, rf, auth):
        request = rf.get('/', HTTP_AUTHORIZATION='Token something')
        assert auth.authenticate(request) is None

    @patch('tenxyte.core.jwt_service.JWTService.decode_token')
    def test_authenticate_invalid_token(self, mock_decode, rf, auth):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_decode.return_value = DecodedToken(
            user_id='', app_id='', jti='', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=False, error='Invalid token'
        )
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer invalid_token')
        
        with pytest.raises(AuthenticationFailed, match='Token invalide ou expiré'):
            auth.authenticate(request)
            
    @patch('tenxyte.core.jwt_service.JWTService.decode_token')
    def test_authenticate_app_id_mismatch(self, mock_decode, rf, auth):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_decode.return_value = DecodedToken(
            user_id='1', app_id='app1_id', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer valid_token')
        
        # Mock request.application
        request.application = MagicMock()
        request.application.id = 'app2_id'
        
        with pytest.raises(AuthenticationFailed, match='Token ne correspond pas'):
            auth.authenticate(request)

    @patch('tenxyte.core.jwt_service.JWTService.decode_token')
    def test_authenticate_user_not_found(self, mock_decode, rf, auth):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        mock_decode.return_value = DecodedToken(
            user_id='9999', app_id='app1', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer valid_token')
        
        with pytest.raises(AuthenticationFailed, match='Utilisateur non trouvé'):
            auth.authenticate(request)

    @patch('tenxyte.core.jwt_service.JWTService.decode_token')
    def test_authenticate_inactive_user(self, mock_decode, rf, auth):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        user = User.objects.create_user(email='test@example.com', password='pwd', is_active=False)
        mock_decode.return_value = DecodedToken(
            user_id=str(user.id), app_id='app1', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer valid_token')
        
        with pytest.raises(AuthenticationFailed, match='Compte utilisateur inactif'):
            auth.authenticate(request)

    @patch('tenxyte.core.jwt_service.JWTService.decode_token')
    def test_authenticate_locked_user(self, mock_decode, rf, auth):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        user = User.objects.create_user(email='test2@example.com', password='pwd')
        mock_decode.return_value = DecodedToken(
            user_id=str(user.id), app_id='app1', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer valid_token')
        
        with patch.object(User, 'is_account_locked', return_value=True):
            with pytest.raises(AuthenticationFailed, match='Compte utilisateur verrouillé'):
                auth.authenticate(request)

    @patch('tenxyte.core.jwt_service.JWTService.decode_token')
    def test_authenticate_banned_user(self, mock_decode, rf, auth):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        user = User.objects.create_user(email='test3@example.com', password='pwd', is_banned=True)
        mock_decode.return_value = DecodedToken(
            user_id=str(user.id), app_id='app1', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer valid_token')
        
        # is_account_banned generally checks is_banned
        with pytest.raises(AuthenticationFailed, match='Compte utilisateur banni'):
            auth.authenticate(request)

    @patch('tenxyte.core.jwt_service.JWTService.decode_token')
    def test_authenticate_success(self, mock_decode, rf, auth):
        from tenxyte.core.jwt_service import DecodedToken
        from datetime import datetime, timezone
        user = User.objects.create_user(email='test4@example.com', password='pwd')
        mock_decode.return_value = DecodedToken(
            user_id=str(user.id), app_id='app1_id', jti='jti123', exp=datetime.now(timezone.utc),
            iat=datetime.now(timezone.utc), type='access', claims={}, is_valid=True
        )
        
        request = rf.get('/', HTTP_AUTHORIZATION='Bearer valid_token')
        request.application = MagicMock()
        request.application.id = 'app1_id'
        
        returned_user, token = auth.authenticate(request)
        
        assert returned_user == user
        assert token == 'valid_token'
        
    def test_authenticate_header(self, rf, auth):
        request = rf.get('/')
        assert auth.authenticate_header(request) == 'Bearer'


class TestJWTAuthenticationScheme:
    def test_get_security_definition(self):
        scheme = JWTAuthenticationScheme(target=MagicMock())
        auto_schema = MagicMock()
        
        definition = scheme.get_security_definition(auto_schema)
        
        assert definition == {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
