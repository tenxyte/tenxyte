# AIRS Benchmarks

Reproducible measurements of AIRS's overhead (spec z_aud_2, Requirement 7). Not part of the
default test suite (`pytest`) and does not affect any runtime code — invoke directly.

## Quick start

```bash
docker compose up -d --build
# once healthy:
python run_all.py --base-url http://localhost:8811/api/v1/auth -n 200 --hitl-n 50
```

Without Docker, run the ephemeral instance directly instead of `docker compose up`:

```bash
python -m spec.airs.conformance.tenxyte_ci.seed_and_serve --port 8811 &
python run_all.py --base-url http://localhost:8811/api/v1/auth -n 200 --hitl-n 50
```

This logs in as the demo user, issues a benchmark-only Agent Token (a generous circuit-breaker
allowance, so the harness's own request volume doesn't trip rate limiting mid-run), runs both
scripts below, and writes `results_summary.json` plus the two individual result files.

## `bench_validation.py`

p50/p95/p99 latency for three targets: `agent` (AgentBearer + Double Validation), `jwt` (a plain
authenticated request), `baseline` (no authentication) — isolating AIRS's own marginal cost.

## `bench_hitl.py`

End-to-end latency of one HITL cycle (request → 202 → confirm → replay → response),
auto-confirmed to exclude human think-time.

## Results

See [`RESULTS.md`](RESULTS.md) for the current recorded run and machine specifications template.
