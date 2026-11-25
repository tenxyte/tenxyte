#!/usr/bin/env python
"""
Async_Purity_Check (spec z_aud_3, Requirement 5.4, Property 7) — walks every `async def` in
`src/tenxyte/adapters/fastapi/` and forbids blocking patterns in its body:

  - Calling a sync port method directly (unawaited) — see `FORBIDDEN_SYNC_PORT_METHODS` below.
  - `requests.<verb>(...)` — a blocking HTTP call; use `httpx.AsyncClient` instead.
  - `time.sleep(...)` — blocks the event loop; use `asyncio.sleep`.
  - `open(...)` — blocking file I/O, unless it happens inside an `asyncio.to_thread`/
    `anyio.to_thread.run_sync` call (the sanctioned bridge for genuinely sync work).

A call already wrapped in `await` is never flagged (that's what makes it non-blocking, whichever
port version it resolves to). A false positive can be silenced with a trailing
`# async-purity: ignore[<reason>]` comment on the offending line — every such comment should be
reviewed, not used to bulk-suppress.

Scoping note on FORBIDDEN_SYNC_PORT_METHODS: `UserRepository`/`CacheService`'s sync ABCs share
several very generic verbs (`get`, `set`, `create`, `update`, `delete`, `count`, `exists`) with
ubiquitous, unrelated APIs already used throughout this adapter in legitimate ways
(`dict.get`, `Headers.get`, SQLAlchemy's `Session`/`AsyncSession`). Including those verbs here
would make the checker fail on code that has nothing to do with the ports it's meant to guard,
turning `# async-purity: ignore` into noise rather than a real review signal. This list is
therefore scoped to the sync ports' *distinctively named* methods only — names specific enough
that an unawaited call to one of them in async code is unambiguously either a direct sync-port
call (blocking) or a forgotten `await` (also a bug) — never a legitimate unrelated API.

Usage:
    python scripts/check_async_purity.py             # exit 1 and print file:line on any violation
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = REPO_ROOT / "src" / "tenxyte" / "adapters" / "fastapi"

# UserRepository (ports/repositories.py) + CacheService (core/cache_service.py) sync methods
# distinctive enough not to collide with unrelated APIs. See module docstring for why the
# generic verbs (get/set/create/update/delete/count/exists/list_all/increment/expire/ttl) are
# deliberately excluded.
FORBIDDEN_SYNC_PORT_METHODS: frozenset[str] = frozenset(
    {
        "get_by_id",
        "get_by_email",
        "update_last_login",
        "set_mfa_secret",
        "verify_email",
        "add_to_blacklist",
        "is_blacklisted",
        "remove_from_blacklist",
        "check_rate_limit",
        "reset_rate_limit",
    }
)

_TO_THREAD_CALLS = frozenset({"asyncio.to_thread", "anyio.to_thread.run_sync"})
_HTTP_VERBS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})
_IGNORE_MARKER = "# async-purity: ignore"


@dataclass
class Violation:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _dotted_name(node: ast.expr) -> str | None:
    """'asyncio.to_thread' from Attribute(value=Name('asyncio'), attr='to_thread'); None for
    anything not a plain dotted-name chain (e.g. a call result, a subscript)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


class _PurityVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, source_lines: list[str]):
        self.path = path
        self.source_lines = source_lines
        self.violations: list[Violation] = []
        self._async_depth = 0
        self._to_thread_depth = 0
        self._awaited_call_ids: set[int] = set()

    def _line_is_ignored(self, lineno: int) -> bool:
        if 1 <= lineno <= len(self.source_lines):
            return _IGNORE_MARKER in self.source_lines[lineno - 1]
        return False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._async_depth += 1
        self.generic_visit(node)
        self._async_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # A plain `def` nested inside an async function runs synchronously whenever it's called
        # — it isn't executing on the event loop itself, so its body is out of scope here.
        saved_depth = self._async_depth
        self._async_depth = 0
        self.generic_visit(node)
        self._async_depth = saved_depth

    def visit_Await(self, node: ast.Await) -> None:
        if isinstance(node.value, ast.Call):
            self._awaited_call_ids.add(id(node.value))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._async_depth > 0 and id(node) not in self._awaited_call_ids:
            self._check_call(node)

        dotted = _dotted_name(node.func)
        entering_to_thread = dotted in _TO_THREAD_CALLS
        if entering_to_thread:
            self._to_thread_depth += 1
        self.generic_visit(node)
        if entering_to_thread:
            self._to_thread_depth -= 1

    def _check_call(self, node: ast.Call) -> None:
        if self._line_is_ignored(node.lineno):
            return

        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_SYNC_PORT_METHODS:
            self._add(node, f"unawaited sync port method call: .{func.attr}(...)")
        elif (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "requests"
            and func.attr in _HTTP_VERBS
        ):
            self._add(node, f"blocking HTTP call: requests.{func.attr}(...) — use httpx.AsyncClient")
        elif isinstance(func, ast.Attribute) and _dotted_name(func) == "time.sleep":
            self._add(node, "blocking call: time.sleep(...) — use asyncio.sleep")
        elif isinstance(func, ast.Name) and func.id == "open" and self._to_thread_depth == 0:
            self._add(node, "blocking file I/O: open(...) outside asyncio.to_thread")

    def _add(self, node: ast.Call, message: str) -> None:
        self.violations.append(Violation(self.path, node.lineno, message))


def check_file(path: Path) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    visitor = _PurityVisitor(path, source.splitlines())
    visitor.visit(tree)
    return visitor.violations


def check_directory(target_dir: Path = TARGET_DIR) -> list[Violation]:
    violations: list[Violation] = []
    for path in sorted(target_dir.rglob("*.py")):
        violations.extend(check_file(path))
    return violations


def main(argv: list[str] | None = None) -> int:
    violations = check_directory()
    if not violations:
        print(f"Async_Purity_Check: OK — no blocking patterns found under {TARGET_DIR}.")
        return 0

    print(f"Async_Purity_Check: FAILED — {len(violations)} violation(s):")
    for violation in violations:
        print(f"  {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
