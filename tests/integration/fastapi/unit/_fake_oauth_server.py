"""
A real (if fake) OAuth2 provider server for `test_social_router.py` (spec z_aud_3, Wave G chunk
2/4, task 12.1) — a genuine ASGI app, routed to via `httpx.ASGITransport` (the same mechanism this
whole test suite already uses to drive the real FastAPI app under test), not a mocked function.
`ASGITransport` dispatches purely on path/method, ignoring the request's original host — so this
app's routes are the real *paths* `social_auth_service.py` hits on each provider's real domain
(`GOOGLE_TOKEN_URL`'s path is `/token`, `GITHUB_USERINFO_URL`'s is `/user`, etc. — verified against
the actual constants in that module, not guessed), letting one fake server stand in for all five
real ones within a single test's `_test_transport` override.

Real RSA keypairs, a real JWKS document, and real RS256-signed JWTs back the Google/Apple
id_token paths — `social_auth_service.py`'s JWKS verification code runs for real against this
server's output. No `unittest.mock` anywhere.
"""

from __future__ import annotations

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

_KEY_ID = "fake-provider-key-1"


class FakeOAuthServer:
    """One RSA keypair backs both the "Google" and "Apple" id_token paths in a given test — the
    issuer/audience values are per-token claims, not baked into the key itself, so the same key
    can sign id_tokens for either provider's `verify_id_token_async` path."""

    def __init__(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_jwk = RSAAlgorithm.to_jwk(self.private_key.public_key(), as_dict=True)
        self.public_jwk.update({"kid": _KEY_ID, "use": "sig", "alg": "RS256"})

        # Scripted responses a test sets directly before making a request — keyed by provider
        # name, since each provider hits a distinct real path (no ambiguity).
        self.token_responses: dict[str, dict] = {}
        self.userinfo_responses: dict[str, dict] = {}
        self.github_emails_response: list[dict] | None = None
        self.received_requests: list[dict] = []

        self.app = Starlette(
            routes=[
                # Google
                Route("/oauth2/v3/certs", self._jwks, methods=["GET"]),
                Route("/oauth2/v3/userinfo", self._userinfo("google"), methods=["GET"]),
                # GitHub
                Route("/login/oauth/access_token", self._token("github"), methods=["POST"]),
                Route("/user", self._userinfo("github"), methods=["GET"]),
                Route("/user/emails", self._github_emails, methods=["GET"]),
                # Microsoft
                Route("/common/oauth2/v2.0/token", self._token("microsoft"), methods=["POST"]),
                Route("/v1.0/me", self._userinfo("microsoft"), methods=["GET"]),
                # Facebook
                Route("/v18.0/oauth/access_token", self._token("facebook"), methods=["POST"]),
                Route("/me", self._userinfo("facebook"), methods=["GET"]),
                # Apple
                Route("/auth/token", self._token("apple"), methods=["POST"]),
                Route("/auth/keys", self._jwks, methods=["GET"]),
                # Google's token endpoint path is also literally "/token" (same as the generic
                # path below), registered last so the more specific routes above win.
                Route("/token", self._token("google"), methods=["POST"]),
            ]
        )

    def sign_id_token(self, claims: dict) -> str:
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": _KEY_ID})

    async def _jwks(self, request: Request) -> JSONResponse:
        return JSONResponse({"keys": [self.public_jwk]})

    def _token(self, provider: str):
        async def handler(request: Request) -> JSONResponse:
            body = await request.body()
            form = dict(pair.split("=", 1) for pair in body.decode().split("&") if "=" in pair)
            self.received_requests.append({"provider": provider, "endpoint": "token", "data": form})
            response = self.token_responses.get(provider)
            if response is None:
                return JSONResponse({"error": "no_token_response_scripted"}, status_code=400)
            return JSONResponse(response)

        return handler

    def _userinfo(self, provider: str):
        async def handler(request: Request) -> JSONResponse:
            self.received_requests.append({"provider": provider, "endpoint": "userinfo"})
            response = self.userinfo_responses.get(provider)
            if response is None:
                return JSONResponse({"error": "no_userinfo_response_scripted"}, status_code=400)
            return JSONResponse(response)

        return handler

    async def _github_emails(self, request: Request) -> JSONResponse:
        return JSONResponse(self.github_emails_response or [])
