#!/usr/bin/env python
"""
Orchestrates one full benchmark run (spec z_aud_2, task 10.1/10.2): logs into an already-running
ephemeral Tenxyte instance (see docker-compose.yml / README.md), issues an Agent Token, runs both
bench_validation.py and bench_hitl.py, and writes combined JSON results plus a filled-in
RESULTS.md.

Usage:
    python -m spec.airs.conformance.tenxyte_ci.seed_and_serve --port 8811 &
    python benchmarks/airs/run_all.py --base-url http://localhost:8811/api/v1/auth
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

USER_EMAIL = "conformance-suite@example.com"
USER_PASSWORD = "Conformance-Suite-P4ssw0rd!"

HERE = Path(__file__).resolve().parent


def _login(base_url: str) -> str:
    response = httpx.post(f"{base_url}/login/email/", json={"email": USER_EMAIL, "password": USER_PASSWORD}, timeout=10)
    response.raise_for_status()
    return response.json()["access_token"]


def _issue_token(base_url: str, user_jwt: str) -> dict:
    # A generous circuit-breaker allowance: this benchmark deliberately fires far more requests
    # per minute than any real agent would, to get a stable latency distribution — the default
    # RPM/total limits exist to catch runaway agents, not benchmark harnesses, and would
    # otherwise start rejecting requests mid-run with AGENT_TOKEN_STATUS_SUSPENDED.
    response = httpx.post(
        f"{base_url}/ai/tokens/",
        headers={"Authorization": f"Bearer {user_jwt}"},
        json={
            "agent_id": "airs-benchmark",
            "permissions": ["conformance.test"],
            "circuit_breaker": {"max_requests_per_minute": 100000, "max_requests_total": 1000000},
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("-n", type=int, default=200)
    parser.add_argument("--hitl-n", type=int, default=50)
    args = parser.parse_args()

    user_jwt = _login(args.base_url)
    token = _issue_token(args.base_url, user_jwt)

    validation_out = HERE / "results_validation.json"
    hitl_out = HERE / "results_hitl.json"

    subprocess.run(
        [
            sys.executable,
            str(HERE / "bench_validation.py"),
            "--base-url",
            args.base_url,
            "--agent-token",
            token["token"],
            "--user-jwt",
            user_jwt,
            "-n",
            str(args.n),
            "--out",
            str(validation_out),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(HERE / "bench_hitl.py"),
            "--base-url",
            args.base_url,
            "--agent-token",
            token["token"],
            "--user-jwt",
            user_jwt,
            "-n",
            str(args.hitl_n),
            "--out",
            str(hitl_out),
        ],
        check=True,
    )

    validation_results = json.loads(validation_out.read_text(encoding="utf-8"))
    hitl_results = json.loads(hitl_out.read_text(encoding="utf-8"))

    summary = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
        },
        "validation_overhead": validation_results,
        "hitl_round_trip": hitl_results,
    }
    (HERE / "results_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
