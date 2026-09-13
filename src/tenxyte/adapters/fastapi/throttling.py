"""
Rate limiting for the FastAPI_Adapter (spec z_aud_3, Requirement 3.4) — parity with the
scope/rate families defined by `tenxyte.throttles`'s `IPBasedThrottle` subclasses (same scope
names, same rates). Counting itself reuses `CacheService.check_rate_limit_async` verbatim — the
cache port already implements the exact "read count, reject if at max, else increment and set
expiry on the first hit in a window" fixed-window algorithm DRF's `SimpleRateThrottle` uses, so
there is nothing throttling-algorithm-specific to reimplement here, and it is directly testable
with simulated time by monkeypatching `time.time` in `tenxyte.core.cache_service` — the only
place wall-clock time is read.

Deliberately not ported (out of scope for this task): `ProgressiveLoginThrottle` (exponential
backoff bookkeeping layered on top of a base throttle, not a distinct rate family) and
`SimpleThrottleRule` (settings-driven arbitrary-path throttling — a separate generic mechanism,
not part of the named auth-scope families). Client IP resolution here is minimal
(`request.client.host`) — the Django throttles' `X-Forwarded-For`/`TRUSTED_PROXIES` trust chain
(guarding against IP spoofing behind a reverse proxy) is a security-hardening feature with no
equivalent on `core/settings.py` yet, not silently reimplemented.

Usage as a FastAPI dependency, stacking scopes exactly like Django views stack throttle_classes:

    @router.post("/login")
    async def login(_: None = Depends(rate_limit("login", "login_hourly"))):
        ...
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request
from tenxyte.adapters.fastapi.errors import TenxyteAPIError

# Same scope -> rate mapping as tenxyte.throttles's IPBasedThrottle subclasses.
RATE_SCOPES: dict[str, str] = {
    "login": "5/min",
    "login_hourly": "20/hour",
    "register": "3/hour",
    "register_daily": "10/day",
    "password_reset": "3/hour",
    "password_reset_daily": "10/day",
    "otp_request": "5/hour",
    "otp_verify": "5/min",
    "login_otp_request": "5/min",
    "login_otp_request_daily": "20/day",
    "refresh": "30/min",
    "magic_link_request": "3/hour",
    "magic_link_verify": "10/min",
}

_PERIOD_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_rate(rate: str) -> tuple[int, int]:
    """Same format DRF's `SimpleRateThrottle.parse_rate` accepts: "<num>/<period>", where only
    the period's first letter matters (min/hour/day all resolve via their first character)."""
    num, _, period = rate.partition("/")
    return int(num), _PERIOD_SECONDS[period[0]]


def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


def rate_limit(*scopes: str) -> Callable[..., Coroutine[Any, Any, None]]:
    """A dependency that enforces one or more named rate-limit scopes for the requesting IP,
    raising `RATE_LIMIT_EXCEEDED` (429) on the first scope that's over budget — mirroring how a
    Django view stacks multiple throttle_classes (e.g. `LoginThrottle` + `LoginHourlyThrottle`)."""
    for scope in scopes:
        if scope not in RATE_SCOPES:
            raise ValueError(f"Unknown rate limit scope: {scope!r}")

    async def _dependency(request: Request) -> None:
        cache_service = request.app.state.tenxyte_cache_service
        ip = _get_client_ip(request)

        for scope in scopes:
            max_requests, window_seconds = _parse_rate(RATE_SCOPES[scope])
            key = f"throttle_{scope}_{ip}"
            allowed, _remaining, reset_seconds = await cache_service.check_rate_limit_async(
                key, max_requests, window_seconds
            )
            if not allowed:
                raise TenxyteAPIError(
                    "Rate limit exceeded",
                    code="RATE_LIMIT_EXCEEDED",
                    status_code=429,
                    details={"scope": scope, "retry_after": reset_seconds},
                )

    return _dependency
