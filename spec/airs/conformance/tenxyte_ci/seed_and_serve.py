"""
Stands up the ephemeral Tenxyte instance the AIRS Conformance Suite runs against in CI
(spec z_aud_2, task 4.4): migrates a fresh sqlite file, seeds exactly the permissions and
one test user + application the suite needs, starts a real HTTP server, logs in over HTTP to
obtain a genuine JWT, and prints a JSON line of connection info to stdout for the calling
workflow step to parse.

Usage:
    python -m spec.airs.conformance.tenxyte_ci.seed_and_serve [--port 8811]

Prints exactly one JSON line to stdout once ready, e.g.:
    {"base_url": "http://127.0.0.1:8811/api/v1/auth", "user_jwt": "eyJ...",
     "conformance_probe_path": "/api/v1/auth/ai/_conformance_probe/",
     "hitl_probe_path": "/api/v1/auth/ai/_hitl_probe/",
     "audit_log_path": "/api/v1/auth/admin/audit-logs/"}
Then serves forever until killed (SIGINT/SIGTERM/Ctrl+C).
"""

import argparse
import json
import os
import sys
import threading
from wsgiref.simple_server import WSGIRequestHandler, make_server

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

TEST_PERMISSION = "conformance.test"
EXTRA_PERMISSIONS = ["users.permissions.assign", "users.permissions.remove", "security.view"]
USER_EMAIL = "conformance-suite@example.com"
USER_PASSWORD = "Conformance-Suite-P4ssw0rd!"


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def _django_setup(db_path: str | None):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spec.airs.conformance.tenxyte_ci.settings")
    if db_path:
        os.environ["AIRS_CI_DB_PATH"] = db_path

    import django

    django.setup()


def _seed():
    from django.core.management import call_command

    call_command("migrate", verbosity=0, interactive=False)

    from tenxyte.models.base import get_application_model, get_permission_model, get_user_model

    User = get_user_model()
    Permission = get_permission_model()
    Application = get_application_model()

    for code in [TEST_PERMISSION, *EXTRA_PERMISSIONS]:
        Permission.objects.get_or_create(code=code, defaults={"name": code})

    if not Application.objects.filter(is_active=True).exists():
        Application.create_application(name="AIRS Conformance Demo")

    user, _created = User.objects.get_or_create(
        email=USER_EMAIL,
        defaults={"is_active": True, "first_name": "AIRS", "last_name": "Conformance"},
    )
    user.set_password(USER_PASSWORD)
    user.is_active = True
    user.save()

    permissions = Permission.objects.filter(code__in=[TEST_PERMISSION, *EXTRA_PERMISSIONS])
    user.direct_permissions.add(*permissions)

    return user


def _serve(host: str, port: int):
    from django.core.wsgi import get_wsgi_application

    from spec.airs.conformance.tenxyte_ci.urls import urlpatterns  # noqa: F401 — sanity import

    app = get_wsgi_application()
    server = make_server(host, port, app, handler_class=_QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _login(base_url: str) -> str:
    import httpx

    response = httpx.post(f"{base_url}/login/email/", json={"email": USER_EMAIL, "password": USER_PASSWORD}, timeout=10)
    response.raise_for_status()
    return response.json()["access_token"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8811)
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address. Use 0.0.0.0 to accept connections from other containers."
    )
    parser.add_argument("--db-path", default=None)
    args = parser.parse_args()

    _django_setup(args.db_path)
    _seed()
    server = _serve(args.host, args.port)

    # The URL this process uses to call itself (for the login below) is always loopback,
    # regardless of which host interface it bound to for external connections.
    base_url = f"http://127.0.0.1:{args.port}/api/v1/auth"
    user_jwt = _login(base_url)

    info = {
        "base_url": base_url,
        "user_jwt": user_jwt,
        "airs_test_permission": TEST_PERMISSION,
        "conformance_probe_path": f"{base_url}/ai/_conformance_probe/",
        "hitl_probe_path": f"{base_url}/ai/_hitl_probe/",
        "audit_log_path": f"{base_url}/admin/audit-logs/",
    }
    print(json.dumps(info), flush=True)

    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
