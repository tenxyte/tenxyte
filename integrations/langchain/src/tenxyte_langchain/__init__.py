"""
tenxyte-langchain — LangChain/LangGraph connector for AIRS/1.0 (spec/airs/AIRS-1.0.md).

A pure HTTP client: never imports the `tenxyte` package (HTTP_Only_Rule, design.md D2). Everything
it does is speak the wire protocol Tenxyte's reference implementation formalizes, discovered at
runtime from the target server — it works against any AIRS-conformant server.
"""

from .auth import TenxyteAgentAuth
from .callbacks import TenxyteBudgetCallbackHandler
from .client import TenxyteAIRSClient
from .exceptions import (
    TenxyteAgentTokenError,
    TenxyteAIRSError,
    TenxyteAIRSUnavailable,
    TenxyteBudgetExceededError,
    TenxyteCapabilityError,
    TenxytePermissionDeniedError,
    TenxyteTokenExpiredError,
    TenxyteTokenNotFoundError,
    TenxyteTokenRevokedError,
    TenxyteTokenSuspendedError,
)
from .hitl import TenxyteHITLPending

__version__ = "0.1.0"

__all__ = [
    "TenxyteAIRSClient",
    "TenxyteAIRSError",
    "TenxyteAIRSUnavailable",
    "TenxyteAgentAuth",
    "TenxyteAgentTokenError",
    "TenxyteBudgetCallbackHandler",
    "TenxyteBudgetExceededError",
    "TenxyteCapabilityError",
    "TenxyteHITLPending",
    "TenxytePermissionDeniedError",
    "TenxyteTokenExpiredError",
    "TenxyteTokenNotFoundError",
    "TenxyteTokenRevokedError",
    "TenxyteTokenSuspendedError",
]
