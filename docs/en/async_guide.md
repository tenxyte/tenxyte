# Async/Await Guide

Tenxyte Core services provide first-class support for asynchronous operations through `async`/`await` patterns. This guide explains how to use the async methods effectively in both FastAPI and Django applications.

## Table of Contents

- [Overview](#overview)
- [Async Methods Reference](#async-methods-reference)
  - [CacheService](#cacheservice)
  - [JWTService](#jwtservice)
  - [TOTPService](#totpservice)
  - [MagicLinkService](#magiclinkservice)
  - [SessionService](#sessionservice)
  - [TaskService](#taskservice)
- [When to Use Async vs Sync](#when-to-use-async-vs-sync)
- [Framework-Specific Patterns](#framework-specific-patterns)
  - [FastAPI (Native Async)](#fastapi-native-async)
  - [Django (Async-Compatible)](#django-async-compatible)
- [Performance Considerations](#performance-considerations)
- [Common Pitfalls](#common-pitfalls)

---

## Overview

All Tenxyte Core services provide both synchronous and asynchronous versions of their methods:

```python
# Synchronous (blocks until completion)
token = jwt_service.generate_access_token(user_id="123")

# Asynchronous (yields control to event loop)
token = await jwt_service.generate_access_token_async(user_id="123")
```

**Key benefits of using async:**
- Non-blocking I/O operations
- Better concurrency handling
- Improved throughput for I/O-bound operations
- Native integration with FastAPI and modern async frameworks

---

## Async Methods Reference

### CacheService

All cache operations have async variants that delegate to the underlying cache backend asynchronously:

```python
from tenxyte.core.cache_service import InMemoryCacheService

cache = InMemoryCacheService()

# Basic operations
await cache.set_async("key", "value", timeout=3600)
value = await cache.get_async("key")
exists = await cache.exists_async("key")
await cache.delete_async("key")

# Counter operations
count = await cache.increment_async("counter", delta=1)

# Rate limiting (returns: allowed, remaining, reset_time)
allowed, remaining, reset = await cache.check_rate_limit_async(
    key="rate:user:123",
    max_requests=100,
    window_seconds=60
)

# Token blacklisting (JWT revocation)
await cache.add_to_blacklist_async(jti="token-id", expires_in=3600)
is_blacklisted = await cache.is_blacklisted_async("token-id")
```

### JWTService

Token operations support async for non-blocking validation and blacklisting:

```python
from tenxyte.core.jwt_service import JWTService

jwt_svc = JWTService(settings=settings, blacklist_service=cache)

# Generate tokens (sync only - cryptographic operations)
access_token, jti, exp = jwt_svc.generate_access_token(user_id="123")
refresh_token = jwt_svc.generate_refresh_token(user_id="123")

# Decode and validate (async)
decoded = await jwt_svc.decode_token_async(token)
if decoded and decoded.is_valid:
    print(f"User: {decoded.user_id}")

# Blacklisting (async I/O)
await jwt_svc.blacklist_token_async(token, user_id="123")
await jwt_svc.blacklist_token_by_jti_async(jti="token-id", expires_at=datetime)

# Refresh tokens (async)
new_tokens = await jwt_svc.refresh_tokens_async(refresh_token)
if new_tokens:
    print(f"New access token: {new_tokens.access_token}")

# User-level revocation (async)
await jwt_svc.revoke_all_user_tokens_async(user_id="123")
```

### TOTPService

Two-factor authentication with async storage adapters:

```python
from tenxyte.core.totp_service import TOTPService

totp_svc = TOTPService(settings=settings)

# Setup 2FA (async with storage)
result = await totp_svc.setup_2fa_async(
    user_id="123",
    email="user@example.com",
    storage=async_storage_adapter
)
# Returns: secret, qr_code (base64), backup_codes

# Confirm setup with initial code
ok, error = await totp_svc.confirm_2fa_setup_async(
    user_id="123",
    code="123456",
    storage=async_storage_adapter
)

# Verify during login
ok, error = await totp_svc.verify_2fa_async(
    user_id="123",
    code="123456",
    storage=async_storage_adapter
)
# Returns (True, "") for valid code
# Returns (True, "") if 2FA not enabled (passthrough)
# Returns (False, "error message") for invalid

# Disable 2FA
ok, error = await totp_svc.disable_2fa_async(
    user_id="123",
    code="123456",
    storage=async_storage_adapter
)

# Regenerate backup codes
ok, new_codes, error = await totp_svc.regenerate_backup_codes_async(
    user_id="123",
    code="123456",  # Current TOTP or backup code
    storage=async_storage_adapter
)

# Verify standalone code (for inline checks)
is_valid = await totp_svc.verify_code_async(
    secret=decrypted_secret,
    code="123456",
    user_id="123"  # Optional: for replay protection
)
```

### MagicLinkService

Passwordless authentication with async operations:

```python
from tenxyte.core.magic_link_service import MagicLinkService

magic_svc = MagicLinkService(
    settings=settings,
    email_service=email_service,
    repo=async_repo,
    user_lookup=async_user_lookup
)

# Request magic link (sends email asynchronously)
success, error = await magic_svc.request_magic_link_async(
    email="user@example.com",
    application_id="app-123",
    ip_address="1.2.3.4",
    user_agent="Mozilla/5.0..."
)

# Verify token from link
result = await magic_svc.verify_magic_link_async(
    token="token-from-url",
    application_id="app-123",
    ip_address="1.2.3.4",
    require_same_device=True  # Optional: IP matching
)
# Returns MagicLinkResult with:
# - success: bool
# - user_id: str (if success)
# - error: str (if failed)
```

### SessionService

Session management with async cache and repository operations:

```python
from tenxyte.core.session_service import SessionService

session_svc = SessionService(
    settings=settings,
    cache_service=async_cache,
    session_repository=async_repo
)

# Create session
session_data = await session_svc.create_session_async(
    user=user,
    device_id="device-123",
    ip_address="1.2.3.4",
    user_agent="Mozilla/5.0...",
    application_id="app-123"
)
# Returns dict with session_id, device_fingerprint, etc.

# Validate session
session = await session_svc.validate_session_async(session_id)
if session:
    print(f"Valid session for user: {session['user_id']}")

# Revoke single session
await session_svc.revoke_session_async(session_id)

# Revoke all user sessions
revoked_count = await session_svc.revoke_all_sessions_async(
    user_id="123",
    except_session_id="keep-this-one"  # Optional
)
```

### TaskService

Background job execution with async support:

```python
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

task_svc = AsyncIOTaskService()

# Enqueue sync function (runs in thread pool)
task_id = await task_svc.enqueue_async(send_email, user_id, message)

# Enqueue async function (runs as asyncio task)
task_id = await task_svc.enqueue_async(async_webhook_call, payload)

# Base implementation falls back to to_thread for sync adapters
# Native async adapters (AsyncIOTaskService) handle both optimally
```

---

## When to Use Async vs Sync

### Use Async When:

| Scenario | Reason |
|----------|--------|
| FastAPI endpoints | Native async framework; blocking sync calls hurt performance |
| I/O operations (cache, DB, email) | Don't block the event loop waiting for network/disk |
| Concurrent token validation | Process multiple requests simultaneously |
| Rate limiting checks | Quick async cache lookups |
| Token blacklisting | Non-blocking write to cache/DB |

### Use Sync When:

| Scenario | Reason |
----------|--------|
| Cryptographic operations | `jwt.encode()` is CPU-bound, not I/O; async adds overhead |
| TOTP code generation | `pyotp` is synchronous and fast; no I/O |
| Password hashing | `bcrypt` is CPU-bound; use sync |
| Single-threaded scripts | Simpler, no event loop needed |
| Django views (non-async) | Traditional Django is sync-first |

### Example: Choosing the Right Method

```python
from tenxyte.core.jwt_service import JWTService

jwt_svc = JWTService(settings=settings)

# FastAPI endpoint - use async
def create_access_token_async(user_id: str) -> str:
    # generate_access_token is sync (crypto), but that's OK
    # It's fast and CPU-bound
    token, _, _ = jwt_svc.generate_access_token(user_id)
    return token

# FastAPI endpoint - validate with async
def validate_token_async(token: str) -> Optional[DecodedToken]:
    # decode_token_async allows other requests to proceed
    # while we check the blacklist (I/O operation)
    return await jwt_svc.decode_token_async(token)

# Background task - send revocation notice
def notify_logout_async(user_id: str, token: str):
    # Blacklist check and add are I/O
    await jwt_svc.blacklist_token_async(token, user_id)
```

---

## Framework-Specific Patterns

### FastAPI (Native Async)

FastAPI is designed for async. Use `async def` for all endpoints and prefer async Tenxyte methods:

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

# Initialize services
jwt_svc = JWTService(settings=settings, blacklist_service=cache)

@app.post("/auth/login")
async def login(credentials: LoginCredentials):
    # Sync is fine for crypto operations
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    
    access_token, _, _ = jwt_svc.generate_access_token(str(user.id))
    return {"access": access_token}

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    
    # Use async validation to not block other requests
    decoded = await jwt_svc.decode_token_async(token)
    
    if not decoded or not decoded.is_valid:
        raise HTTPException(401, "Invalid token")
    
    if decoded.is_blacklisted:
        raise HTTPException(401, "Token revoked")
    
    return {"user_id": decoded.user_id}

@app.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    
    # Async blacklisting
    await jwt_svc.blacklist_token_async(token)
    
    return {"status": "logged_out"}
```

### Django (Async-Compatible)

Django 4.2+ supports async views. Use `async def` with Tenxyte's async methods:

```python
# views.py
from django.http import JsonResponse
from django.views import View
from asgiref.sync import sync_to_async

from tenxyte.core.jwt_service import JWTService

jwt_svc = JWTService(settings=settings)

# Async class-based view
class AsyncProtectedView(View):
    async def get(self, request):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        
        # Async token validation
        decoded = await jwt_svc.decode_token_async(token)
        
        if not decoded or not decoded.is_valid:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        
        # For ORM operations, wrap sync calls
        user = await sync_to_async(User.objects.get)(id=decoded.user_id)
        
        return JsonResponse({"user": user.email})

# Async function-based view
async def async_logout(request):
    token = extract_token_from_request(request)
    
    # Async blacklisting
    await jwt_svc.blacklist_token_async(token)
    
    return JsonResponse({"status": "logged_out"})
```

**Note:** Django's ORM is still primarily synchronous. Use `sync_to_async` wrapper:

```python
from asgiref.sync import sync_to_async

# Wrap ORM calls
user = await sync_to_async(User.objects.get)(id=user_id)
sessions = await sync_to_async(list)(UserSession.objects.filter(user_id=user_id))
```

---

## Performance Considerations

### Thread Pool vs Native Async

| Adapter | `enqueue()` | `enqueue_async()` | Best For |
|---------|-------------|-------------------|----------|
| `AsyncIOTaskService` | `run_in_executor` (thread pool) | `create_task` for coroutines | FastAPI, pure async |
| `CeleryTaskService` | Celery worker | `to_thread` fallback | Distributed, heavy tasks |
| `RQTaskService` | RQ worker | `to_thread` fallback | Redis-based queue |
| `SyncThreadTaskService` | `Thread` | `to_thread` fallback | Dev, no dependencies |

### Async Method Implementation Details

```python
# CacheService async methods:
# - InMemoryCacheService: Uses to_thread (locks are sync)
# - RedisCacheService: Uses redis-py async client (truly async I/O)

# JWTService async methods:
# - decode_token_async: Async blacklist check (I/O)
# - blacklist_token_async: Async cache write (I/O)
# - refresh_tokens_async: Async DB/cache operations

# All other crypto operations remain sync (CPU-bound)
```

### Benchmark: Sync vs Async Blacklist Check

```python
import asyncio
import time

# Simulating 100 concurrent token validations
async def benchmark():
    tokens = [generate_test_token() for _ in range(100)]
    
    # Sync version (blocking)
    start = time.time()
    for token in tokens:
        jwt_svc.decode_token(token)  # Blocking I/O
    sync_time = time.time() - start
    
    # Async version (concurrent)
    start = time.time()
    await asyncio.gather(*[
        jwt_svc.decode_token_async(token) for token in tokens
    ])
    async_time = time.time() - start
    
    print(f"Sync: {sync_time:.2f}s, Async: {async_time:.2f}s")
    # Typical result: Async 5-10x faster for I/O-bound operations

asyncio.run(benchmark())
```

---

## Common Pitfalls

### 1. Forgetting `await`

```python
# WRONG: Returns a coroutine object, not the result
decoded = jwt_svc.decode_token_async(token)  # Missing await!
if decoded.is_valid:  # AttributeError: 'coroutine' object has no attribute 'is_valid'
    ...

# CORRECT:
decoded = await jwt_svc.decode_token_async(token)
```

### 2. Calling Async in Sync Context Without Event Loop

```python
# WRONG: Can't await outside async function
def sync_function():
    result = await cache.get_async("key")  # SyntaxError

# CORRECT: Use asyncio.run() or async def
async def async_function():
    result = await cache.get_async("key")

# Or for quick scripts:
import asyncio
result = asyncio.run(cache.get_async("key"))
```

### 3. Blocking the Event Loop in Async Context

```python
# WRONG: Blocks entire event loop
async def bad_endpoint():
    time.sleep(5)  # Blocks ALL concurrent requests!
    return {"done": True}

# CORRECT: Use async sleep or run in executor
async def good_endpoint():
    await asyncio.sleep(5)  # Yields to other requests
    # OR for sync I/O:
    await asyncio.to_thread(blocking_io_function)
    return {"done": True}
```

### 4. Using Sync Methods in FastAPI Without Care

```python
# WRONG in FastAPI: Blocks the event loop
@app.get("/slow")
def slow_endpoint():  # Notice: def, not async def
    time.sleep(10)  # Blocks all other requests!
    return {"done": True}

# CORRECT:
@app.get("/slow")
async def fast_endpoint():
    await asyncio.sleep(10)  # Other requests proceed
    return {"done": True}
```

### 5. Mixing Async and Django ORM Incorrectly

```python
# WRONG: Direct ORM call in async view
async def bad_view(request):
    user = User.objects.get(id=1)  # Synchronous I/O in async context!

# CORRECT: Wrap ORM with sync_to_async
from asgiref.sync import sync_to_async

async def good_view(request):
    user = await sync_to_async(User.objects.get)(id=1)
    # OR for queries returning multiple objects:
    users = await sync_to_async(list)(User.objects.all())
```

---

## Quick Reference: Async Method Cheat Sheet

```python
# CacheService
await cache.get_async(key)
await cache.set_async(key, value, timeout)
await cache.delete_async(key)
await cache.exists_async(key)
await cache.increment_async(key, delta)
await cache.expire_async(key, timeout)
await cache.ttl_async(key)
await cache.add_to_blacklist_async(jti, expires_in)
await cache.is_blacklisted_async(jti)
await cache.remove_from_blacklist_async(jti)
await cache.check_rate_limit_async(key, max_requests, window_seconds)
await cache.reset_rate_limit_async(key)

# JWTService
decoded = await jwt_svc.decode_token_async(token)
await jwt_svc.blacklist_token_async(token, user_id)
await jwt_svc.blacklist_token_by_jti_async(jti, expires_at, user_id)
tokens = await jwt_svc.refresh_tokens_async(refresh_token)
await jwt_svc.revoke_all_user_tokens_async(user_id)

# TOTPService
setup = await totp_svc.setup_2fa_async(user_id, email, storage)
ok, err = await totp_svc.confirm_2fa_setup_async(user_id, code, storage)
ok, err = await totp_svc.verify_2fa_async(user_id, code, storage)
ok, err = await totp_svc.disable_2fa_async(user_id, code, storage)
ok, codes, err = await totp_svc.regenerate_backup_codes_async(user_id, code, storage)
is_valid = await totp_svc.verify_code_async(secret, code, user_id)

# MagicLinkService
ok, err = await magic_svc.request_magic_link_async(email, ...)
result = await magic_svc.verify_magic_link_async(token, ...)

# SessionService
session = await session_svc.create_session_async(user, ...)
session = await session_svc.validate_session_async(session_id)
await session_svc.revoke_session_async(session_id)
count = await session_svc.revoke_all_sessions_async(user_id)

# TaskService
task_id = await task_svc.enqueue_async(func, *args, **kwargs)
```

---

## Next Steps

- [Task Service](task_service.md) — Background job processing
- [FastAPI Quickstart](fastapi_quickstart.md) — Complete FastAPI setup
- [Architecture](architecture.md) — Understanding Ports and Adapters
