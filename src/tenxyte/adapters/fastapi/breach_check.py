"""
HaveIBeenPwned breach-password check for the FastAPI_Adapter (spec z_aud_3, Wave B) — a
framework-agnostic reimplementation of `tenxyte.services.breach_check_service`, not a reuse of
it: that module does `from ..conf import auth_settings`, which imports `django.conf.settings` at
module load time, making it unimportable from a Django-less FastAPI process. Same k-anonymity
HIBP protocol (SHA-1 prefix/suffix split, only the first 5 hex chars ever leave this process),
driven by `core/settings.py`'s `breach_check_enabled`/`breach_check_reject` instead.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

import requests

from tenxyte.core.settings import Settings

logger = logging.getLogger(__name__)

HIBP_API_URL = "https://api.pwnedpasswords.com/range/{prefix}"
HIBP_TIMEOUT = 3  # seconds


def is_pwned(password: str, settings: Settings) -> tuple[bool, int]:
    """(is_pwned, breach_count). Fails open (False, 0) on any network error or when breach
    checking is disabled — a third-party outage must never block registration/password changes."""
    if not settings.breach_check_enabled:
        return False, 0

    # nosemgrep: python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1
    sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1_hash[:5], sha1_hash[5:]

    try:
        response = requests.get(
            HIBP_API_URL.format(prefix=prefix), headers={"Add-Padding": "true"}, timeout=HIBP_TIMEOUT
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("HIBP API error: %s — skipping breach check", exc)
        return False, 0

    for line in response.text.splitlines():
        if ":" not in line:
            continue
        line_suffix, _, count_str = line.partition(":")
        if line_suffix.upper() == suffix:
            return True, int(count_str.strip())

    return False, 0


def check_password(password: str, settings: Settings) -> tuple[bool, str]:
    """(ok, error_message) — ok is False only when breach_check_reject is also enabled; a hit
    with reject disabled is reported as ok=True (caller may still flag it informationally, as
    the Django_Adapter's PasswordResetConfirmView does)."""
    pwned, count = is_pwned(password, settings)
    if not pwned:
        return True, ""
    if not settings.breach_check_reject:
        return True, ""
    return False, f"This password has appeared in {count:,} data breaches. Please choose a different password."


async def check_password_async(password: str, settings: Settings) -> tuple[bool, str]:
    """Async entry point — `requests` is blocking I/O (a forbidden direct call from `async def`
    per `scripts/check_async_purity.py`), bridged via `asyncio.to_thread` per the JWT_Async_Pattern
    rather than calling `check_password` directly from router code."""
    return await asyncio.to_thread(check_password, password, settings)
