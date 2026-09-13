"""
Packaging inversion tests — verifies `pyproject.toml`'s dependency structure matches the
Requirement 2 contract (Core-only default install, Django moved to an opt-in extra).

Spec: specs/z_aud_1 (Phase 1 "Crédibilité"), Requirement 2, design.md "Property 12".
"""

import re
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_django]

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"

# The exact 0.9.6.4 top-level `dependencies` list, frozen here as the historical baseline that
# Property 12 checks against — this constant intentionally never changes.
_LEGACY_0_9_DEPENDENCIES = frozenset(
    {
        "django>=4.2",
        "djangorestframework>=3.16",
        "django-cors-headers>=4.4",
        "drf-spectacular>=0.27",
        "PyJWT>=2.12.1",
        "bcrypt>=4.2",
        "pyotp>=2.9",
        "qrcode[pil]>=8.0",
        "google-auth>=2.49.1",
        "google-auth-oauthlib>=1.2",
        "cryptography>=42.0",
        "Pillow>=11.0",
        "requests>=2.32",
        "pydantic>=2.12",
        "email-validator>=2.0",
    }
)

_CORE_ONLY_PACKAGE_NAMES = frozenset(
    {"PyJWT", "bcrypt", "pyotp", "qrcode", "cryptography", "Pillow", "requests", "pydantic", "email-validator"}
)

_DJANGO_PACKAGE_NAMES = frozenset(
    {"django", "djangorestframework", "django-cors-headers", "drf-spectacular", "google-auth", "google-auth-oauthlib"}
)


def _normalize(spec: str) -> str:
    """Normalize a PEP 508 requirement string for set comparison (case-insensitive package name)."""
    return re.sub(r"^([A-Za-z0-9_.\-\[\]]+)", lambda m: m.group(1).lower(), spec.strip())


def _package_name(spec: str) -> str:
    return re.split(r"[<>=\[]", spec.strip(), maxsplit=1)[0]


@pytest.fixture(scope="module")
def pyproject_data():
    with open(_PYPROJECT_PATH, "rb") as f:
        return tomllib.load(f)


def test_dependencies_is_core_only(pyproject_data):
    deps = pyproject_data["project"]["dependencies"]
    names = {_package_name(d) for d in deps}
    assert (
        names == _CORE_ONLY_PACKAGE_NAMES
    ), f"Base `dependencies` must be exactly the Core set (Requirement 2.1). Got: {sorted(names)}"
    for django_pkg in ("django", "djangorestframework", "django-cors-headers", "drf-spectacular"):
        assert not any(
            _package_name(d).lower() == django_pkg for d in deps
        ), f"'{django_pkg}' must NOT be in the base `dependencies` (Requirement 2.1)."


def test_django_extra_provides_the_full_django_stack(pyproject_data):
    django_extra = pyproject_data["project"]["optional-dependencies"]["django"]
    names = {_package_name(d) for d in django_extra}
    assert (
        names == _DJANGO_PACKAGE_NAMES
    ), f"`[django]` extra must provide exactly the Django stack (Requirement 2.2). Got: {sorted(names)}"


def test_core_extra_is_a_noop_alias(pyproject_data):
    core_extra = pyproject_data["project"]["optional-dependencies"]["core"]
    assert core_extra == [], "`[core]` must be a no-op deprecated alias (Requirement 2.6) — empty list."


def test_property_12_dependency_set_equivalence(pyproject_data):
    """Feature: z_aud_1, Property 12: Équivalence des ensembles de dépendances.

    deps(1.0) ∪ extras[django](1.0) == deps(0.9.6.4) — same packages, same version constraints —
    guaranteeing `pip install tenxyte[django]` reproduces today's default install exactly.
    """
    deps = pyproject_data["project"]["dependencies"]
    django_extra = pyproject_data["project"]["optional-dependencies"]["django"]

    union = {_normalize(d) for d in deps} | {_normalize(d) for d in django_extra}
    legacy = {_normalize(d) for d in _LEGACY_0_9_DEPENDENCIES}

    assert union == legacy, (
        f"dependencies ∪ extras[django] must equal the 0.9.6.4 dependency set.\n"
        f"Missing from union: {sorted(legacy - union)}\n"
        f"Extra in union (not in legacy): {sorted(union - legacy)}"
    )


def test_other_extras_remain_functional(pyproject_data):
    extras = pyproject_data["project"]["optional-dependencies"]
    for name in ("fastapi", "postgres", "mysql", "mongodb", "twilio", "sendgrid", "webauthn"):
        assert name in extras and len(extras[name]) > 0, f"`[{name}]` extra must remain unchanged and non-empty."


def test_all_extra_includes_django_and_fastapi(pyproject_data):
    all_extra = pyproject_data["project"]["optional-dependencies"]["all"]
    names = {_package_name(d) for d in all_extra}
    assert _DJANGO_PACKAGE_NAMES.issubset(names), "`[all]` must include the full Django stack."
    assert "fastapi" in names, "`[all]` must include FastAPI."


def test_version_and_classifier_consistency(pyproject_data):
    """Feature: z_aud_1, Requirement 7.1: version 1.0.0 + Production/Stable classifier, in sync."""
    project = pyproject_data["project"]
    version = project["version"]
    classifiers = project["classifiers"]

    import tenxyte

    assert version == tenxyte.__version__, "pyproject.toml version must match tenxyte.__version__."

    is_1x_or_later = tuple(int(p) for p in version.split(".")[:2] if p.isdigit()) >= (1, 0)
    has_stable_classifier = "Development Status :: 5 - Production/Stable" in classifiers
    has_beta_classifier = "Development Status :: 4 - Beta" in classifiers

    if is_1x_or_later:
        assert has_stable_classifier, "Version >= 1.0 must carry the Production/Stable classifier."
        assert not has_beta_classifier, "Version >= 1.0 must not still carry the Beta classifier."
    else:
        assert not has_stable_classifier, "Pre-1.0 versions must not claim Production/Stable."
