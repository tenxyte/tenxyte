"""
FastAPI Routes for Tenxyte Adapter.
"""
import bcrypt
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from tenxyte.core.schemas import LoginRequest, TokenResponse, MagicLinkRequest
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.magic_link_service import MagicLinkService
from tenxyte.core.settings import get_settings
from tenxyte.ports.repositories import UserRepository

# We assume get_user_repository and get_jwt_service are provided by the FastAPI DI system
# For the proof of concept, we define empty dependencies that the user app should override.

def get_user_repository() -> UserRepository:
    raise NotImplementedError("Dependency get_user_repository must be overridden")

def get_jwt_service() -> JWTService:
    raise NotImplementedError("Dependency get_jwt_service must be overridden")

def get_magic_link_service() -> MagicLinkService:
    raise NotImplementedError("Dependency get_magic_link_service must be overridden")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    jwt_service: JWTService = Depends(get_jwt_service)
):
    """
    Authenticate a user and return JWT tokens.
    """
    user = user_repo.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User has no password set",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        # Check password hash (assumes bcrypt)
        is_valid = bcrypt.checkpw(
            request.password.encode('utf-8'), 
            user.password_hash.encode('utf-8')
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Generate tokens
    token_pair = jwt_service.generate_new_token_pair(
        user_id=user.id,
        application_id="fastapi-app",
        extra_claims={"email": user.email}
    )
    
    # Update last login
    user_repo.update_last_login(user.id, datetime.now(timezone.utc))

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        refresh_expires_in=get_settings().jwt_refresh_token_lifetime
    )

@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(
    request: MagicLinkRequest,
    magic_link_service: MagicLinkService = Depends(get_magic_link_service)
):
    """
    Request a magic link for passwordless login.
    """
    result = magic_link_service.request_magic_link(
        email=request.email,
        ip_address="0.0.0.0", # Can be extracted from Request
        user_agent="FastAPI", # Can be extracted from Request
        application_id="fastapi-app"
    )
    
    # From a security standpoint, we always return a 202 
    # even if the email doesn't exist to prevent enum attacks.
    return {"message": "If the email exists, a magic link has been sent."}
