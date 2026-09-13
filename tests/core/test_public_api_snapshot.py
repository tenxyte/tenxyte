"""
Public API snapshot test.

Spec: specs/z_aud_1 (Phase 1 "Crédibilité"), Requirement 1.4, design.md "Property 4".

Fails the build if a previously exported public symbol from `tenxyte/__init__.py` disappears
without going through the deprecation cycle described in docs/en/stability.md. The snapshot below
must stay in sync with the "tenxyte/__init__.py and tenxyte.core Exports" section of
docs/en/stability.md (and its French counterpart) — additions are MINOR changes and should be
added to both places together; removals require a full deprecation cycle (see stability.md).
"""

import pytest

import tenxyte
import tenxyte.core

pytestmark = [pytest.mark.no_django]

# Symbols that MUST be exported at the `tenxyte` top level (tenxyte/__init__.py), per
# docs/en/stability.md §5. This is the Requirement 1.4 snapshot.
EXPECTED_TOP_LEVEL_PUBLIC_SYMBOLS = frozenset(
    {
        "AbstractUser",
        "AbstractRole",
        "AbstractPermission",
        "AbstractApplication",
        "get_user_model",
        "get_role_model",
        "get_permission_model",
        "get_application_model",
        "setup",
        "TenxyteMissingDependencyError",
    }
)

# Symbols that MUST be exported by `tenxyte.core` (tenxyte/core/__init__.py), per
# docs/en/stability.md §5. Framework-agnostic — always available regardless of installed adapter.
EXPECTED_CORE_PUBLIC_SYMBOLS = frozenset(
    {
        "Settings",
        "SettingsProvider",
        "SecureModePreset",
        "SECURE_MODE_PRESETS",
        "init",
        "get_settings",
        "EnvSettingsProvider",
        "get_env_settings",
        "EmailService",
        "EmailAttachment",
        "ConsoleEmailService",
        "CacheService",
        "InMemoryCacheService",
        "UserBase",
        "UserCreate",
        "UserUpdate",
        "UserResponse",
        "UserInDB",
        "LoginRequest",
        "TokenResponse",
        "OrganizationBase",
        "OrganizationCreate",
        "OrganizationResponse",
        "JWTService",
        "TokenPair",
        "DecodedToken",
        "TokenBlacklistService",
        "InMemoryTokenBlacklistService",
        "TOTPService",
        "TOTPSetupResult",
        "TOTPUserData",
        "TOTPStorage",
        "CodeReplayProtection",
        "WebAuthnService",
        "WebAuthnCredential",
        "WebAuthnChallenge",
        "RegistrationResult",
        "AuthenticationResult",
        "WebAuthnCredentialRepository",
        "WebAuthnChallengeRepository",
        "MagicLinkService",
        "MagicLinkToken",
        "MagicLinkResult",
        "MagicLinkRepository",
        "UserLookup",
        "TaskService",
    }
)


def test_top_level_all_is_a_superset_of_the_snapshot():
    """Feature: z_aud_1, Property 4: Snapshot des exports publics (tenxyte/__init__.py)."""
    current = set(tenxyte.__all__)
    missing = EXPECTED_TOP_LEVEL_PUBLIC_SYMBOLS - current
    assert not missing, (
        f"Public symbol(s) removed from tenxyte.__all__ without a deprecation cycle: {sorted(missing)}. "
        "See docs/en/stability.md — a removal requires a DeprecationWarning for a full MINOR "
        "version before it can be dropped in a MAJOR release."
    )


def test_top_level_symbols_are_all_resolvable_via_dir():
    """Every documented top-level symbol shows up in dir(tenxyte), even before first access."""
    exported = set(dir(tenxyte))
    missing = EXPECTED_TOP_LEVEL_PUBLIC_SYMBOLS - exported
    assert not missing, f"dir(tenxyte) is missing documented symbols: {sorted(missing)}"


def test_core_all_is_a_superset_of_the_snapshot():
    """Feature: z_aud_1, Property 4: Snapshot des exports publics (tenxyte.core.__all__)."""
    current = set(tenxyte.core.__all__)
    missing = EXPECTED_CORE_PUBLIC_SYMBOLS - current
    assert not missing, (
        f"Public symbol(s) removed from tenxyte.core.__all__ without a deprecation cycle: "
        f"{sorted(missing)}. See docs/en/stability.md."
    )


def test_version_attribute_present_and_string():
    assert isinstance(tenxyte.__version__, str)
    assert tenxyte.__version__
