# Applications Guide — API Client Management

Tenxyte provides a built-in `Application` model to manage multiple API clients (such as Web apps, Mobile apps, testing scripts, or B2B integrations). Each application gets its own `access_key` and `access_secret` which are required to authenticate API requests.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [API Usage](#api-usage)
  - [Create an Application](#create-an-application)
  - [List Applications](#list-applications)
  - [Get Application Details](#get-application-details)
  - [Update an Application](#update-an-application)
  - [Regenerate Credentials](#regenerate-credentials)
  - [Delete an Application](#delete-an-application)
- [Security Notes](#security-notes)
- [Python API](#python-api)
- [Data Model](#data-model)

---

## Overview

In modern systems, a backend usually serves multiple clients. Instead of using a single global API key or hardcoding credentials, Tenxyte allows you to generate distinct keys for each client. 

For example, you could have:
- `Web Frontend` App
- `iOS Mobile` App
- `Partner X Integration` App

By passing the `X-Access-Key` and `X-Access-Secret` HTTP headers, Tenxyte identifies the client application performing the request.

---

## How It Works

1. **Creation**: An administrator creates an Application via the API (or Python code).
2. **Credentials Display**: The system generates an `access_key` (public) and an `access_secret` (private). The raw `access_secret` is returned **only once** and then securely hashed (bcrypt + base64) in the database.
3. **Usage**: Every request to protected Tenxyte auth endpoints must include the `X-Access-Key` and `X-Access-Secret` headers so the system can verify the application's identity.
4. **Revocation**: If a secret leaks, administrators can regenerate credentials for that specific application or deactivate the application entirely.

---

## Configuration

The default Application model can be customized. If you need to add fields (like rate limits, owner, etc.), you can extend `AbstractApplication`.

```python
# Create a custom model
from tenxyte.models import AbstractApplication
from django.db import models

class CustomApplication(AbstractApplication):
    owner = models.ForeignKey('users.User', on_delete=models.CASCADE)
    api_rate_limit = models.IntegerField(default=1000)

    class Meta(AbstractApplication.Meta):
        db_table = 'custom_applications'
```

And update your `settings.py`:
```python
TENXYTE_APPLICATION_MODEL = 'myapp.CustomApplication'
```

---

## API Usage

All endpoints are located under `/api/v1/auth/applications/` and require appropriate RBAC permissions (`applications.view`, `applications.create`, `applications.update`, `applications.delete`, `applications.regenerate`) and a valid JWT.

### Create an Application

Creates a new application and returns the secret.

```bash
POST /api/v1/auth/applications/
Authorization: Bearer <token>

{
  "name": "Mobile iOS App",
  "description": "Main iOS app for end-users"
}
```

**Response `201`:**
```json
{
  "message": "Application created successfully",
  "application": {
    "id": 1,
    "name": "Mobile iOS App",
    "description": "Main iOS app for end-users",
    "access_key": "c4ca4238a0b923820dcc509a6f75849b...",
    "is_active": true,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  },
  "credentials": {
    "access_key": "c4ca4238a0b923820dcc509a6f75849b...",
    "access_secret": "8b1a9953c4611296a827abf8c47804d7..."
  },
  "warning": "Save the access_secret now! It will never be shown again."
}
```

### List Applications

Returns a paginated list of all applications.

```bash
GET /api/v1/auth/applications/
Authorization: Bearer <token>
```

Accepts query parameters such as `?search=mobile`, `?is_active=true`, `?ordering=name`.

### Get Application Details

Retrieves details of a standard application. The secret is never returned.

```bash
GET /api/v1/auth/applications/1/
Authorization: Bearer <token>
```

### Update an Application

Updates the name or description of an application.

```bash
PUT /api/v1/auth/applications/1/
Authorization: Bearer <token>

{
  "name": "Mobile iOS App v2",
  "description": "Updated iOS app",
  "is_active": true
}
```

Alternatively, use `PATCH` to quickly toggle the active status:
```bash
PATCH /api/v1/auth/applications/1/
Authorization: Bearer <token>

{
  "is_active": false
}
```

### Regenerate Credentials

If a secret is compromised or lost, you can invalidate the old credentials and create new ones. This requires a specific explicit string confirmation (`"REGENERATE"`).

```bash
POST /api/v1/auth/applications/1/regenerate/
Authorization: Bearer <token>

{
     "confirmation": "REGENERATE"
}
```

**Response `200`:**
```json
{
  "message": "Credentials regenerated successfully",
  "application": { /* ... */ },
  "credentials": {
    "access_key": "new_key...",
    "access_secret": "new_secret..."
  },
  "warning": "Save the access_secret now! It will never be shown again.",
  "old_credentials_invalidated": true
}
```

### Delete an Application

Permanently deletes the application and revokes its access completely.

```bash
DELETE /api/v1/auth/applications/1/
Authorization: Bearer <token>
```

---

## Security Notes

1. **Hashing:** Just like passwords, application secrets are securely hashed using `bcrypt` and stored in base64. They cannot be recovered by reading the database.
2. **One-Time Display:** The `access_secret` is only returned once when the `POST` or `regenerate` endpoint is called. After that, it is inaccessible.
3. **Deactivation:** Before completely deleting an application, consider deactivating it (`PATCH is_active: false`) to temporarily halt its access without losing its history and statistics.

---

## Python API

You can programmatically interact with the Application model inside your Python code:

```python
from tenxyte.models import get_application_model

Application = get_application_model()

# 1. Create Application
app, raw_secret = Application.create_application(
    name="Test Script API", 
    description="For internal testing"
)
print(f"Key: {app.access_key}")
print(f"Secret: {raw_secret}")

# 2. Verify Secret
is_valid = app.verify_secret(raw_secret) # Returns True or False

# 3. Regenerate Credentials
new_credentials = app.regenerate_credentials()
print(new_credentials["access_key"])
print(new_credentials["access_secret"])
```

---

## Data Model

```
Application (AbstractApplication)
├── id  (Primary Key)
├── name (string)
├── description (text)
├── access_key (string, unique, indexed)
├── access_secret (string, hashed)
├── is_active (boolean)
├── created_at (datetime)
└── updated_at (datetime)
```
