"""
Minimal AIRS/1.0 HTTP client for tenxyte-mcp-server.

Deliberately self-contained — this package does not depend on `tenxyte-langchain` (design.md:
"réutilise le protocole, pas le package LC"), so the two connectors stay independently
installable and versioned. Complies with the HTTP_Only_Rule: never imports `tenxyte`.
"""

from __future__ import annotations

from typing import Any

import httpx

_DEFAULT_DISCOVERY_PATH = "/ai/.well-known/airs/"


class AIRSError(Exception):
    """Raised for any non-2xx AIRS response. `code`/`reason` mirror the server's own fields
    when present (spec/airs/AIRS-1.0.md §8) — not guaranteed to be non-None."""

    def __init__(
        self, message: str, *, code: str | None = None, reason: str | None = None, status_code: int | None = None
    ):
        super().__init__(message)
        self.code = code
        self.reason = reason
        self.status_code = status_code

    def as_dict(self) -> dict[str, Any]:
        return {"error": str(self), "code": self.code, "reason": self.reason, "status_code": self.status_code}


class AIRSClient:
    def __init__(
        self,
        base_url: str,
        agent_token: str,
        *,
        access_key: str | None = None,
        access_secret: str | None = None,
        discovery_path: str = _DEFAULT_DISCOVERY_PATH,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.agent_token = agent_token
        self._discovery_path = discovery_path
        self._discovery: dict[str, Any] | None = None

        headers = {"Authorization": f"AgentBearer {agent_token}"}
        if access_key:
            headers["X-Access-Key"] = access_key
        if access_secret:
            headers["X-Access-Secret"] = access_secret

        self._http = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout, transport=transport)

    @property
    def discovery(self) -> dict[str, Any]:
        if self._discovery is None:
            response = self._http.get(self._discovery_path)
            if response.status_code != 200:
                raise AIRSError(f"AIRS discovery returned {response.status_code}", status_code=response.status_code)
            self._discovery = response.json()
        return self._discovery

    def endpoint(self, name: str, **params: Any) -> str:
        template = self.discovery["endpoints"][name]
        return template.format(**{k: str(v) for k, v in params.items()}) if params else template

    def require_level(self, level: str) -> None:
        if level not in self.discovery.get("conformance", []):
            raise AIRSError(f"Server does not announce AIRS level '{level}'", code="CAPABILITY_MISSING")

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self._http.request(method, path, **kwargs)
        if 400 <= response.status_code < 600:
            try:
                body = response.json()
            except ValueError:
                body = {"error": response.text}
            raise AIRSError(
                body.get("error") or body.get("message") or f"AIRS request failed ({response.status_code})",
                code=body.get("code"),
                reason=body.get("reason") or body.get("suspended_reason"),
                status_code=response.status_code,
            )
        return response

    def heartbeat(self, token_id: Any) -> dict[str, Any]:
        return self._request("POST", self.endpoint("heartbeat", id=token_id)).json()

    def report_usage(
        self, token_id: Any, *, cost_usd: float = 0.0, prompt_tokens: int = 0, completion_tokens: int = 0
    ) -> dict[str, Any]:
        self.require_level("budget")
        return self._request(
            "POST",
            self.endpoint("report_usage", id=token_id),
            json={"cost_usd": cost_usd, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
        ).json()

    def pending_actions(self) -> list[dict[str, Any]]:
        self.require_level("hitl")
        return self._request("GET", self.endpoint("pending_actions")).json()

    def close(self) -> None:
        self._http.close()
