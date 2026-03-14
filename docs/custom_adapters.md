# Creating Custom Adapters

Tenxyte's **Ports and Adapters** architecture makes it incredibly easy to extend or replace specific parts of the system without modifying the core logic.

If you are using a framework other than Django or FastAPI, or if you want to use a different database ORM, caching system, or SMS provider, you can write your own custom adapters.

## The Concept

The Core logic relies on abstract interfaces called **Ports**. You can find these defined in the `tenxyte.ports` module.

To use a custom implementation, you just need to create a class that inherits from the relevant Port, implement the required methods, and pass your adapter instance to the Core services.

## Example 1: Custom Cache Service

Suppose you want to use a custom Redis implementation instead of the default cache, or maybe a simple in-memory dictionary for testing.

```python
from tenxyte.ports.services import CacheService
import redis

class RedisCacheAdapter(CacheService):
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.client = redis.from_url(redis_url)

    def get(self, key: str) -> str | None:
        val = self.client.get(key)
        return val.decode("utf-8") if val else None

    def set(self, key: str, value: str, timeout: int = None) -> None:
        self.client.set(key, value, ex=timeout)

    def delete(self, key: str) -> None:
        self.client.delete(key)
```

## Example 2: Custom Email Service

If you want to use a provider that Tenxyte doesn't natively support (e.g., Postmark or Mailgun), you implement the `EmailService` port.

```python
from tenxyte.ports.services import EmailService
import requests

class PostmarkEmailAdapter(EmailService):
    def __init__(self, api_token: str, from_email: str):
        self.api_token = api_token
        self.from_email = from_email

    def send_email(self, to_email: str, subject: str, body: str, html_body: str = None) -> bool:
        response = requests.post(
            "https://api.postmarkapp.com/email",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": self.api_token
            },
            json={
                "From": self.from_email,
                "To": to_email,
                "Subject": subject,
                "TextBody": body,
                "HtmlBody": html_body
            }
        )
        return response.status_code == 200
```

## Example 3: Custom Repositories (Database ORM)

Repositories are how the Core reads and writes entities (Users, Roles, Organizations) from the database. If you are integrating Tenxyte with a custom internal database system or a different ORM like Prisma or Tortoise ORM, you need to implement the repository ports.

```python
from tenxyte.ports.repositories import UserRepository
from tenxyte.core.models import UserEntity # The core data class

class CustomInternalUserRepository(UserRepository):
    def get_by_id(self, user_id: str) -> UserEntity | None:
        # custom database logic
        pass
        
    def get_by_email(self, email: str) -> UserEntity | None:
        # custom database logic
        pass
        
    def create(self, user_data: dict) -> UserEntity:
        # custom database logic
        pass

    def update(self, user_id: str, update_data: dict) -> UserEntity:
        # custom database logic
        pass
```

## Wiring it all together

Once you have your custom adapters, you pass them into the core services when initializing your application.

```python
from tenxyte.core.services.auth import AuthService
from tenxyte.core.settings import Settings

# 1. Initialize your custom adapters
my_cache = RedisCacheAdapter()
my_email = PostmarkEmailAdapter(api_token="...", from_email="...")
my_user_repo = CustomInternalUserRepository()

# 2. Configure the core settings
settings = Settings(
    TENXYTE_JWT_SECRET_KEY="your-secret-key",
    # ...
)

# 3. Instantiate the core services with your custom adapters
auth_service = AuthService(
    user_repo=my_user_repo,
    cache_service=my_cache,
    email_service=my_email,
    settings=settings
)

# 4. Use the core service in your framework's endpoints!
# token = auth_service.login_with_email("user@example.com", "password123")
```

By adhering to the abstract interfaces defined in `tenxyte.ports`, your custom adapters are guaranteed to be fully compatible with Tenxyte's internal security logic, 2FA, JWT generation, and RBAC systems.
