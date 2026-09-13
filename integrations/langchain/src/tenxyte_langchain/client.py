"""
`TenxyteAIRSClient` — low-level HTTP client for tenxyte-langchain (spec z_aud_2, Requirement 4).

Speaks only the AIRS/1.0 wire protocol (spec/airs/AIRS-1.0.md): resolves every endpoint through
the target's Discovery Endpoint ([AIRS-DISC-1]) rather than hardcoding paths, so it works against
any conformant server, not just Tenxyte. Complies with the HTTP_Only_Rule (design.md D2): this
module never imports the `tenxyte` package.
"""

from __future__ import annotations

from typing import Any

import httpx

from .exceptions import (
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
from .hitl import PreparedRequestSnapshot, TenxyteHITLPending

_DEFAULT_DISCOVERY_PATH = "/ai/.well-known/airs/"


def _classify_error(response: httpx.Response) -> TenxyteAIRSError:
    """
    Map a non-2xx AIRS response to a typed exception.

    The specification deliberately does not mandate exact `code` strings ([AIRS-CORE-16]) — only
    that the six conditions be distinguishable. This classifier matches on substrings so it works
    against Tenxyte's own codes (`AGENT_TOKEN_STATUS_SUSPENDED`, ...) and reasonably-named
    alternatives from other implementations alike, rather than hardcoding one server's exact
    strings.
    """
    try:
        body = response.json()
    except ValueError:
        body = {"error": response.text}

    code = str(body.get("code", "")).upper()
    reason = body.get("reason") or body.get("suspended_reason")
    message = body.get("error") or body.get("message") or f"AIRS request failed with {response.status_code}"
    # Tenxyte's own report-usage endpoint responds to a budget-exceeded report with
    # {"error": "Budget exceeded", "status": "suspended"} — no "code"/"reason" field at all,
    # unlike its other suspension paths (which go through AGENT_TOKEN_STATUS_SUSPENDED). Since
    # the spec deliberately doesn't mandate a code string ([AIRS-CORE-16]), match the message
    # text too rather than assuming every implementation always populates "code"/"reason".

    if "NOT_FOUND" in code:
        return TenxyteTokenNotFoundError(message, status_code=response.status_code, body=body)
    if "BUDGET" in code or (reason and "BUDGET" in str(reason).upper()) or "BUDGET" in message.upper():
        return TenxyteBudgetExceededError(message, status_code=response.status_code, body=body)
    if "SUSPEND" in code:
        return TenxyteTokenSuspendedError(message, suspended_reason=reason, status_code=response.status_code, body=body)
    if "REVOK" in code:
        return TenxyteTokenRevokedError(message, status_code=response.status_code, body=body)
    if "EXPIR" in code:
        return TenxyteTokenExpiredError(message, status_code=response.status_code, body=body)
    if "PERMISSION" in code or response.status_code == 403:
        return TenxytePermissionDeniedError(message, status_code=response.status_code, body=body)

    return TenxyteAIRSError(message, status_code=response.status_code, body=body)


class TenxyteAIRSClient:
    """
    Low-level HTTP client: resolves endpoints via discovery, attaches whichever credential
    (`agent_token` or `user_jwt`) was configured, and raises typed exceptions.

    Use `agent_token` for the runtime, agent-side operations (`heartbeat`, `report_usage`,
    generic `request`); use `user_jwt` for setup-time, human-side operations (issuing a token in
    the first place — outside this client's scope by design, see `TenxyteAgentAuth`).
    """

    def __init__(
        self,
        base_url: str,
        *,
        agent_token: str | None = None,
        user_jwt: str | None = None,
        access_key: str | None = None,
        access_secret: str | None = None,
        discovery_path: str = _DEFAULT_DISCOVERY_PATH,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.agent_token = agent_token
        self.user_jwt = user_jwt
        self._discovery_path = discovery_path
        self._discovery: dict[str, Any] | None = None

        headers = {}
        if access_key:
            headers["X-Access-Key"] = access_key
        if access_secret:
            headers["X-Access-Secret"] = access_secret

        self._http = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout, transport=transport)

    def _auth_headers(self) -> dict[str, str]:
        if self.agent_token:
            return {"Authorization": f"AgentBearer {self.agent_token}"}
        if self.user_jwt:
            return {"Authorization": f"Bearer {self.user_jwt}"}
        return {}

    @property
    def discovery(self) -> dict[str, Any]:
        """The target's Discovery document ([AIRS-DISC-1]), fetched once and cached."""
        if self._discovery is None:
            try:
                response = self._http.get(self._discovery_path)
            except httpx.HTTPError as exc:
                raise TenxyteAIRSUnavailable(
                    f"Could not reach AIRS discovery at {self.base_url}{self._discovery_path}: {exc}"
                ) from exc
            if response.status_code != 200:
                raise TenxyteAIRSUnavailable(
                    f"AIRS discovery returned {response.status_code} at {self.base_url}{self._discovery_path}",
                    status_code=response.status_code,
                )
            self._discovery = response.json()
        return self._discovery

    def endpoint(self, name: str, **params: Any) -> str:
        """Resolve a logical endpoint name from discovery, substituting any `{param}` placeholders."""
        template = self.discovery["endpoints"][name]
        return template.format(**{k: str(v) for k, v in params.items()}) if params else template

    def require_level(self, level: str) -> None:
        """Raise `TenxyteCapabilityError` unless the target announces this Conformance Level."""
        if level not in self.discovery.get("conformance", []):
            raise TenxyteCapabilityError(f"Server at {self.base_url} does not announce AIRS level '{level}'")

    def request(self, method: str, path: str, *, trace_id: str | None = None, **kwargs: Any) -> httpx.Response:
        """
        Low-level, generic request against any AIRS (or AIRS-adjacent) endpoint. Attaches the
        configured credential and, when given, `X-Prompt-Trace-ID`. Raises `TenxyteHITLPending`
        on 202, and a typed `TenxyteAgentTokenError`/`TenxytePermissionDeniedError`/... on 4xx.
        """
        headers = dict(kwargs.pop("headers", None) or {})
        headers.update(self._auth_headers())
        if trace_id:
            headers.setdefault("X-Prompt-Trace-ID", trace_id)

        response = self._http.request(method, path, headers=headers, **kwargs)

        if response.status_code == 202:
            body = response.json()
            snapshot = PreparedRequestSnapshot(method=method, path=path, kwargs={"headers": headers, **kwargs})
            raise TenxyteHITLPending(
                body["confirmation_token"],
                body.get("expires_at"),
                client=self,
                snapshot=snapshot,
            )

        if 400 <= response.status_code < 600:
            raise _classify_error(response)

        return response

    def heartbeat(self, token_id: Any, *, trace_id: str | None = None) -> dict[str, Any]:
        """POST the heartbeat endpoint ([AIRS-GUARDS-3])."""
        return self.request("POST", self.endpoint("heartbeat", id=token_id), trace_id=trace_id).json()

    def report_usage(
        self,
        token_id: Any,
        *,
        cost_usd: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """POST the report-usage endpoint ([AIRS-BUDGET-1]). Raises `TenxyteBudgetExceededError`
        when this report pushes the token over budget."""
        self.require_level("budget")
        return self.request(
            "POST",
            self.endpoint("report_usage", id=token_id),
            json={"cost_usd": cost_usd, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
            trace_id=trace_id,
        ).json()

    def pending_actions(self) -> list[dict[str, Any]]:
        """GET the human-authenticated pending-actions listing ([AIRS-HITL-3])."""
        self.require_level("hitl")
        return self.request("GET", self.endpoint("pending_actions")).json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> TenxyteAIRSClient:  # noqa: PYI034 — no typing.Self on the Python 3.10 floor
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


__all__ = ["TenxyteAIRSClient"]
