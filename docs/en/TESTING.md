# Testing Guide for Tenxyte

## Installing Test Dependencies

```bash
pip install -e ".[dev]"
```

This will install:
- **pytest**: Core test framework
- **pytest-django**: Django integration
- **pytest-cov**: Coverage report generation
- **pytest-asyncio**: Async test support
- **black, ruff, mypy**: Linting and type checking tools

## Running Tests

### All Tests

```bash
pytest
```

### Tests with Coverage Report

```bash
pytest --cov=tenxyte --cov-report=html --cov-report=term
```

The HTML report will be generated in `htmlcov/index.html`. The project baseline for coverage is **90%** (configured in `pyproject.toml`).

### Specific Tests

```bash
# Specific test directory
pytest tests/core/

# Specific test file
pytest tests/core/test_core_jwt_service.py

# Specific test class
pytest tests/core/test_core_jwt_service.py::TestJWTService

# Specific test
pytest tests/core/test_core_jwt_service.py::TestJWTService::test_generate_access_token

# Tests matching a pattern
pytest tests/ -k "password"
```

### Advanced Options

```bash
pytest -v              # Verbose mode
pytest -s              # Show print() output
pytest --pdb           # Debug on failure
pytest -n auto         # Parallel testing (requires pytest-xdist)
pytest --durations=10  # Show 10 slowest tests
pytest --lf            # Re-run only last failures
```

## Test Structure

Tenxyte organizes tests by category:

```
tests/
├── core/                       # Core service tests (JWT, Cache, Email, TOTP, Sessions, etc.)
│   └── conftest.py             # Core test fixtures (mocks, no DB)
├── integration/
│   ├── django/                 # Django adapter integration tests (Models, Signals, Views)
│   │   ├── conftest.py         # Shared Django fixtures (DB, API clients, users)
│   │   ├── multidb/            # Multi-database support tests
│   │   ├── test_dashboard.py   # Dashboard view tests
│   │   └── settings.py         # Django test settings
│   └── fastapi/                # FastAPI adapter tests (Models, Repositories, Routers)
└── test_canonical_spec.py      # Canonical specification validation
```

## Available Fixtures

Defined in `tests/integration/django/conftest.py`:

- `api_client`: Standard REST Framework API Client
- `app_api_client`: Client with `X-Access-Key` / `X-Access-Secret` headers
- `authenticated_client`: Client with JWT + Application headers
- `authenticated_admin_client`: Admin client with JWT + Application headers
- `application`: Test Application model instance
- `user`: Standard test user (test@example.com)
- `admin_user`: User with "admin" role
- `user_with_phone`: User with phone number (for OTP tests)
- `user_with_2fa`: User with TOTP enabled
- `permission`/`role`: Test RBAC model instances

## Test Categories

### 1. Core Tests (`tests/core/`)
Core service-layer logic tests (JWT, OTP, TOTP, Cache, Email, Session, Magic Link, WebAuthn). Fast, isolated, and framework-agnostic. Also includes security-specific tests (timing attack mitigation).

### 2. Integration Tests (`tests/integration/`)

#### Django (`tests/integration/django/`)
Testing Django adapter components: model interactions, database constraints, signals, views, serializers, and dashboard.

#### FastAPI (`tests/integration/fastapi/`)
Testing FastAPI adapter components: Pydantic models, repositories, and routers.

### 3. Multi-DB Tests (`tests/integration/django/multidb/`)
Ensures compatibility with multiple backends:
```bash
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_sqlite"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_pgsql"
pytest tests/integration/django/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.integration.django.multidb.settings_mongodb"
```

## Expected Coverage

Tenxyte enforces a **90% coverage threshold**. To check coverage of a specific module:
```bash
pytest --cov=tenxyte.core.jwt_service tests/core/test_core_jwt_service.py
```

## Best Practices

1. **Isolation**: Never let tests depend on each other. Use `db` fixture for database isolation.
2. **Mocking**: Mock external services (Email, SMS gateways) unless testing the backends specifically.
3. **Naming**: Use descriptive names: `test_<feature>_<scenario>_<expected_result>`.
4. **Edge Cases**: Always test empty inputs, invalid formats, and boundary values.

## Troubleshooting

### `ImportError: No module named 'tenxyte'`
Ensure you've installed the package in editable mode: `pip install -e .`

### `Database errors`
The tests use an in-memory SQLite database by default (`--create-db --reuse-db` are enabled in `pytest.ini`). For other databases, ensure the environment variables for `DB_HOST`, `DB_USER`, etc., are set correctly.

### `Django settings not configured`
Check that `DJANGO_SETTINGS_MODULE` points to `tests.settings` or a valid settings file.
