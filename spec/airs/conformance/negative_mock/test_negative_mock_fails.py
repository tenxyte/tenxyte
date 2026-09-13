"""
Negative control wrapper test (spec z_aud_2, task 4.3 — design.md Property 4, negative half).

Starts the deliberately non-conformant mock server (server.py) in a background thread, then runs
a representative slice of the Conformance Suite against it *as a subprocess*, and asserts that
run FAILS — proving the suite actually discriminates conformant from non-conformant servers,
rather than passing everything unconditionally.

This test is tagged `negative_control` and excluded from the default collection filter CI uses for
the positive run against Tenxyte (see ../README.md) — it is meant to be invoked as its own,
separate step.
"""

import importlib.util
import socket
import subprocess
import sys
import threading
from contextlib import closing
from pathlib import Path

import pytest

_SERVER_PATH = Path(__file__).resolve().parent / "server.py"
_spec = importlib.util.spec_from_file_location("_negative_mock_server", _SERVER_PATH)
_server_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_server_module)
HITL_PROBE_PATH = _server_module.HITL_PROBE_PATH
PROBE_PATH = _server_module.PROBE_PATH
run = _server_module.run

pytestmark = pytest.mark.negative_control

CONFORMANCE_DIR = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def running_mock():
    port = _free_port()
    server = run(port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_conformance_suite_fails_against_the_negative_mock(running_mock):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(CONFORMANCE_DIR),
            "--airs-base-url",
            running_mock,
            "--airs-user-jwt",
            "not-a-real-jwt-the-mock-does-not-check-it",
            "--airs-conformance-probe-path",
            PROBE_PATH,
            "--airs-hitl-probe-path",
            HITL_PROBE_PATH,
            "-m",
            "not negative_control",
            "-q",
            "--no-header",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(CONFORMANCE_DIR.parent.parent.parent),
        check=False,
    )

    assert result.returncode != 0, (
        "the Conformance Suite passed against a deliberately non-conformant server — "
        f"it is not discriminating.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "failed" in result.stdout.lower() or "error" in result.stdout.lower()
