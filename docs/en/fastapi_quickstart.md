# FastAPI Quickstart

Get started with Tenxyte in a FastAPI application in 2 minutes. This guide covers installing Tenxyte with FastAPI support, configuring the core services, and setting up authentication endpoints.

## Table of Contents

- [Install](#1-install)
- [Configure](#2-configure-your-fastapi-app)
- [Initialize Core Services](#3-initialize-core-services)
- [Create Endpoints](#4-create-authentication-endpoints)
- [Run the Application](#5-run-the-application)
- [Usage Examples](#usage-examples)
- [Production Considerations](#production-considerations)

---

## 1. Install

Install Tenxyte with FastAPI extras:

```bash
pip install tenxyte[fastapi,postgres]  # Includes FastAPI + PostgreSQL support
```

Available extras for FastAPI:
- `[fastapi]` — FastAPI core dependencies (fastapi, uvicorn, python-multipart)
- `[postgres]` — PostgreSQL support (psycopg2-binary)
- `[mysql]` — MySQL support (mysqlclient)
- `[webauthn]` — Passkeys/FIDO2 support
- `[all]` — Everything included

---

## 2. Configure Your FastAPI App

Create your main application file:

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from tenxyte.core.settings import Settings, init
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

# Initialize settings
settings = init(provider=EnvSettingsProvider())

# Initialize task service
task_service = AsyncIOTaskService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting up Tenxyte services...")
    yield
    # Shutdown
    print("Shutting down Tenxyte services...")

app = FastAPI(
    title="My FastAPI App with Tenxyte",
    description="Authentication and security powered by Tenxyte",
    version="1.0.0",
    lifespan=lifespan
)
```

### Environment Variables

Create a `.env` file:

```bash
# Required for JWT
TENXYTE_JWT_SECRET_KEY=your-super-secret-jwt-key-at-least-32-characters-long

# Optional: Token lifetimes
TENXYTE_JWT_ACCESS_TOKEN_LIFETIME=3600
TENXYTE_JWT_REFRESH_TOKEN_LIFETIME=604800

# Optional: Security settings
TENXYTE_MAX_LOGIN_ATTEMPTS=5
TENXYTE_LOCKOUT_DURATION=300

# Database (example with SQLAlchemy/asyncpg)
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
```

---

## 3. Initialize Core Services

Set up the core Tenxyte services with your infrastructure adapters:

```python
# services.py
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.cache_service import InMemoryCacheService
from tenxyte.core.email_service import ConsoleEmailService
from tenxyte.core.totp_service import TOTPService
from tenxyte.core.magic_link_service import MagicLinkService
from tenxyte.core.settings import Settings

from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

# Initialize services
settings = Settings(provider=EnvSettingsProvider())
cache_service = InMemoryCacheService()  # Or Redis adapter
email_service = ConsoleEmailService()    # Or SendGrid adapter
task_service = AsyncIOTaskService()

# Core services
jwt_service = JWTService(
    settings=settings,
    blacklist_service=cache_service
)

totp_service = TOTPService(settings=settings)

magic_link_service = MagicLinkService(
    settings=settings,
    email_service=email_service,
    # repo and user_lookup would be your custom implementations
)
```

---

## 4. Create Authentication Endpoints

### JWT Authentication Endpoints

```python
# auth_router.py
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from services import jwt_service, settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT tokens."""
    # Verify credentials (implement your own user verification)
    user = await verify_user_credentials(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate tokens
    access_token, jti, expires_at = jwt_service.generate_access_token(
        user_id=str(user.id),
        application_id="default"
    )
    refresh_token = jwt_service.generate_refresh_token(
        user_id=str(user.id),
        application_id="default"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(settings.access_token_lifetime.total_seconds())
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    token_pair = await jwt_service.refresh_tokens_async(refresh_token)
    if not token_pair:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": token_pair.token_type,
        "expires_in": token_pair.expires_in
    }

@router.post("/logout")
async def logout(authorization: str = Header(...)):
    """Logout and blacklist the token."""
    token = authorization.replace("Bearer ", "")
    await jwt_service.blacklist_token_async(token)
    return {"status": "logged_out"}
```

### Dependency for Protected Routes

```python
# dependencies.py
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services import jwt_service

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to extract and validate JWT token."""
    token = credentials.credentials
    
    decoded = await jwt_service.decode_token_async(token)
    if not decoded or not decoded.is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if decoded.is_blacklisted:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    
    # Load user from database
    user = await get_user_by_id(decoded.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Usage in protected routes
@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
```

### 2FA Endpoints

```python
# twofa_router.py
from fastapi import APIRouter, Depends, HTTPException
from services import totp_service, settings

router = APIRouter(prefix="/2fa", tags=["2FA"])

class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str  # Base64 encoded QR code
    backup_codes: list[str]

@router.post("/setup", response_model=TOTPSetupResponse)
async def setup_2fa(current_user: User = Depends(get_current_user)):
    """Setup TOTP 2FA for current user."""
    # Your custom storage adapter
    storage = UserTOTPStorage(user_id=current_user.id)
    
    result = await totp_service.setup_2fa_async(
        user_id=str(current_user.id),
        email=current_user.email,
        storage=storage
    )
    
    return {
        "secret": result.secret,
        "qr_code": result.qr_code,
        "backup_codes": result.backup_codes
    }

@router.post("/confirm")
async def confirm_2fa_setup(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Confirm TOTP setup with verification code."""
    storage = UserTOTPStorage(user_id=current_user.id)
    
    success, error = await totp_service.confirm_2fa_setup_async(
        user_id=str(current_user.id),
        code=code,
        storage=storage
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {"status": "2fa_enabled"}

@router.post("/verify")
async def verify_2fa(
    user_id: str,
    code: str
):
    """Verify TOTP code during login."""
    storage = UserTOTPStorage(user_id=user_id)
    
    success, error = await totp_service.verify_2fa_async(
        user_id=user_id,
        code=code,
        storage=storage
    )
    
    if not success:
        raise HTTPException(status_code=401, detail=error or "Invalid code")
    
    return {"status": "verified"}
```

---

## 5. Run the Application

```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation.

---

## Usage Examples

### Complete Login Flow with 2FA

```python
@app.post("/login/step1")
async def login_step1(request: LoginRequest):
    """First step: validate credentials."""
    user = await verify_user_credentials(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if 2FA is enabled
    storage = UserTOTPStorage(user_id=user.id)
    user_data = await storage.load_user_data_async(str(user.id))
    
    if user_data and user_data.is_2fa_enabled:
        # Return temporary token for 2FA step
        temp_token = jwt_service.generate_access_token(
            user_id=str(user.id),
            application_id="default",
            extra_claims={"2fa_pending": True}
        )[0]
        return {"requires_2fa": True, "temp_token": temp_token}
    
    # No 2FA required, return full tokens
    access_token, _, _ = jwt_service.generate_access_token(str(user.id), application_id="default")
    refresh_token = jwt_service.generate_refresh_token(str(user.id), application_id="default")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "requires_2fa": False
    }

@app.post("/login/step2")
async def login_step2(code: str, temp_token: str):
    """Second step: validate 2FA code."""
    # Verify temp token
    decoded = await jwt_service.decode_token_async(temp_token)
    if not decoded or not decoded.extra_claims.get("2fa_pending"):
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Verify 2FA code
    storage = UserTOTPStorage(user_id=decoded.user_id)
    success, error = await totp_service.verify_2fa_async(
        user_id=decoded.user_id,
        code=code,
        storage=storage
    )
    
    if not success:
        raise HTTPException(status_code=401, detail=error)
    
    # Issue final tokens
    access_token, _, _ = jwt_service.generate_access_token(decoded.user_id, application_id="default")
    refresh_token = jwt_service.generate_refresh_token(decoded.user_id, application_id="default")
    
    return {"access_token": access_token, "refresh_token": refresh_token}
```

### Background Task Example

```python
from services import task_service, email_service

@app.post("/register")
async def register(request: RegisterRequest):
    """Register user and send welcome email in background."""
    # Create user (synchronous DB operation)
    user = await create_user(request.email, request.password)
    
    # Send welcome email asynchronously
    await task_service.enqueue_async(
        email_service.send_welcome_async,
        to_email=user.email,
        first_name=user.first_name,
        login_url="https://app.example.com/login"
    )
    
    return {"user_id": user.id, "status": "registered"}
```

---

## Production Considerations

### 1. Use Production-Grade Cache

Replace `InMemoryCacheService` with a Redis adapter for multi-instance deployments. Tenxyte does not ship a Redis adapter, but creating one is straightforward (see [Custom Adapters](custom_adapters.md)):

```python
# See custom_adapters.md for full RedisCacheAdapter implementation
from my_adapters.cache import RedisCacheAdapter

cache_service = RedisCacheAdapter(redis_url="redis://localhost:6379/0")

jwt_service = JWTService(settings=settings, blacklist_service=cache_service)
```

### 2. Configure CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Rate Limiting

```python
from fastapi import Request
from services import cache_service

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host
    allowed, remaining, reset_time = await cache_service.check_rate_limit_async(
        key=f"rate_limit:{client_ip}",
        max_requests=100,  # requests
        window_seconds=60  # per minute
    )
    
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
```

### 4. Application Authentication

For application-level authentication (API keys), use the `Application` model directly:

```python
from fastapi import Security, HTTPException, Header
from tenxyte.models import get_application_model

Application = get_application_model()

async def verify_app_credentials(
    access_key: str = Header(..., alias="X-Access-Key"),
    access_secret: str = Header(..., alias="X-Access-Secret")
):
    from asgiref.sync import sync_to_async
    try:
        app = await sync_to_async(Application.objects.get)(
            access_key=access_key, is_active=True
        )
    except Application.DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid application credentials")
    
    if not app.verify_secret(access_secret):
        raise HTTPException(status_code=401, detail="Invalid application credentials")
    return app

@app.get("/protected")
async def protected_endpoint(app = Security(verify_app_credentials)):
    return {"message": f"Hello from {app.name}"}
```

---

## Next Steps

- [Task Service](task_service.md) — Background job processing with AsyncIOTaskService
- [Async Guide](async_guide.md) — Deep dive into async patterns with Tenxyte
- [Architecture](architecture.md) — Understanding Ports and Adapters
- [Settings Reference](settings.md) — All configuration options
- [Custom Adapters](custom_adapters.md) — Build your own adapters

---

## Comparison: Django vs FastAPI

| Feature | Django | FastAPI |
|---------|--------|---------|
| Setup | `tenxyte.setup()` | Manual service initialization |
| ORM | Django ORM (built-in) | SQLAlchemy, Tortoise, or any async ORM |
| Task Queue | Celery, RQ, or threads | Native asyncio |
| Auth Middleware | Automatic | Manual dependency injection |
| Admin Panel | Built-in | Requires custom implementation |
| Async Support | Partial (Django 4.2+) | Native |

Both frameworks use the **same Core services** — your authentication logic is portable!
