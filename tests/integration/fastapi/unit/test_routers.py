import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone
import bcrypt

from tenxyte.adapters.fastapi.routers import router, get_user_repository, get_jwt_service, get_magic_link_service
from tenxyte.core.jwt_service import TokenPair, SecurityWarning
from tenxyte.core.magic_link_service import MagicLinkResult
from tenxyte.ports.repositories import User

# Create a FastAPI app for testing
app = FastAPI()
app.include_router(router)

# Mock services
mock_user_repo = Mock()
mock_jwt_service = Mock()
mock_magic_link_service = Mock()

# Override dependencies
app.dependency_overrides[get_user_repository] = lambda: mock_user_repo
app.dependency_overrides[get_jwt_service] = lambda: mock_jwt_service
app.dependency_overrides[get_magic_link_service] = lambda: mock_magic_link_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mocks():
    mock_user_repo.reset_mock()
    mock_jwt_service.reset_mock()
    mock_magic_link_service.reset_mock()

def test_login_success():
    # Setup mocks
    password = "MySecurePassword123"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    mock_user = User(
        id="u1", 
        email="test@user.com", 
        password_hash=hashed, 
        is_active=True
    )
    mock_user_repo.get_by_email.return_value = mock_user
    
    # Mock token generation
    mock_jwt_service.generate_new_token_pair.return_value = TokenPair(
        access_token="acc",
        access_token_jti="jti",
        access_token_expires_at=datetime.now(timezone.utc),
        refresh_token="ref",
        token_type="Bearer",
        expires_in=900
    )
    
    with patch("tenxyte.adapters.fastapi.routers.get_settings") as mock_settings:
        mock_settings.return_value.jwt_refresh_token_lifetime = 86400
        
        # Test
        response = client.post("/auth/login", json={
            "email": "test@user.com",
            "password": password
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "acc"
        assert data["refresh_token"] == "ref"
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 900
        assert data["refresh_expires_in"] == 86400

        mock_user_repo.update_last_login.assert_called_once()
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore", SecurityWarning)
            mock_jwt_service.generate_new_token_pair.assert_called_once_with(
                user_id="u1",
                application_id="fastapi-app",
                extra_claims={"email": "test@user.com"}
            )

def test_login_user_not_found():
    mock_user_repo.get_by_email.return_value = None
    
    response = client.post("/auth/login", json={
        "email": "notfound@user.com",
        "password": "password"
    })
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_login_no_password_set():
    mock_user = User(
        id="u1", 
        email="test@user.com", 
        password_hash=None, 
        is_active=True
    )
    mock_user_repo.get_by_email.return_value = mock_user
    
    response = client.post("/auth/login", json={
        "email": "test@user.com",
        "password": "password"
    })
    
    assert response.status_code == 401

def test_login_invalid_password():
    # Setup mocks
    hashed_wrong = bcrypt.hashpw("DifferentPassword".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    mock_user = User(
        id="u1", 
        email="test@user.com", 
        password_hash=hashed_wrong, 
        is_active=True
    )
    mock_user_repo.get_by_email.return_value = mock_user
    
    response = client.post("/auth/login", json={
        "email": "test@user.com",
        "password": "password"
    })
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_login_inactive_user():
    password = "password"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    mock_user = User(
        id="u1", 
        email="test@user.com", 
        password_hash=hashed, 
        is_active=False
    )
    mock_user_repo.get_by_email.return_value = mock_user
    
    response = client.post("/auth/login", json={
        "email": "test@user.com",
        "password": password
    })
    
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"]

def test_magic_link_request():
    mock_magic_link_service.request_magic_link.return_value = MagicLinkResult(
        success=True
    )
    
    response = client.post("/auth/magic-link", json={
        "email": "test@user.com"
    })
    
    assert response.status_code == 202
    assert "If the email exists" in response.json()["message"]
    
    mock_magic_link_service.request_magic_link.assert_called_once()
    args = mock_magic_link_service.request_magic_link.call_args[1]
    assert args["email"] == "test@user.com"
    assert args["application_id"] == "fastapi-app"
