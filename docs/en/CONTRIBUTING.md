# Contributing

Thank you for your interest in contributing to Tenxyte!

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Code Style](#code-style)
- [Making Changes](#making-changes)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Documentation](#documentation)
- [Reporting Issues](#reporting-issues)
- [Supported Versions](#supported-versions)
- [Code of Conduct](#code-of-conduct)
- [Questions?](#questions)

---

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/tenxyte.git
cd tenxyte
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode along with all development tools:
- **pytest** + pytest-django + pytest-asyncio — test framework
- **pytest-cov** — coverage reporting
- **black** — code formatter
- **ruff** — linter
- **mypy** — type checking

### 4. Run Tests

```bash
pytest
```

---

## Running Tests

### All Tests

```bash
pytest
```

### Specific Tests

```bash
# By directory
pytest tests/unit/

# By file
pytest tests/unit/test_jwt.py

# By class
pytest tests/unit/test_validators.py::TestPasswordValidator

# By name
pytest tests/unit/test_jwt.py::TestJWTService::test_generate_access_token

# By keyword
pytest tests/ -k "password"
```

### With Coverage

```bash
pytest --cov=tenxyte --cov-report=html --cov-report=term
```

The HTML report is generated in `htmlcov/index.html`. The project enforces a **90% coverage threshold** (configured in `pyproject.toml`).

### Targeting a Specific Module

```bash
pytest --cov=tenxyte.services.auth_service tests/unit/test_auth_service.py
```

### Advanced Options

```bash
pytest -v              # Verbose output
pytest -s              # Show print() output
pytest --pdb           # Debug on failure
pytest --durations=10  # Show 10 slowest tests
pytest --lf            # Re-run only last failures
```

---

## Test Structure

```
tests/
├── unit/                 # Core Services, Validators — fast and isolated
├── integration/
│   ├── django/           # Django adapter: Models, Signals, Views, DB constraints
│   └── fastapi/          # FastAPI adapter: Models, Repositories, Routers
├── security/             # Timing attacks, breach detection, rate limiting
├── multidb/              # Multi-database backend compatibility
├── conftest.py           # Shared fixtures
├── settings.py           # Django test settings
└── test_dashboard.py     # Dashboard view tests
```

### Multi-Database Tests

```bash
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_sqlite"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_pgsql"
pytest tests/multidb/ -o "DJANGO_SETTINGS_MODULE=tests.multidb.settings_mongodb"
```

---

## Code Style

We use **black** for formatting and **ruff** for linting, both configured with a max line length of **120 characters**.

### Format Code

```bash
black src/tenxyte/
```

### Check Formatting (CI Mode)

```bash
black --check src/tenxyte/
```

### Lint

```bash
ruff check src/tenxyte/
```

### Type Check

```bash
mypy src/tenxyte/
```

### Configuration

See `pyproject.toml` for black and ruff configuration:

```toml
[tool.black]
line-length = 120
target-version = ["py310", "py311", "py312"]

[tool.ruff]
line-length = 120
target-version = "py310"
```

---

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write clear, documented code
- Follow existing patterns and conventions
- Add tests for new functionality
- Update documentation if needed

### 3. Run Tests and Linting

```bash
pytest
black --check src/tenxyte/
ruff check src/tenxyte/
```

### 4. Commit Your Changes

Write clear commit messages:

```bash
git commit -m "Add support for custom token claims"
```

### 5. Push and Create a Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a pull request on GitHub targeting the `main` or `develop` branch.

---

## Pull Request Guidelines

### CI Checks

Pull requests are automatically tested by GitHub Actions against a matrix of:
- **Python**: 3.10, 3.11, 3.12, 3.13
- **Django**: 4.2, 5.0, 5.1, 5.2, 6.0
- **FastAPI**: latest stable

Coverage is reported via Codecov on Python 3.12 / Django 6.0.

### What We Look For

- [ ] Tests pass on all supported Python/Django versions
- [ ] Code is formatted with black (`black --check` passes)
- [ ] No linting errors (`ruff check` passes)
- [ ] New features include tests
- [ ] Coverage stays above 90%
- [ ] Documentation is updated if needed
- [ ] Commit messages are clear and descriptive

### What to Include

- Clear description of the change
- Link to related issue (if any)
- Screenshots for UI changes
- Migration notes for breaking changes

---

## Documentation

Documentation is organized in the `docs/` directory:

| File | Content |
|------|---------|
| `quickstart.md` | Getting started guide |
| `settings.md` | All configuration options |
| `endpoints.md` | REST API endpoint reference |
| `rbac.md` | Role-Based Access Control |
| `airs.md` | AI Responsibility & Security |
| `organizations.md` | Multi-tenant Organizations |
| `security.md` | Security architecture |
| `schemas.md` | Database schemas |
| `architecture.md` | Core & Adapters architecture |
| `custom_adapters.md` | Creating custom adapters |
| `TESTING.md` | Testing guide |
| `MIGRATION_GUIDE.md` | Migration from other packages |
| `troubleshooting.md` | Common issues and solutions |

When adding or changing a feature, update the relevant documentation file(s).

> [!IMPORTANT]
> ### Schema Consistency (all models)
>
> Tenxyte is **framework-agnostic**. Every response object (`User`, `Organization`, `Role`, `TokenPair`, `AuditLog`, etc.) **must be identical** across all adapters (Django, FastAPI, custom). This is a core value of the project.
>
> **Rules:**
> - The canonical schemas are defined in [`schemas.md`](schemas.md) and in `tenxyte.core.schemas` ([source](../../src/tenxyte/core/schemas.py)). Any model change must start from these reference files.
> - **No alias fields.** Do not add fields that duplicate existing ones (e.g. `is_verified` aliasing `is_email_verified`, or `date_joined` aliasing `created_at`). Each piece of information must appear exactly once.
> - **No feature state in preference sub-objects.** Objects like `preferences` contain only user preferences. Feature state (e.g. `is_2fa_enabled`) belongs in dedicated top-level fields.
> - When modifying a model, update **all** occurrences: `tenxyte.core.schemas.py`, adapter serializers (`auth_serializers.py`, etc.), `schemas.md` (EN + FR), and every relevant JSON example in `endpoints.md` (EN + FR).
> - **Test obligation:** after any model change, all tests involving the modified model must be re-run and **must pass without errors**. No PR modifying a schema will be accepted if tests fail.

---

## Reporting Issues

### Bug Reports

Include:
- Tenxyte version (`pip show tenxyte`)
- Python version
- Django version
- Django REST Framework version
- Steps to reproduce
- Expected vs actual behavior
- Full traceback (if applicable)

### Feature Requests

- Describe the use case
- Explain why it can't be done with current features
- Propose a solution if you have one

---

## Supported Versions

| Component | Versions |
|-----------|----------|
| Python | 3.10, 3.11, 3.12, 3.13 |
| Django | 4.2, 5.0, 5.1, 5.2, 6.0 |
| DRF | ≥ 3.16 |
| FastAPI | Latest stable |

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

---

## Questions?

Open a [GitHub Issue](https://github.com/tenxyte/tenxyte/issues) for bug reports and feature requests, or start a [GitHub Discussion](https://github.com/tenxyte/tenxyte/discussions) for general questions.
