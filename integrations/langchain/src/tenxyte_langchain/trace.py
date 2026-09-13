"""Prompt Trace ID resolution ([AIRS-TRACE-1]/[AIRS-TRACE-2])."""

from __future__ import annotations

import re
import uuid

# Same character class the server accepts ([AIRS-TRACE-2]): at most 128 chars, [A-Za-z0-9_-].
_SAFE = re.compile(r"[^A-Za-z0-9_-]")


def resolve_trace_id(run_id: str | None = None) -> str:
    """Derive an `X-Prompt-Trace-ID` from a LangChain run ID when available, else a fresh uuid4."""
    if run_id:
        candidate = f"lc-{run_id}"
    else:
        candidate = f"lc-{uuid.uuid4()}"
    return _SAFE.sub("-", candidate)[:128]
