"""
`TenxyteAgentAuth` — per-request authentication + background heartbeat (spec z_aud_2,
Requirement 4.3/4.4/4.7).

An `httpx.Auth` implementation: attach it to any `httpx.Client(auth=...)` and every outgoing
request gets `Authorization: AgentBearer <token>` and `X-Prompt-Trace-ID` automatically
([AIRS-CORE-11], [AIRS-TRACE-1]). When the Agent Token declares a heartbeat requirement, it also
runs a background daemon thread sending heartbeats at a safety margin below the required
interval (design.md: `max(1, heartbeat_required_every // 2)`), never propagating a failure —
the server's own suspension is the authority, not this client (design.md "Décision de conception
: heartbeat en tâche de fond").
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

import httpx

from .trace import resolve_trace_id

if TYPE_CHECKING:
    from .client import TenxyteAIRSClient


def heartbeat_interval_seconds(heartbeat_required_every: int) -> int:
    """[AIRS-GUARDS-4]-safe interval: strictly below the server's requirement, floor 1s."""
    return max(1, heartbeat_required_every // 2)


class TenxyteAgentAuth(httpx.Auth):
    def __init__(
        self,
        agent_token: str,
        *,
        client: TenxyteAIRSClient | None = None,
        token_id: object | None = None,
        heartbeat_required_every: int | None = None,
        run_id_provider: Callable[[], str | None] | None = None,
    ):
        self._agent_token = agent_token
        self._run_id_provider = run_id_provider or (lambda: None)

        self.heartbeat_failed = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        if heartbeat_required_every and client is not None and token_id is not None:
            interval = heartbeat_interval_seconds(heartbeat_required_every)
            self._thread = threading.Thread(target=self._heartbeat_loop, args=(client, token_id, interval), daemon=True)
            self._thread.start()

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"AgentBearer {self._agent_token}"
        request.headers.setdefault("X-Prompt-Trace-ID", resolve_trace_id(self._run_id_provider()))
        yield request

    def _heartbeat_loop(self, client: TenxyteAIRSClient, token_id: object, interval: float) -> None:
        while not self._stop_event.wait(interval):
            try:
                client.heartbeat(token_id)
                self.heartbeat_failed = False
            except Exception:  # noqa: BLE001 — never propagate from a background thread
                self.heartbeat_failed = True

    def close(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> TenxyteAgentAuth:  # noqa: PYI034 — no typing.Self on the Python 3.10 floor
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
