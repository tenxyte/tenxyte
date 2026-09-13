"""
Typed exception hierarchy for tenxyte-langchain.

Every family in spec/airs/AIRS-1.0.md §8 (Error Codes) is fail-safe by design ([AIRS-CORE-22]):
callers get a specific, typed exception instead of a bare HTTP error, and none of these are meant
to be retried automatically with the same Agent Token ([AIRS-CORE-17]).
"""

from __future__ import annotations

from typing import Any


class TenxyteAIRSError(Exception):
    """Base class for every error this connector raises."""

    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class TenxyteAIRSUnavailable(TenxyteAIRSError):
    """The AIRS server (or its discovery document) could not be reached."""


class TenxyteCapabilityError(TenxyteAIRSError):
    """The server's discovery document does not announce a Conformance Level this call needs."""


class TenxyteAgentTokenError(TenxyteAIRSError):
    """Base class for the terminal Agent Token conditions of [AIRS-CORE-16]. Never retry these."""


class TenxyteTokenNotFoundError(TenxyteAgentTokenError):
    """The presented token is unknown to the server (condition 1)."""


class TenxyteTokenSuspendedError(TenxyteAgentTokenError):
    """The token is SUSPENDED (condition 2). `suspended_reason` is one of the five spec reasons,
    when the server provided it."""

    def __init__(self, message: str, *, suspended_reason: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.suspended_reason = suspended_reason


class TenxyteTokenRevokedError(TenxyteAgentTokenError):
    """The token is REVOKED — permanent, irreversible (condition 3)."""


class TenxyteTokenExpiredError(TenxyteAgentTokenError):
    """The token is EXPIRED (condition 4)."""


class TenxytePermissionDeniedError(TenxyteAIRSError):
    """Double Validation failed (condition 5): the token's grant, or the Delegating User's own
    permission, does not cover the requested action."""


class TenxyteBudgetExceededError(TenxyteAgentTokenError):
    """The token was suspended for BUDGET_EXCEEDED after reporting usage ([AIRS-BUDGET-3])."""
