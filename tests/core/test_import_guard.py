"""
Property-based / subprocess tests for the Import_Guard (PEP 562) in `tenxyte/__init__.py`.

Spec: specs/z_aud_1 (Phase 1 "Crédibilité"), Requirement 2, design.md "Correctness Properties".

Because Django is actually installed in this development/CI environment (it remains a default
runtime dependency until the packaging inversion of Requirement 2 ships), "Django absent" is
simulated in an isolated subprocess via a `sys.meta_path` finder that raises `ImportError` for any
`django*` import — this is the standard technique for testing packaging/import boundaries without
needing a second venv, and matches the approach flagged as acceptable in design.md.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_django]

_SRC_PATH = str(Path(__file__).resolve().parents[2] / "src")

# Prelude injected into every subprocess script: blocks `django` and all `django.*` imports before
# `tenxyte` is ever imported, then puts `src/` on sys.path.
_BLOCK_DJANGO_PRELUDE = textwrap.dedent(f"""
    import sys, importlib.abc

    class _BlockDjango(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if name == "django" or name.startswith("django."):
                raise ImportError(f"blocked for test: {{name}}")
            return None

    sys.meta_path.insert(0, _BlockDjango())
    sys.path.insert(0, {_SRC_PATH!r})
    """)


def _run(script_body: str) -> subprocess.CompletedProcess:
    full_script = _BLOCK_DJANGO_PRELUDE + textwrap.dedent(script_body)
    return subprocess.run(
        [sys.executable, "-c", full_script],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ===========================================================================
# Property 1: Import sans Django réussit et expose le Core
# ===========================================================================


def test_property_1_import_without_django_succeeds():
    """Feature: z_aud_1, Property 1: Import sans Django réussit et expose le Core."""
    result = _run("""
        import tenxyte
        assert isinstance(tenxyte.__version__, str) and tenxyte.__version__
        print("IMPORT_OK")
        """)
    assert result.returncode == 0, result.stderr
    assert "IMPORT_OK" in result.stdout


def test_property_1_core_submodule_importable_without_django():
    """Feature: z_aud_1, Property 1: les symboles Core sont importables sans Django."""
    result = _run("""
        from tenxyte.core.jwt_service import JWTService
        from tenxyte.core import Settings, TOTPService, WebAuthnService, MagicLinkService
        print("CORE_IMPORT_OK")
        """)
    assert result.returncode == 0, result.stderr
    assert "CORE_IMPORT_OK" in result.stdout


def test_property_1_exceptions_module_importable_without_django():
    """`tenxyte.exceptions` must import cleanly without Django (it defines the guard exception)."""
    result = _run("""
        from tenxyte.exceptions import TenxyteMissingDependencyError
        assert issubclass(TenxyteMissingDependencyError, ImportError)
        print("EXCEPTIONS_IMPORT_OK")
        """)
    assert result.returncode == 0, result.stderr
    assert "EXCEPTIONS_IMPORT_OK" in result.stdout


# ===========================================================================
# Property 2: Accès à un symbole Django-only sans Django échoue explicitement
# ===========================================================================


@pytest.mark.parametrize(
    "attr_expr",
    [
        "tenxyte.AbstractUser",
        "tenxyte.AbstractRole",
        "tenxyte.AbstractPermission",
        "tenxyte.AbstractApplication",
        "tenxyte.get_user_model",
        "tenxyte.get_role_model",
        "tenxyte.get_permission_model",
        "tenxyte.get_application_model",
    ],
)
def test_property_2_django_only_symbol_raises_explicit_error(attr_expr):
    """Feature: z_aud_1, Property 2: accès à un symbole Django-only sans Django échoue explicitement."""
    result = _run(f"""
        import tenxyte
        try:
            {attr_expr}
            print("UNEXPECTED_SUCCESS")
        except tenxyte.TenxyteMissingDependencyError as e:
            assert "pip install tenxyte[django]" in str(e), str(e)
            print("EXPECTED_ERROR_OK")
        """)
    assert result.returncode == 0, result.stderr
    assert "EXPECTED_ERROR_OK" in result.stdout
    assert "UNEXPECTED_SUCCESS" not in result.stdout


def test_property_2_setup_raises_explicit_error_without_django():
    """Feature: z_aud_1, Property 2: `tenxyte.setup()` sans Django échoue explicitement (MT-1)."""
    result = _run("""
        import tenxyte
        try:
            tenxyte.setup({})
            print("UNEXPECTED_SUCCESS")
        except tenxyte.TenxyteMissingDependencyError as e:
            assert "pip install tenxyte[django]" in str(e), str(e)
            print("EXPECTED_ERROR_OK")
        """)
    assert result.returncode == 0, result.stderr
    assert "EXPECTED_ERROR_OK" in result.stdout
    assert "UNEXPECTED_SUCCESS" not in result.stdout


def test_property_2_never_returns_none_or_degraded_object():
    """A Django-only symbol never silently resolves to None or a degraded stand-in."""
    result = _run("""
        import tenxyte
        try:
            x = tenxyte.AbstractUser
            print(f"RESOLVED:{x!r}")
        except tenxyte.TenxyteMissingDependencyError:
            print("RAISED_OK")
        """)
    assert result.returncode == 0, result.stderr
    assert "RAISED_OK" in result.stdout
    assert "RESOLVED:None" not in result.stdout
