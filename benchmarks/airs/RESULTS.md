# AIRS Benchmark Results

Reproduce with:

```bash
docker compose up -d --build   # or: python -m spec.airs.conformance.tenxyte_ci.seed_and_serve --port 8811
python benchmarks/airs/run_all.py --base-url http://localhost:8811/api/v1/auth -n 200 --hitl-n 50
```

Numbers below are from a real, executed run (spec z_aud_2, task 10.2) — a preliminary
development-machine data point, recorded to satisfy "at least one executed run" and to prove the
harness works end-to-end. **Treat these numbers as illustrative, not publication-grade**: low
`n`, a single unvirtualized Windows machine, no isolation from other processes. Before citing
figures in the launch article (`spec/airs/launch/`), re-run with a higher `-n` (200+) on a
quiet, dedicated machine (ideally Linux, matching the `docker-compose.yml` target environment)
and replace this section.

## Run — 2026-09-13 (preliminary, development machine)

**Machine:** Windows-11-10.0.26200-SP0, Python 3.14.6, Intel64 Family 6 Model 186 Stepping 2
(GenuineIntel). Ephemeral Tenxyte instance (`spec/airs/conformance/tenxyte_ci/`), sqlite,
single process, same machine as the client (no network hop) — the absolute numbers below are
therefore a floor, not a production-representative figure; the *relative* deltas between targets
are the more meaningful part of this preliminary pass.

### Validation overhead (`bench_validation.py`, n=50, warmup=20)

| Target | p50 (ms) | p95 (ms) | p99 (ms) | mean (ms) |
|---|---|---|---|---|
| `baseline` (no auth — Discovery Endpoint) | 15.9 | 21.8 | 26.3 | 15.3 |
| `jwt` (human Bearer JWT — `GET /me/`) | 20.8 | 32.6 | 35.7 | 21.1 |
| `agent` (AgentBearer + Double Validation) | 31.1 | 36.0 | 43.8 | 28.5 |

Reading: the delta between `jwt` and `agent` — the marginal cost of AgentBearer resolution
(SHA-256 hash lookup) plus Double Validation's two permission checks, on top of an already
JWT-authenticated request — is roughly **+10ms at p50** on this preliminary run.

### HITL round-trip (`bench_hitl.py`, n=20, warmup=5)

Full cycle: request → `202` → confirm → replay → `200`, auto-confirmed (excludes human
think-time).

| Metric | Value |
|---|---|
| p50 | 90.5 ms |
| p95 | 121.6 ms |
| p99 | 125.5 ms |
| mean | 94.3 ms |

Reading: three sequential HTTP round trips (the initial 202, the confirm, the replay) on the
same machine — the protocol overhead itself is small; most of this is the fixed cost of three
separate HTTP requests rather than any per-request AIRS-specific processing.

## Machine specifications template (for the next, official run)

```
Date:
Tenxyte version / commit:
Host: (cloud instance type / CPU model / RAM)
OS:
Python version:
Docker version (if used):
Network: (same-host / same-VPC / public internet, and the RTT baseline to the server)
Command line used:
```
