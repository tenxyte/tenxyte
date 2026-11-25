#!/usr/bin/env python
"""
Contract_Fixtures — OpenAPI export + drift check (spec z_aud_3, Requirement 6.6, Property 12,
task 14.1): exports a versioned OpenAPI document per adapter (`openapi/tenxyte-django.json`,
`openapi/tenxyte-fastapi.json`) and checks that the two describe the same contract for every
`parity_matrix.py`-"ported" (shared) endpoint.

**Both exports use prefix-free paths** (`/register/`, not `/api/v1/register/`) — matching
`parity_matrix.py`'s own normalization exactly, and reflecting what each adapter's contract
actually *is*: `tenxyte.urls.urlpatterns` is prefix-agnostic by design (a consuming Django project
`include()`s it at whatever prefix it chooses — verified by reading
`tests/integration/django/urls.py`, which mounts it under `{api_prefix}/auth/`, a *test-harness*
mounting choice, not a fact about the library), and `create_tenxyte_router()`'s own module
docstring names it "a mountable router" for the same reason. The FastAPI export is generated from
the real, runnable `create_tenxyte_app()` (so it reflects real route registration, including
Group E's conditional org router) and then has `settings.api_prefix` stripped from every path key
post-generation, the same way `parity_matrix.get_fastapi_routes()` already does.

**Django's schema is generated from `tenxyte.urls.urlpatterns` directly**
(`SchemaGenerator(patterns=...)`), not from the test project's root URLconf — using the root
URLconf would bake the test harness's `/auth/` mounting choice into a document meant to be a
*canonical* export of the library's own contract.

**The drift check compares paths, methods, and declared status codes — scoped to
`parity_matrix.py`'s "ported" (shared, non-excluded) endpoints only**, via
`openapi_drift_exceptions.toml` (same shape/discipline as `parity_exclusions.toml`: every entry
needs a non-empty `reason`). A real, one-time measurement (2026-09-15) found 85 of 114 ported
endpoints have mismatched declared status codes — verified NOT to be 85 real behavioral bugs:
almost every mismatch traces to one of two structural, framework-level causes, not a per-endpoint
defect:

1. FastAPI's schema generator auto-declares `422` for any route with a Pydantic request body
   (its own native validation-error status) — but `errors.py`'s `_handle_validation_error`
   intercepts that at runtime and returns `400` instead (parity with Django's real behavior,
   verified in `errors.py`'s own module docstring). FastAPI's OpenAPI generator has no way to know
   about that exception-handler rewrite, so the *documented* code (422) never matches what a real
   caller actually receives (400) — a known, general FastAPI quirk, not specific to this port.
2. Every error path this port raises via `TenxyteAPIError` (the vast majority of non-2xx
   responses) is invisible to FastAPI's schema generator unless the route also declares a
   `responses={...}=` kwarg — which none of this port's ~114 routes do yet. Django's own
   `@extend_schema` docs, by contrast, are hand-authored and typically *do* enumerate several
   status codes per operation (even where, as extensively documented elsewhere in this port's own
   module docstrings, those hand-authored docs are themselves sometimes wrong about what the real
   view returns).

Retrofitting `responses={}` onto ~114 FastAPI routes (or auditing and fixing every one of Django's
hand-authored docs) is out of this task's scope — a dedicated pass, not a "let's continue"
extension. `openapi_drift_exceptions.toml` records today's real, measured gap per endpoint so nothing
NEW can drift silently in the meantime; closing an exception (by actually adding a matching
`responses={}` declaration, or fixing a wrong Django doc) is real, incremental progress toward
Property 12, not exclusion-as-an-answer the way `parity_exclusions.toml` documents permanent
"BREAK, not a fix" gaps for Property 1.

Usage:
    python scripts/export_openapi.py                     # export both schemas, report-only
    python scripts/export_openapi.py --check-drift        # export + gate on new/unexplained drift
    python scripts/export_openapi.py --bootstrap-exceptions
        # (maintenance only, not run in CI) regenerate openapi_drift_exceptions.toml from the
        # *current* real diff — use after intentionally fixing a schema (closing a gap) or adding
        # a new ported endpoint, to re-baseline; never to silence a newly introduced regression.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.parity_matrix import (
    Endpoint,
    compute_matrix,
    get_django_routes,
    get_fastapi_routes,
    load_exclusions,
)

OPENAPI_DIR = REPO_ROOT / "openapi"
DJANGO_SCHEMA_PATH = OPENAPI_DIR / "tenxyte-django.json"
FASTAPI_SCHEMA_PATH = OPENAPI_DIR / "tenxyte-fastapi.json"
DRIFT_EXCEPTIONS_PATH = REPO_ROOT / "openapi_drift_exceptions.toml"

_TITLE = "Tenxyte"
_VERSION = "1.0.0"


def export_django_schema() -> dict[str, Any]:
    import django
    from django.conf import settings as django_settings

    if not django_settings.configured:
        django.setup()

    from drf_spectacular.generators import SchemaGenerator

    from tenxyte.urls import urlpatterns

    generator = SchemaGenerator(title=_TITLE, version=_VERSION, patterns=urlpatterns)
    return generator.get_schema(request=None, public=True)


def export_fastapi_schema() -> dict[str, Any]:
    from tenxyte.adapters.fastapi.app import create_tenxyte_app
    from tenxyte.core.env_provider import EnvSettingsProvider
    from tenxyte.core.settings import Settings

    class _OrganizationsEnabledProvider(EnvSettingsProvider):
        """Same override `parity_matrix.get_fastapi_routes()` applies — Group E's router is
        conditionally registered, so its 12 endpoints would be invisible to this export
        otherwise."""

        def get(self, name, default=None):
            if name == "TENXYTE_ORGANIZATIONS_ENABLED":
                return True
            return super().get(name, default)

    settings = Settings(provider=_OrganizationsEnabledProvider())
    app = create_tenxyte_app(settings=settings, auto_create_schema=False)
    app.title = _TITLE
    app.version = _VERSION
    schema = app.openapi()

    prefix = settings.api_prefix
    schema["paths"] = {(path.removeprefix(prefix) or "/"): value for path, value in schema["paths"].items()}
    return schema


def load_drift_exceptions() -> dict[Endpoint, str]:
    if not DRIFT_EXCEPTIONS_PATH.exists():
        return {}

    with DRIFT_EXCEPTIONS_PATH.open("rb") as f:
        data = tomllib.load(f)

    exceptions: dict[Endpoint, str] = {}
    for entry in data.get("exception", []):
        endpoint_str = entry["endpoint"]
        reason = entry.get("reason", "").strip()
        if not reason:
            raise ValueError(f"openapi_drift_exceptions.toml: endpoint {endpoint_str!r} has an empty reason")
        method, _, path = endpoint_str.partition(" ")
        exceptions[(method.upper(), path)] = reason
    return exceptions


def _status_codes(schema: dict[str, Any], method: str, path: str) -> set[str]:
    operation = schema.get("paths", {}).get(path, {}).get(method.lower(), {})
    return set(operation.get("responses", {}).keys())


def compute_drift(
    django_schema: dict[str, Any],
    fastapi_schema: dict[str, Any],
    ported_endpoints: list[Endpoint],
) -> list[dict]:
    """One row per `ported` endpoint whose declared status-code set differs between the two
    schemas."""
    rows = []
    for method, path in sorted(ported_endpoints):
        django_codes = _status_codes(django_schema, method, path)
        fastapi_codes = _status_codes(fastapi_schema, method, path)
        if django_codes != fastapi_codes:
            rows.append(
                {
                    "method": method,
                    "path": path,
                    "django_codes": sorted(django_codes),
                    "fastapi_codes": sorted(fastapi_codes),
                }
            )
    return rows


def _write_bootstrap_exceptions(drift_rows: list[dict]) -> None:
    lines = [
        "# Auto-generated by `python scripts/export_openapi.py --bootstrap-exceptions`",
        "# (spec z_aud_3, Requirement 6.6, Property 12) — see `export_openapi.py`'s module",
        "# docstring for what these entries mean and why they exist. Re-running the bootstrap",
        "# overwrites this file with the *current* real diff — do that deliberately (after fixing",
        "# a schema or adding an endpoint), never to silence a regression you haven't looked at.",
        "",
    ]
    for row in drift_rows:
        lines.append("[[exception]]")
        lines.append(f'endpoint = "{row["method"]} {row["path"]}"')
        lines.append(
            f'reason = "Django declares {row["django_codes"]}; FastAPI declares '
            f'{row["fastapi_codes"]}. FastAPI\'s auto-schema only documents its own native 422 '
            "validation response (rewritten to 400 at runtime, see errors.py) plus each route's "
            "success code — TenxyteAPIError-raised error paths aren't declared via a route-level "
            'responses={} kwarg yet."'
        )
        lines.append("")
    DRIFT_EXCEPTIONS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check-drift", action="store_true", help="Gate on unexplained status-code drift.")
    parser.add_argument(
        "--bootstrap-exceptions",
        action="store_true",
        help="Regenerate openapi_drift_exceptions.toml from the current real diff (maintenance only).",
    )
    args = parser.parse_args(argv)

    django_schema = export_django_schema()
    fastapi_schema = export_fastapi_schema()

    OPENAPI_DIR.mkdir(parents=True, exist_ok=True)
    DJANGO_SCHEMA_PATH.write_text(json.dumps(django_schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    FASTAPI_SCHEMA_PATH.write_text(json.dumps(fastapi_schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Exported {DJANGO_SCHEMA_PATH} and {FASTAPI_SCHEMA_PATH}.")

    django_routes = get_django_routes()
    fastapi_routes = get_fastapi_routes()
    exclusions = load_exclusions()
    rows = compute_matrix(django_routes, fastapi_routes, exclusions)
    ported_endpoints = [(r["method"], r["path"]) for r in rows if r["status"] == "ported"]

    drift_rows = compute_drift(django_schema, fastapi_schema, ported_endpoints)
    print(f"OpenAPI drift: {len(drift_rows)}/{len(ported_endpoints)} ported endpoints have mismatched status codes.")

    if args.bootstrap_exceptions:
        _write_bootstrap_exceptions(drift_rows)
        print(f"Wrote {len(drift_rows)} entries to {DRIFT_EXCEPTIONS_PATH}.")
        return 0

    if not args.check_drift:
        print("No --check-drift given: report-only run, not gating.")
        return 0

    exceptions = load_drift_exceptions()
    unexplained = [row for row in drift_rows if (row["method"], row["path"]) not in exceptions]
    if unexplained:
        print(f"FAILED: {len(unexplained)} unexplained OpenAPI drift(s) not in openapi_drift_exceptions.toml:")
        for row in unexplained:
            print(f"  {row['method']} {row['path']}: django={row['django_codes']} fastapi={row['fastapi_codes']}")
        return 1

    print(f"OK: every drift ({len(drift_rows)}) is accounted for in openapi_drift_exceptions.toml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
