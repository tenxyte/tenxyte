# Ephemeral Contract_Fixtures backend for the JS monorepo's Playwright E2E tests (spec z_aud_3,
# Requirement 6.6, task 14.2) — runs the real FastAPI_Adapter via seed_and_serve.py. Not a
# production deployment example: see examples/deployment/ for that (hardened multi-stage build,
# non-root user, Postgres/Redis).
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[fastapi]"

COPY examples/js-contract-backend ./examples/js-contract-backend

EXPOSE 8000
CMD ["python", "examples/js-contract-backend/seed_and_serve.py", "--host", "0.0.0.0", "--port", "8000"]
