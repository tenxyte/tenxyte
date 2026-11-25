"""
Sync-API snapshot test for the ports touched by z_aud_3's Async_Ports work.

Feature: z_aud_3, Property 5: L'API sync du Core est intouchée

Snapshots the exact method signatures of `UserRepository` (ports/repositories.py) and the WebAuthn
storage protocols (core/webauthn_service.py) before/after this phase, and asserts the new async
mirrors are strictly additive: same method *names* as their sync counterpart, only new `_async`
methods appended — never a removed or renamed sync method.
"""

import inspect

import pytest

from tenxyte.core.webauthn_service import (
    AsyncWebAuthnChallengeRepository,
    AsyncWebAuthnCredentialRepository,
    WebAuthnChallengeRepository,
    WebAuthnCredentialRepository,
)
from tenxyte.ports.async_repositories import AsyncUserRepository
from tenxyte.ports.repositories import UserRepository

pytestmark = [pytest.mark.no_django]

# Frozen snapshot: (method_name, tuple_of_param_names_excluding_self) as of z_aud_3's start.
EXPECTED_USER_REPOSITORY_SIGNATURE = {
    "get_by_id": ("user_id",),
    "get_by_email": ("email",),
    "create": ("user",),
    "update": ("user",),
    "delete": ("user_id",),
    "list_all": ("skip", "limit", "filters"),
    "count": ("filters",),
    "update_last_login": ("user_id", "timestamp"),
    "set_mfa_secret": ("user_id", "mfa_type", "secret"),
    "verify_email": ("user_id",),
}


def _param_names(func) -> tuple:
    return tuple(p for p in inspect.signature(func).parameters if p != "self")


def test_user_repository_sync_signatures_unchanged():
    for name, expected_params in EXPECTED_USER_REPOSITORY_SIGNATURE.items():
        method = getattr(UserRepository, name)
        assert _param_names(method) == expected_params, f"UserRepository.{name} signature changed"


def test_async_user_repository_is_an_exact_mirror_no_more_no_less():
    sync_methods = {name for name in EXPECTED_USER_REPOSITORY_SIGNATURE}
    async_methods = {
        name
        for name, member in vars(AsyncUserRepository).items()
        if not name.startswith("_") and inspect.iscoroutinefunction(member)
    }
    assert async_methods == sync_methods, (
        f"AsyncUserRepository must mirror UserRepository exactly: "
        f"missing={sync_methods - async_methods}, extra={async_methods - sync_methods}"
    )
    for name in sync_methods:
        sync_params = _param_names(getattr(UserRepository, name))
        async_params = _param_names(getattr(AsyncUserRepository, name))
        assert sync_params == async_params, f"{name}: sync params {sync_params} != async params {async_params}"


def test_webauthn_storage_protocols_unchanged():
    sync_credential_methods = {"get_by_credential_id", "list_by_user", "create", "update_sign_count", "delete"}
    sync_challenge_methods = {"create", "get_by_id", "consume"}

    for name in sync_credential_methods:
        assert hasattr(WebAuthnCredentialRepository, name)
    for name in sync_challenge_methods:
        assert hasattr(WebAuthnChallengeRepository, name)


def test_async_webauthn_protocols_are_additive_supersets():
    # Protocol inheritance means the async protocols still declare (via MRO) every sync method
    # name, plus their own *_async siblings — never a removed sync method.
    credential_members = set(
        vars(AsyncWebAuthnCredentialRepository).get("__protocol_attrs__", []) or dir(AsyncWebAuthnCredentialRepository)
    )
    for name in ("get_by_credential_id", "list_by_user", "create", "update_sign_count", "delete"):
        assert name in credential_members or hasattr(AsyncWebAuthnCredentialRepository, name)

    for name in (
        "get_by_credential_id_async",
        "list_by_user_async",
        "create_async",
        "update_sign_count_async",
        "delete_async",
    ):
        assert hasattr(AsyncWebAuthnCredentialRepository, name)

    for name in ("create_async", "get_by_id_async", "consume_async"):
        assert hasattr(AsyncWebAuthnChallengeRepository, name)
