"""
A real (if fake) GitHub OAuth2 provider server for the Contract_Backend's `seed_and_serve.py`
(specs/02-console-runtime, tâche 6.2, Action_Id `social.exchange`/`social.callback`) — a genuine
ASGI app routed to via `httpx.ASGITransport`, not a mocked function. Same mechanism and the same
intent as `tests/integration/fastapi/unit/_fake_oauth_server.py` (that one backs a pytest fixture
for `test_social_router.py` and covers all five providers + JWKS/id_token signing; this one is a
deliberately smaller, GitHub-only copy for the long-running demo server, which only needs the
`access_token` ceremony (`social.exchange`) and the `code` ceremony (`social.callback`) — neither
touches Google/Apple's id_token/JWKS path, so that machinery is left out rather than copied unused.

`ASGITransport` dispatches purely on path/method, ignoring the request's original host — so this
app's two routes are the real *paths* `social_auth_service.py` hits on GitHub's real domains
(`GITHUB_TOKEN_URL`'s path is `/login/oauth/access_token`, `GITHUB_USERINFO_URL`'s is `/user`).
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


class FakeGitHubOAuthServer:
    def __init__(self) -> None:
        self.token_response: dict | None = None
        self.userinfo_response: dict | None = None
        self.app = Starlette(
            routes=[
                Route("/login/oauth/access_token", self._token, methods=["POST"]),
                Route("/user", self._userinfo, methods=["GET"]),
            ]
        )

    async def _token(self, request: Request) -> JSONResponse:
        if self.token_response is None:
            return JSONResponse({"error": "no_token_response_scripted"}, status_code=400)
        return JSONResponse(self.token_response)

    async def _userinfo(self, request: Request) -> JSONResponse:
        if self.userinfo_response is None:
            return JSONResponse({"error": "no_userinfo_response_scripted"}, status_code=400)
        return JSONResponse(self.userinfo_response)
