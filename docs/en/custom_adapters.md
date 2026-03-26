# Creating Custom Adapters

Tenxyte's **Ports and Adapters** architecture makes it incredibly easy to extend or replace specific parts of the system without modifying the core logic.

If you are using a framework other than Django or FastAPI, or if you want to use a different database ORM, caching system, or SMS provider, you can write your own custom adapters.

## The Concept

The Core logic relies on abstract interfaces called **Ports**. These are defined in two locations:

- **`tenxyte.ports`** — Repository interfaces (`UserRepository`, `OrganizationRepository`, `RoleRepository`, `AuditLogRepository`) and service protocols (`EmailService`, `CacheService`).
- **`tenxyte.core`** — Core service ABCs (`EmailService`, `CacheService`, `JWTService`, `TOTPService`, etc.) with richer base implementations.

To use a custom implementation, you just need to create a class that inherits from the relevant abstract base class, implement the required methods, and pass your adapter instance to the Core services.

## Example 1: Custom Cache Service

The `CacheService` ABC (defined in `tenxyte.core.cache_service`) requires implementing seven abstract methods: `get`, `set`, `delete`, `exists`, `increment`, `expire`, and `ttl`.

Suppose you want to use Redis:

```python
from tenxyte.core.cache_service import CacheService
from typing import Any, Optional
import redis

class RedisCacheAdapter(CacheService):
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.client = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[Any]:
        val = self.client.get(key)
        return val.decode("utf-8") if val else None

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        self.client.set(key, value, ex=timeout)
        return True

    def delete(self, key: str) -> bool:
        self.client.delete(key)
        return True

    def exists(self, key: str) -> bool:
        return bool(self.client.exists(key))

    def increment(self, key: str, delta: int = 1) -> int:
        return self.client.incr(key, delta)

    def expire(self, key: str, timeout: int) -> bool:
        return bool(self.client.expire(key, timeout))

    def ttl(self, key: str) -> int:
        return self.client.ttl(key)
```

> **Note:** The `CacheService` base class also provides built-in convenience methods `add_to_blacklist`, `is_blacklisted`, `check_rate_limit`, and `reset_rate_limit` which work automatically once the abstract methods are implemented.

## Example 2: Custom Email Service

The `EmailService` ABC (defined in `tenxyte.core.email_service`) requires implementing one abstract method: `send`. Higher-level methods like `send_magic_link`, `send_two_factor_code`, `send_password_reset`, etc. are already implemented in the base class by calling `send`.

```python
from tenxyte.core.email_service import EmailService
from typing import List, Optional
import requests

class PostmarkEmailAdapter(EmailService):
    def __init__(self, api_token: str, from_email: str):
        self.api_token = api_token
        self.from_email = from_email

    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments=None,
    ) -> bool:
        response = requests.post(
            "https://api.postmarkapp.com/email",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": self.api_token
            },
            json={
                "From": from_email or self.from_email,
                "To": to_email,
                "Subject": subject,
                "TextBody": body,
                "HtmlBody": html_body
            }
        )
        return response.status_code == 200
```

## Example 3: Custom Repositories (Database ORM)

Repositories are how the Core reads and writes entities (Users, Roles, Organizations) from the database. The `UserRepository` ABC is defined in `tenxyte.ports.repositories` and uses the `User` dataclass from the same module.

```python
from tenxyte.ports.repositories import UserRepository, User
from typing import Any, Dict, List, Optional
from datetime import datetime

class CustomUserRepository(UserRepository):
    def get_by_id(self, user_id: str) -> Optional[User]:
        # custom database logic
        pass

    def get_by_email(self, email: str) -> Optional[User]:
        # custom database logic
        pass

    def create(self, user: User) -> User:
        # custom database logic — receives a User dataclass
        pass

    def update(self, user: User) -> User:
        # custom database logic — receives a User dataclass
        pass

    def delete(self, user_id: str) -> bool:
        pass

    def list_all(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[User]:
        pass

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        pass

    def update_last_login(self, user_id: str, timestamp: datetime) -> bool:
        pass

    def set_mfa_secret(self, user_id: str, mfa_type, secret: str) -> bool:
        pass

    def verify_email(self, user_id: str) -> bool:
        pass
```

## Example 4: Custom Task Service

The `TaskService` ABC (defined in `tenxyte.core.task_service`) provides an interface for background job execution. It requires implementing the `enqueue` method for synchronous execution, and optionally `_enqueue_async_native` for native async support.

### Basic Sync-Only Adapter

```python
from tenxyte.core.task_service import TaskService
from typing import Any, Callable
import my_task_queue

class CustomTaskService(TaskService):
    """
    Adapter for a custom task queue (e.g., Huey, ARQ, or custom implementation).
    """
    
    def __init__(self, queue_url: str):
        self.client = my_task_queue.Client(queue_url)
    
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Enqueue a synchronous function to run in the background.
        Must return a task ID string.
        """
        job = self.client.submit(func, args=args, kwargs=kwargs)
        return job.id
```

### Full Async Adapter

For optimal performance in async applications (FastAPI), implement native async support:

```python
from tenxyte.core.task_service import TaskService
from typing import Any, Callable, Coroutine, Union
import asyncio

class AsyncCustomTaskService(TaskService):
    """
    Full async task service adapter with native coroutine support.
    """
    
    def __init__(self, queue_url: str):
        self.sync_client = my_task_queue.Client(queue_url)
        self.async_client = my_task_queue.AsyncClient(queue_url)
    
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """Sync enqueue - runs in background worker."""
        job = self.sync_client.submit(func, args=args, kwargs=kwargs)
        return job.id
    
    async def _enqueue_async_native(
        self, 
        func: Union[Callable[..., Coroutine[Any, Any, Any]], Callable[..., Any]], 
        *args: Any, 
        **kwargs: Any
    ) -> str:
        """
        Native async enqueue - used by enqueue_async() automatically.
        This method is called by the base class when available.
        """
        if asyncio.iscoroutinefunction(func):
            # It's an async function - create the coroutine and submit
            coro = func(*args, **kwargs)
            job = await self.async_client.submit_coro(coro)
        else:
            # It's a sync function - submit to async client
            job = await self.async_client.submit(func, args=args, kwargs=kwargs)
        return job.id
```

### Usage Example

```python
# Initialize your custom adapter
task_service = AsyncCustomTaskService("https://queue.example.com")

# Enqueue sync function
job_id = task_service.enqueue(send_email, user_id=123, subject="Welcome")

# Enqueue async function (works in async context)
await task_service.enqueue_async(async_webhook_call, payload=data)

# Both work transparently with Tenxyte services
from tenxyte.core.magic_link_service import MagicLinkService

magic_link_service = MagicLinkService(
    settings=settings,
    email_service=email_service,
    repo=repo,
    user_lookup=user_lookup,
    task_service=task_service  # Injected for async email sending
)
```

> **Note:** If you only implement `enqueue()`, the base class `enqueue_async()` will automatically fall back to running `enqueue()` in a thread pool using `asyncio.to_thread()`. Implementing `_enqueue_async_native()` is optional but recommended for better performance in async applications.

---

## Wiring it all together

Once you have your custom adapters, you pass them into the Core services when initializing your application. Each Core service (e.g., `JWTService`, `TOTPService`, `MagicLinkService`) accepts specific dependencies in its constructor.

```python
from tenxyte.core.settings import Settings, init
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.jwt_service import JWTService

# 1. Initialize your custom adapters
my_cache = RedisCacheAdapter()
my_email = PostmarkEmailAdapter(api_token="...", from_email="...")
my_user_repo = CustomUserRepository()

# 2. Configure the core settings with a provider
#    (reads TENXYTE_* from environment variables)
settings = init(provider=EnvSettingsProvider())

# 3. Instantiate the core services
jwt_service = JWTService(settings=settings)

# 4. Use the core services in your framework's endpoints!
# token_pair = jwt_service.generate_token_pair(user_id="123", ...)
```

> **Tip:** For Django projects, the `DjangoSettingsProvider` adapter reads `TENXYTE_*` settings from `django.conf.settings` automatically. For FastAPI, use `EnvSettingsProvider` or pass the settings directly.

By implementing the abstract methods defined in `tenxyte.core` and `tenxyte.ports`, your custom adapters are guaranteed to be fully compatible with Tenxyte's internal security logic, 2FA, JWT generation, and RBAC systems.
