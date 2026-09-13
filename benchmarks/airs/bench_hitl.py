#!/usr/bin/env python
"""
AIRS HITL round-trip latency benchmark (spec z_aud_2, Requirement 7.2(b)).

Measures the end-to-end latency of one HITL cycle — request -> 202 -> confirm -> replay ->
response — auto-confirming immediately so the measurement excludes human think-time by
construction, isolating the protocol's own overhead.

Not part of the default test suite — invoke directly (see README.md). Does not affect any
runtime code (Requirement 7.4).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass

import httpx


@dataclass
class Percentiles:
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    n: int


def _percentiles(samples_ms: list[float]) -> Percentiles:
    ordered = sorted(samples_ms)

    def _pct(p: float) -> float:
        if not ordered:
            return float("nan")
        idx = min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))
        return ordered[idx]

    return Percentiles(
        p50_ms=_pct(50),
        p95_ms=_pct(95),
        p99_ms=_pct(99),
        mean_ms=statistics.fmean(ordered) if ordered else float("nan"),
        n=len(ordered),
    )


def _one_cycle(
    client: httpx.Client, hitl_path: str, agent_headers: dict, confirm_url_template: str, human_headers: dict
) -> float:
    start = time.perf_counter()

    response = client.post(hitl_path, headers=agent_headers, json={})
    assert response.status_code == 202, response.text
    confirmation_token = response.json()["confirmation_token"]

    confirm_response = client.post(
        confirm_url_template.format(confirmation_token=confirmation_token),
        headers=human_headers,
        json={"token": confirmation_token},
    )
    assert confirm_response.status_code == 200, confirm_response.text

    replay_headers = dict(agent_headers)
    replay_headers["X-Action-Confirmation"] = confirmation_token
    replay_response = client.post(hitl_path, headers=replay_headers, json={})
    assert replay_response.status_code == 200, replay_response.text

    return (time.perf_counter() - start) * 1000.0


def run(
    base_url: str, agent_token: str, user_jwt: str, hitl_path: str, confirm_path_template: str, n: int, warmup: int
) -> dict:
    agent_headers = {"Authorization": f"AgentBearer {agent_token}"}
    human_headers = {"Authorization": f"Bearer {user_jwt}"}

    with httpx.Client(base_url=base_url, timeout=10) as client:
        for _ in range(warmup):
            _one_cycle(client, hitl_path, agent_headers, confirm_path_template, human_headers)

        samples = [_one_cycle(client, hitl_path, agent_headers, confirm_path_template, human_headers) for _ in range(n)]

    return asdict(_percentiles(samples))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="e.g. http://localhost:8811/api/v1/auth")
    parser.add_argument("--agent-token", required=True)
    parser.add_argument("--user-jwt", required=True)
    parser.add_argument("--hitl-path", default="/ai/_hitl_probe/")
    parser.add_argument("--confirm-path-template", default="/ai/pending-actions/{confirmation_token}/confirm/")
    parser.add_argument("-n", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    results = run(
        args.base_url,
        args.agent_token,
        args.user_jwt,
        args.hitl_path,
        args.confirm_path_template,
        args.n,
        args.warmup,
    )
    output = json.dumps(results, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
