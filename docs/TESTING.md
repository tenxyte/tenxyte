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
pytest tests/unit/

# Specific test file
pytest tests/unit/test_jwt.py

# Specific test class
pytest tests/unit/test_validators.py::TestPasswordValidator

# Specific test
pytest tests/unit/test_jwt.py::TestJWTService::test_generate_access_token

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
├── unit/                 # Unit tests (Services, Validators)
├── integration/          # Integration tests (Models, Signals)
├── security/             # Security-specific tests (Timing attacks, BREACH, etc.)
├── multidb/              # Multi-database support tests
├── conftest.py           # Shared fixtures
├── settings.py           # Django test settings
└── test_dashboard.py     # Main dashboard view tests
```

## Available Fixtures

Defined in `tests/conftest.py`:

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

### 1. Unit Tests (`tests/unit/`)
Service-layer logic tests (JWT, OTP, TOTP, Breach Check). Fast and isolated.

### 2. Integration Tests (`tests/integration/`)
Testing model interactions, database constraints, and signals.

### 3. Security Tests (`tests/security/`)
Vulnerability-specific tests including:
- Password breach detection
- Account enumeration protection
- Rate limiting and lockout logic
- JWT signature validation

### 4. Multi-DB Tests (`tests/multidb/`)
Ensures compatibility with multiple backends:
```bash
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb"
```

## Expected Coverage

Tenxyte enforces a **90% coverage threshold**. To check coverage of a specific module:
```bash
pytest --cov=tenxyte.services.auth_service tests/unit/test_auth_service.py
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
