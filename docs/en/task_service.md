# Task Service — Background Jobs

Tenxyte provides a unified abstraction for executing background tasks through the `TaskService` port. This allows your application to enqueue jobs without coupling to specific implementations like Celery, RQ, or FastAPI BackgroundTasks.

## Table of Contents

- [The TaskService Port](#the-taskservice-port)
- [Available Adapters](#available-adapters)
  - [Django Adapters](#django-adapters)
  - [FastAPI Adapter](#fastapi-adapter)
- [Usage Examples](#usage-examples)
  - [Enqueueing Synchronous Tasks](#enqueueing-synchronous-tasks)
  - [Enqueueing Asynchronous Tasks](#enqueueing-asynchronous-tasks)
- [Configuration by Framework](#configuration-by-framework)
  - [Django Configuration](#django-configuration)
  - [FastAPI Configuration](#fastapi-configuration)
- [Creating Custom TaskService Adapters](#creating-custom-taskservice-adapters)

---

## The TaskService Port

The `TaskService` abstract base class is defined in `tenxyte.core.task_service` and provides two methods:

| Method | Description |
|--------|-------------|
| `enqueue(func, *args, **kwargs)` | Enqueue a synchronous function to run in the background. Returns a task ID string. |
| `enqueue_async(func, *args, **kwargs)` | Enqueue a function (sync or async) non-blockingly. Auto-detects coroutines and handles them natively. |

The base class implementation of `enqueue_async` dynamically delegates to a native async method (`_enqueue_async_native`) if available, or falls back to running the synchronous `enqueue` in a thread pool using `asyncio.to_thread()`.

---

## Available Adapters

### Django Adapters

Located in `tenxyte.adapters.django.task_service`:

| Adapter | Description | When to Use |
|---------|-------------|-------------|
| `SyncThreadTaskService` | Runs tasks in a background thread using Python's `threading` module. | Development, testing, or when you don't want external dependencies. Zero configuration required. |
| `CeleryTaskService` | Delegates to Celery's task queue. | Production Django with Celery already configured. |
| `RQTaskService` | Delegates to Django-RQ. | Production Django with Redis Queue (RQ). |

#### SyncThreadTaskService

```python
from tenxyte.adapters.django.task_service import SyncThreadTaskService

task_service = SyncThreadTaskService()

# Send welcome email in background
def send_welcome_email(user_id):
    user = User.objects.get(id=user_id)
    # ... send email logic

task_id = task_service.enqueue(send_welcome_email, user.id)
print(f"Task started: {task_id}")  # Returns thread name
```

#### CeleryTaskService

```python
from tenxyte.adapters.django.task_service import CeleryTaskService
from celery import shared_task

task_service = CeleryTaskService()

# Option 1: Use existing Celery task
@shared_task
def process_report(report_id):
    # ... heavy processing
    pass

task_id = task_service.enqueue(process_report, report_id=123)

# Option 2: Use regular function (auto-wrapped in Celery task)
def cleanup_old_sessions():
    Session.objects.filter(expires__lt=timezone.now()).delete()

task_id = task_service.enqueue(cleanup_old_sessions)
```

**Requirements:**
```bash
pip install tenxyte[django] celery
```

#### RQTaskService

```python
from tenxyte.adapters.django.task_service import RQTaskService

task_service = RQTaskService(queue_name="high")  # or "default"

def generate_pdf(invoice_id):
    # ... PDF generation logic
    pass

task_id = task_service.enqueue(generate_pdf, invoice_id=456)
```

**Requirements:**
```bash
pip install tenxyte[django] django-rq
```

---

### FastAPI Adapter

Located in `tenxyte.adapters.fastapi.task_service`:

| Adapter | Description | When to Use |
|---------|-------------|-------------|
| `AsyncIOTaskService` | Native asyncio-based background execution using `asyncio.create_task()` and thread pools. | FastAPI applications or any pure async Python application. |

#### AsyncIOTaskService

```python
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService
from fastapi import FastAPI

app = FastAPI()
task_service = AsyncIOTaskService()

# Sync function - runs in thread pool
def send_sms_notification(phone_number: str, message: str):
    # ... synchronous SMS API call
    pass

# Async function - runs as asyncio task
async def process_webhook(data: dict):
    # ... async HTTP calls to external services
    async with httpx.AsyncClient() as client:
        await client.post("https://partner-api.example.com/webhook", json=data)

@app.post("/orders/")
async def create_order(order: OrderCreate):
    # Save order (sync DB call)
    order_id = await save_order(order)
    
    # Enqueue background tasks without blocking response
    await task_service.enqueue_async(send_sms_notification, order.customer_phone, "Order received!")
    await task_service.enqueue_async(process_webhook, {"order_id": order_id, "status": "created"})
    
    return {"order_id": order_id, "status": "created"}
```

**Key features:**
- Automatically detects if function is sync or async
- Async functions run as `asyncio.Task` (non-blocking, same event loop)
- Sync functions run in `loop.run_in_executor()` (thread pool)
- Exception handling built-in with logging

**Requirements:**
```bash
pip install tenxyte[fastapi]
```

---

## Usage Examples

### Enqueueing Synchronous Tasks

All adapters support the synchronous `enqueue()` method:

```python
from tenxyte.core.task_service import TaskService

def heavy_computation(data: list) -> dict:
    """Some CPU-intensive work."""
    results = []
    for item in data:
        results.append(process_item(item))
    return {"processed": len(results)}

# In your view/endpoint
job_id = task_service.enqueue(heavy_computation, large_dataset)
# Returns immediately, computation runs in background
```

### Enqueueing Asynchronous Tasks

Use `enqueue_async()` for non-blocking execution, especially in async contexts:

```python
# In an async endpoint
async def handle_request(request):
    # This won't block the response even if the task is sync
    await task_service.enqueue_async(send_notification, user_id, message)
    return {"status": "accepted"}
```

**Behavior by adapter:**
- **AsyncIOTaskService**: Async functions run as native `asyncio.Task`; sync functions use thread pool
- **CeleryTaskService/RQTaskService/SyncThreadTaskService**: Falls back to `asyncio.to_thread(self.enqueue, ...)`

---

## Configuration by Framework

### Django Configuration

Add the task service to your settings or use dependency injection:

```python
# settings.py
TENXYTE_TASK_SERVICE_CLASS = "tenxyte.adapters.django.task_service.CeleryTaskService"
TENXYTE_TASK_SERVICE_QUEUE = "default"  # For RQTaskService

# Or in your service layer
from tenxyte.adapters.django.task_service import CeleryTaskService
from tenxyte.core.email_service import EmailService

class AuthService:
    def __init__(self):
        self.task_service = CeleryTaskService()
        self.email_service = EmailService()
    
    def send_magic_link(self, user_id: str, email: str):
        # Generate magic link synchronously
        token = self.generate_magic_token(user_id)
        
        # Send email asynchronously
        self.task_service.enqueue(
            self.email_service.send_magic_link,
            to_email=email,
            magic_link_url=f"https://app.example.com/magic?token={token}",
            expires_in_minutes=15
        )
```

### FastAPI Configuration

With FastAPI, instantiate the service and inject it via dependency:

```python
# dependencies.py
from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService

task_service = AsyncIOTaskService()

async def get_task_service() -> AsyncIOTaskService:
    return task_service

# main.py
from fastapi import Depends
from dependencies import get_task_service

@app.post("/auth/magic-link/")
async def request_magic_link(
    email: str,
    task_service: AsyncIOTaskService = Depends(get_task_service)
):
    # Validate email exists
    user = await find_user_by_email(email)
    if not user:
        return {"status": "if_exists_sent"}  # Don't reveal if email exists
    
    # Send magic link in background (async email service call)
    await task_service.enqueue_async(
        email_service.send_magic_link_async,
        to_email=email,
        magic_link_url=generate_magic_link(user.id),
        expires_in_minutes=15
    )
    
    return {"status": "if_exists_sent"}
```

---

## Creating Custom TaskService Adapters

To integrate with a different task queue system (e.g., Huey, ARQ, or a custom queue), implement the `TaskService` ABC:

```python
from tenxyte.core.task_service import TaskService
from typing import Any, Callable
import my_custom_queue

class CustomQueueTaskService(TaskService):
    """
    Adapter for a custom task queue system.
    """
    
    def __init__(self, queue_url: str):
        self.client = my_custom_queue.Client(queue_url)
    
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Enqueue a synchronous function.
        """
        # Serialize the function call
        job = self.client.submit(func, args=args, kwargs=kwargs)
        return job.id
    
    # Optional: Implement native async support for better performance
    async def _enqueue_async_native(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> str:
        """
        Optional native async implementation.
        If provided, enqueue_async() will use this instead of to_thread().
        """
        # If your queue has an async client
        job = await self.client.async_submit(func, args=args, kwargs=kwargs)
        return job.id
```

Then use it:

```python
task_service = CustomQueueTaskService("https://queue.example.com")

# Both sync and async usage work
task_service.enqueue(sync_function, arg1, arg2)
await task_service.enqueue_async(async_or_sync_function, arg1, arg2)
```

---

## Next Steps

- [Async Guide](async_guide.md) — Deep dive into async/await patterns with Tenxyte
- [FastAPI Quickstart](fastapi_quickstart.md) — Complete FastAPI setup guide
- [Custom Adapters](custom_adapters.md) — Creating adapters for other services (Cache, Email, etc.)
