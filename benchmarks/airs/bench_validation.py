#!/usr/bin/env python
"""
AIRS validation overhead benchmark (spec z_aud_2, Requirement 7.2(a)).

Measures p50/p95/p99 request latency for three targets against the same ephemeral Tenxyte
instance the AIRS Conformance Suite uses (spec/airs/conformance/tenxyte_ci/):

  1. `agent`    — AgentBearer + Double Validation, hitting a @require_agent_clearance-protected
                  demo endpoint (the conformance_probe used by the Conformance Suite).
  2. `jwt`      — a plain authenticated request (human Bearer JWT) to an equivalent endpoint
                  (`GET /me/`), isolating "the double RBAC pass" as the delta over this baseline.
  3. `baseline` — no authentication at all (the Discovery Endpoint), the floor.

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


def _time_requests(client: httpx.Client, method: str, path: str, *, headers: dict, n: int) -> list[float]:
    samples = []
    for _ in range(n):
        start = time.perf_counter()
        client.request(method, path, headers=headers)
        samples.append((time.perf_counter() - start) * 1000.0)
    return samples


def run(base_url: str, agent_token: str, user_jwt: str, n: int, warmup: int) -> dict:
    with httpx.Client(base_url=base_url, timeout=10) as client:
        targets = {
            "agent": ("GET", "/ai/_conformance_probe/", {"Authorization": f"AgentBearer {agent_token}"}),
            "jwt": ("GET", "/me/", {"Authorization": f"Bearer {user_jwt}"}),
            "baseline": ("GET", "/ai/.well-known/airs/", {}),
        }

        results = {}
        for name, (method, path, headers) in targets.items():
            _time_requests(client, method, path, headers=headers, n=warmup)  # warm-up, discarded
            samples = _time_requests(client, method, path, headers=headers, n=n)
            results[name] = asdict(_percentiles(samples))

        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="e.g. http://localhost:8811/api/v1/auth")
    parser.add_argument("--agent-token", required=True)
    parser.add_argument("--user-jwt", required=True)
    parser.add_argument("-n", type=int, default=200, help="Requests per target (after warm-up).")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--out", default=None, help="Write JSON results to this file instead of stdout.")
    args = parser.parse_args()

    results = run(args.base_url, args.agent_token, args.user_jwt, args.n, args.warmup)
    output = json.dumps(results, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
