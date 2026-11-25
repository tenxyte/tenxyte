"""
Negative control mock server for the AIRS Conformance Suite (spec z_aud_2, task 4.3).

A deliberately non-conformant AIRS server, built on the Python standard library only (no
framework dependency), used solely to prove the Conformance Suite actually discriminates
conformant from non-conformant implementations (design.md Property 4, negative half).

It violates exactly three clauses of spec/airs/AIRS-1.0.md, each labeled below:

  1. [AIRS-DISC-1]: the discovery document omits `airs_version` entirely.
  2. [AIRS-CORE-9]/[AIRS-CORE-16]: EVERY Agent Token is accepted regardless of status — a
     revoked, expired, or entirely made-up token is treated identically to a valid one.
  3. [AIRS-HITL-3]: the HITL-gated probe endpoint always executes immediately (HTTP 200),
     never returning the required 202 pending-confirmation contract.

Run standalone: `python -m spec.airs.conformance.negative_mock.server --port 8999`
"""

import argparse
import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROBE_PATH = "/ai/_conformance_probe/"
HITL_PROBE_PATH = "/ai/_hitl_probe/"


class NonConformantAIRSHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def _send_json(self, status, body):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            return {}

    def do_GET(self):
        if self.path.rstrip("/") == "/ai/.well-known/airs".rstrip("/") or self.path.startswith("/ai/.well-known/airs"):
            # Violation 1 [AIRS-DISC-1]: no "airs_version" key at all.
            self._send_json(
                200,
                {
                    "conformance": ["core", "hitl"],
                    "endpoints": {
                        "tokens": "/ai/tokens/",
                        "token_detail": "/ai/tokens/{id}/",
                        "token_revoke": "/ai/tokens/{id}/revoke/",
                        "token_suspend": "/ai/tokens/{id}/suspend/",
                        "token_revoke_all": "/ai/tokens/revoke-all/",
                        "heartbeat": "/ai/tokens/{id}/heartbeat/",
                        "report_usage": "/ai/tokens/{id}/report-usage/",
                        "pending_actions": "/ai/pending-actions/",
                        "pending_action_confirm": "/ai/pending-actions/{confirmation_token}/confirm/",
                        "pending_action_deny": "/ai/pending-actions/{confirmation_token}/deny/",
                    },
                    "limits": {"token_max_lifetime": 86400, "default_expiry": 3600},
                },
            )
            return

        if self.path == PROBE_PATH:
            # Violation 2 [AIRS-CORE-9]/[AIRS-CORE-16]: no Agent Token validation whatsoever.
            self._send_json(200, {"executed": True})
            return

        if self.path.startswith("/ai/tokens/") and self.path.endswith("/"):
            self._send_json(200, {"id": 1, "status": "ACTIVE"})
            return

        self._send_json(404, {"error": "Not found", "code": "NOT_FOUND"})

    def do_POST(self):
        body = self._read_json_body()

        if self.path == "/ai/tokens/":
            # Issues a fixed, predictable raw token — no real permission or ownership checks.
            self._send_json(
                201,
                {
                    "id": 1,
                    "token": "non-conformant-fixed-token",
                    "agent_id": body.get("agent_id", "mock-agent"),
                    "status": "ACTIVE",
                    "expires_at": "2999-01-01T00:00:00Z",
                },
            )
            return

        if self.path == PROBE_PATH:
            # Violation 2, mirrored on POST: always accepted, whatever the AgentBearer value.
            self._send_json(200, {"executed": True})
            return

        if self.path == HITL_PROBE_PATH:
            # Violation 3 [AIRS-HITL-3]: executes immediately instead of returning 202.
            self._send_json(200, {"executed": True})
            return

        if self.path.endswith("/revoke/") or self.path.endswith("/suspend/"):
            self._send_json(200, {"status": "ok"})
            return

        if self.path.endswith("/heartbeat/") or self.path.endswith("/report-usage/"):
            # Violation 2, mirrored: accepted regardless of the presented token's real status.
            self._send_json(200, {"status": "ok"})
            return

        if "/pending-actions/" in self.path:
            self._send_json(200, {"status": "confirmed" if "confirm" in self.path else "denied"})
            return

        self._send_json(404, {"error": "Not found", "code": "NOT_FOUND"})


def run(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), NonConformantAIRSHandler)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8999)
    args = parser.parse_args()

    server = run(args.port)
    print(f"Non-conformant AIRS mock listening on http://127.0.0.1:{args.port} (token={uuid.uuid4().hex[:8]} run id)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
