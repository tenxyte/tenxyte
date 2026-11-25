"""
HITL (Human-in-the-Loop) contract for tenxyte-langchain (spec/airs/AIRS-1.0.md §5).

Design (spec z_aud_2, design.md "Décision de conception : HITL dans LangChain — exception typée
+ reprise"): every HTTP 202 from the server raises `TenxyteHITLPending`, carrying enough to
replay the *original* request later via `.resume()`, once a human has confirmed out-of-band. The
connector never confirms or denies actions itself — that authority stays with a human, through
Tenxyte's own API, entirely outside this package (see [AIRS-CORE-21]).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import TenxyteAIRSClient


@dataclass
class PreparedRequestSnapshot:
    """Enough of the original request to replay it identically, plus a confirmation header."""

    method: str
    path: str
    kwargs: dict[str, Any] = field(default_factory=dict)


class TenxyteHITLPending(Exception):
    """
    Raised whenever a request receives HTTP 202 `pending_confirmation` ([AIRS-HITL-3]).

    Two usage patterns share this one primitive (design.md D5):
      - Simple try/except: catch it, hand `confirmation_token` to your own notification channel,
        and call `.resume()` once a human has approved it.
      - LangGraph `interrupt()`: catch it inside a tool, call `interrupt(confirmation_token)`, and
        have the resuming node call `.resume()` after the graph is resumed with human approval.
    """

    def __init__(
        self,
        confirmation_token: str,
        expires_at: str | datetime,
        *,
        client: TenxyteAIRSClient,
        snapshot: PreparedRequestSnapshot,
        message: str | None = None,
    ):
        super().__init__(message or f"Action requires human confirmation (confirmation_token={confirmation_token!r})")
        self.confirmation_token = confirmation_token
        self.expires_at = expires_at
        self._client = client
        self._snapshot = snapshot

    def resume(self):
        """
        Replay the original request with `X-Action-Confirmation` added ([AIRS-HITL-6]).

        Call this only after a human has confirmed `self.confirmation_token` through Tenxyte's
        own API — never from within this package.
        """
        kwargs = dict(self._snapshot.kwargs)
        headers = dict(kwargs.pop("headers", None) or {})
        headers["X-Action-Confirmation"] = self.confirmation_token
        return self._client.request(
            self._snapshot.method,
            self._snapshot.path,
            headers=headers,
            **kwargs,
        )
