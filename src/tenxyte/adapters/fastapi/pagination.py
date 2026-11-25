"""
Pagination for the Reference_Stack's list endpoints (spec z_aud_3, Wave D, task 10.1) — mirrors
`tenxyte.pagination.TenxytePagination`'s exact response shape and query-param names (`page`,
`page_size`, default 20, max 100), the single pagination convention every Django_Adapter list
endpoint uses.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import Request

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def apply_ordering(stmt: Any, ordering: str, allowed: dict[str, Any], *, default: str) -> Any:
    """Shared `?ordering=` handling for every Wave D list endpoint (first extracted in
    `rbac_service.py`, task 10.1 chunk 1) — comma-separated fields, `-` prefix for descending,
    unknown field names silently ignored, matching `filters.apply_ordering`'s own behavior."""
    fields = [f.strip() for f in (ordering or "").split(",") if f.strip()]
    if not fields:
        fields = [default]
    for field in fields:
        desc = field.startswith("-")
        name = field[1:] if desc else field
        column = allowed.get(name)
        if column is None:
            continue
        stmt = stmt.order_by(column.desc() if desc else column.asc())
    return stmt


def get_page_params(request: Request) -> tuple[int, int]:
    """`(page, page_size)` from query params, clamped the same way DRF's `PageNumberPagination`
    does: `page` floors at 1, `page_size` is capped at `MAX_PAGE_SIZE`."""
    try:
        page = int(request.query_params.get("page", 1))
    except ValueError:
        page = 1
    page = max(page, 1)

    try:
        page_size = int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE))
    except ValueError:
        page_size = DEFAULT_PAGE_SIZE
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    return page, page_size


def paginated_response(request: Request, *, items: list[Any], count: int, page: int, page_size: int) -> dict:
    """Same shape as `TenxytePagination.get_paginated_response`: `count`, `page`, `page_size`,
    `total_pages`, `next`, `previous`, `results` — `next`/`previous` are full URLs (or `None`),
    built from the current request with only the `page` query param changed, matching DRF's own
    `get_next_link`/`get_previous_link`."""
    total_pages = math.ceil(count / page_size) if page_size else 0

    next_url = str(request.url.include_query_params(page=page + 1)) if page < total_pages else None
    previous_url = None
    if page > 1:
        previous_url = (
            str(request.url.include_query_params(page=page - 1))
            if page > 2
            else str(request.url.remove_query_params("page"))
        )

    return {
        "count": count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next": next_url,
        "previous": previous_url,
        "results": items,
    }
