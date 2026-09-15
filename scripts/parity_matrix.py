#!/usr/bin/env python
"""
Parity_Matrix (spec z_aud_3, Requirements 4.5 & 5.1, Property 1) — diffs the Django_Adapter's
routes (`tenxyte.urls.urlpatterns`, introspected directly, not hand-maintained) against the
FastAPI_Adapter's (`create_tenxyte_router()`), normalized to the same (METHOD, /relative/path/)
shape, and reports three states per Django endpoint:

  - "ported"   — the same (method, path) exists on both adapters.
  - "excluded" — listed in `parity_exclusions.toml` with a non-empty justification.
  - "pending"  — neither of the above; whether this fails the run depends on `--groups`
                 (Requirement 4.5: silent omissions are never permitted, but a route belonging
                 to a wave not yet delivered is not a silent omission — it's tracked as "pending"
                 and only gates CI once its group is named in --groups).

Usage:
    python scripts/parity_matrix.py                    # report only, never exits non-zero
    python scripts/parity_matrix.py --groups=A,B        # gate: fail if A/B has an unexcused gap
    python scripts/parity_matrix.py --groups=all        # gate on every group (full parity check)
    python scripts/parity_matrix.py --no-docs           # skip writing docs/{en,fr}/parity_table.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    # Allows `python scripts/parity_matrix.py` from the repo root without requiring the caller
    # to set PYTHONPATH — the script's own directory is Python's default sys.path[0], not the
    # repo root, so `import tests.integration...` (for DJANGO_SETTINGS_MODULE) would fail otherwise.
    sys.path.insert(0, str(REPO_ROOT))

EXCLUSIONS_PATH = REPO_ROOT / "parity_exclusions.toml"
DOCS_EN_PATH = REPO_ROOT / "docs" / "en" / "parity_table.md"
DOCS_FR_PATH = REPO_ROOT / "docs" / "fr" / "parity_table.md"

Endpoint = tuple[str, str]  # (HTTP method, normalized relative path)

ALL_GROUPS = ("A", "B", "C", "D", "E", "F", "G")

# Prefix -> Parity_Group, per tasks.md's own per-wave endpoint lists (5.1, 6.1, 7.1, 9.1, 10.1,
# 11.1, 12.1). Order doesn't matter: every prefix here is unique to exactly one group in the
# current route set (verified against the full `tenxyte.urls.urlpatterns` enumeration).
_GROUP_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("A", ("/register/", "/login/email/", "/login/phone/", "/refresh/", "/logout/", "/me/")),
    ("B", ("/password/",)),
    ("C", ("/otp/", "/login/otp/", "/magic-link/", "/2fa/")),
    ("F", ("/ai/",)),
    (
        "D",
        (
            "/permissions",
            "/roles",
            "/users/",
            "/applications",
            "/admin/users",
            "/admin/audit-logs",
            "/admin/login-attempts",
            "/admin/blacklisted-tokens",
            "/admin/refresh-tokens",
            "/dashboard/",
        ),
    ),
    ("E", ("/organizations", "/org-roles")),
    (
        "G",
        (
            "/webauthn/",
            "/social/",
            "/request-account-deletion/",
            "/confirm-account-deletion/",
            "/cancel-account-deletion/",
            "/account-deletion-status/",
            "/export-user-data/",
            "/admin/deletion-requests",
        ),
    ),
)


def group_of(path: str) -> str | None:
    """Which Parity_Group a normalized Django path belongs to, or None if none matched (a bug in
    _GROUP_PREFIXES's coverage, not a valid outcome for any route currently in tenxyte.urls)."""
    for group, prefixes in _GROUP_PREFIXES:
        if any(path.startswith(prefix) for prefix in prefixes):
            return group
    return None


_DJANGO_CONVERTER_RE = re.compile(r"<(?:[\w.]+:)?(\w+)>")


def _normalize_django_path(raw_pattern: str) -> str:
    """'roles/<str:role_id>/permissions/' -> '/roles/{role_id}/permissions/' — same converter ->
    {name} normalization FastAPI's own path-param syntax uses, so the two sides compare equal."""
    normalized = _DJANGO_CONVERTER_RE.sub(r"{\1}", raw_pattern)
    return normalized if normalized.startswith("/") else f"/{normalized}"


def _methods_of_view_class(view_class) -> list[str]:
    return [m.upper() for m in ("get", "post", "put", "patch", "delete") if hasattr(view_class, m)]


def get_django_routes() -> dict[Endpoint, str]:
    """(method, normalized path) -> view class/function name, for every route Django exposes."""
    import django
    from django.conf import settings as django_settings

    if not django_settings.configured:
        django.setup()

    from tenxyte.urls import urlpatterns

    routes: dict[Endpoint, str] = {}
    for pattern in urlpatterns:
        path = _normalize_django_path(str(pattern.pattern))
        callback = pattern.callback
        view_class = getattr(callback, "cls", None)
        name = view_class.__name__ if view_class is not None else getattr(callback, "__name__", str(callback))
        methods = _methods_of_view_class(view_class) if view_class is not None else []
        for method in methods:
            routes[(method, path)] = name
    return routes


def _iter_routes(router, path_prefix: str = ""):
    """Recursively flattens `router.routes`, descending into nested/included sub-routers —
    newer FastAPI versions represent an `include_router()`'d router lazily as an
    `_IncludedRouter` wrapper (its own `.routes` is empty; the real routes live on
    `.original_router.routes`, applied under `.include_context.prefix`) rather than eagerly
    flattening at include-time. Ducktyped (`original_router`) rather than importing that private
    class, since its name/shape isn't public API."""
    for route in router.routes:
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            nested_prefix = getattr(getattr(route, "include_context", None), "prefix", "") or ""
            yield from _iter_routes(original_router, path_prefix + nested_prefix)
        else:
            yield route, path_prefix + getattr(route, "path", "")


def get_fastapi_routes(settings=None) -> dict[Endpoint, str]:
    """(method, normalized path) -> route/endpoint name, for every route the FastAPI_Adapter's
    router exposes — normalized by stripping its configured api_prefix, the same way Django's
    routes are already prefix-free (tenxyte.urls has no prefix of its own).

    Forces `organizations_enabled=True` when no `settings` override is given (spec z_aud_3, Wave
    E, task 11.1) — Parity_Group E's router is conditionally registered, same as Django's own
    `urlpatterns`, and `tests/integration/django/settings.py` already sets
    `TENXYTE_ORGANIZATIONS_ENABLED = True` so `get_django_routes()` sees all 12 of its endpoints;
    without the same override here, every one of them would report as an unmatched "pending" gap
    regardless of how much of the group is actually built, since the *default* (env-resolved)
    settings this script would otherwise use has the flag off."""
    from tenxyte.adapters.fastapi.app import create_tenxyte_router
    from tenxyte.core.env_provider import EnvSettingsProvider
    from tenxyte.core.settings import Settings

    if settings is not None:
        resolved_settings = settings
    else:

        class _OrganizationsEnabledProvider(EnvSettingsProvider):
            def get(self, name, default=None):
                if name == "TENXYTE_ORGANIZATIONS_ENABLED":
                    return True
                return super().get(name, default)

        resolved_settings = Settings(provider=_OrganizationsEnabledProvider())
    router = create_tenxyte_router(resolved_settings)
    prefix = resolved_settings.api_prefix

    routes: dict[Endpoint, str] = {}
    for route, full_path in _iter_routes(router):
        path = full_path.removeprefix(prefix) or "/"
        methods = getattr(route, "methods", None) or set()
        name = getattr(route, "name", None) or getattr(getattr(route, "endpoint", None), "__name__", str(route))
        for method in methods - {"HEAD", "OPTIONS"}:
            routes[(method, path)] = name
    return routes


def load_exclusions() -> dict[Endpoint, str]:
    """`parity_exclusions.toml` -> {(method, path): reason}. Every entry must carry a non-empty
    `reason` (Requirement 4.5) — an exclusion without one is a config error, not a valid exclusion."""
    if not EXCLUSIONS_PATH.exists():
        return {}

    with EXCLUSIONS_PATH.open("rb") as f:
        data = tomllib.load(f)

    exclusions: dict[Endpoint, str] = {}
    for entry in data.get("exclusion", []):
        endpoint_str = entry["endpoint"]
        reason = entry.get("reason", "").strip()
        if not reason:
            raise ValueError(f"parity_exclusions.toml: endpoint {endpoint_str!r} has an empty reason")
        method, _, path = endpoint_str.partition(" ")
        exclusions[(method.upper(), path)] = reason
    return exclusions


def compute_matrix(
    django_routes: dict[Endpoint, str],
    fastapi_routes: dict[Endpoint, str],
    exclusions: dict[Endpoint, str],
) -> list[dict]:
    rows = []
    for endpoint, view_name in sorted(django_routes.items()):
        method, path = endpoint
        if endpoint in fastapi_routes:
            status, reason = "ported", None
        elif endpoint in exclusions:
            status, reason = "excluded", exclusions[endpoint]
        else:
            status, reason = "pending", None
        rows.append(
            {
                "method": method,
                "path": path,
                "view": view_name,
                "group": group_of(path),
                "status": status,
                "reason": reason,
            }
        )
    return rows


def _resolve_groups(groups_arg: str | None) -> set[str]:
    if not groups_arg:
        return set()
    if groups_arg.strip().lower() == "all":
        return set(ALL_GROUPS)
    return {g.strip().upper() for g in groups_arg.split(",") if g.strip()}


def find_gate_failures(rows: list[dict], gated_groups: set[str]) -> list[dict]:
    return [row for row in rows if row["status"] == "pending" and row["group"] in gated_groups]


_STATUS_MARKS = {"ported": "✅", "excluded": "\U0001f6ab", "pending": "\U0001f51c"}


def render_markdown(rows: list[dict], *, lang: str) -> str:
    headers = {
        "en": ("Method", "Path", "Django view", "Group", "Status"),
        "fr": ("Méthode", "Chemin", "Vue Django", "Groupe", "État"),
    }[lang]
    title = {"en": "# Parity table (Django → FastAPI)", "fr": "# Table de parité (Django → FastAPI)"}[lang]
    legend = {
        "en": "✅ ported · \U0001f6ab excluded (reason) · \U0001f51c planned wave",
        "fr": "✅ porté · \U0001f6ab exclu (raison) · \U0001f51c vague planifiée",
    }[lang]

    lines = [title, "", legend, "", f"| {' | '.join(headers)} |", f"|{'---|' * len(headers)}"]
    for row in rows:
        mark = _STATUS_MARKS[row["status"]]
        detail = row["reason"] if row["status"] == "excluded" else (row["group"] or "—")
        lines.append(f"| {row['method']} | `{row['path']}` | {row['view']} | {row['group'] or '—'} | {mark} {detail} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--groups", default=None, help="Comma-separated Parity_Group letters to gate on, or 'all'.")
    parser.add_argument("--no-docs", action="store_true", help="Don't write docs/{en,fr}/parity_table.md.")
    args = parser.parse_args(argv)

    django_routes = get_django_routes()
    fastapi_routes = get_fastapi_routes()
    exclusions = load_exclusions()
    rows = compute_matrix(django_routes, fastapi_routes, exclusions)

    if not args.no_docs:
        DOCS_EN_PATH.parent.mkdir(parents=True, exist_ok=True)
        DOCS_FR_PATH.parent.mkdir(parents=True, exist_ok=True)
        DOCS_EN_PATH.write_text(render_markdown(rows, lang="en"), encoding="utf-8")
        DOCS_FR_PATH.write_text(render_markdown(rows, lang="fr"), encoding="utf-8")

    ported = sum(1 for r in rows if r["status"] == "ported")
    print(f"Parity_Matrix: {ported}/{len(rows)} Django endpoints ported ({len(exclusions)} excluded).")

    gated_groups = _resolve_groups(args.groups)
    if not gated_groups:
        print("No --groups given: report-only run, not gating.")
        return 0

    failures = find_gate_failures(rows, gated_groups)
    if failures:
        print(f"FAILED: {len(failures)} unexcused gap(s) in gated group(s) {sorted(gated_groups)}:")
        for row in failures:
            print(f"  {row['method']} {row['path']} ({row['view']}, group {row['group']})")
        return 1

    print(f"OK: no unexcused gaps in gated group(s) {sorted(gated_groups)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
