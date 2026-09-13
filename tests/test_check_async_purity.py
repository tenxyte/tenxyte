"""
Tests for scripts/check_async_purity.py (spec z_aud_3, Requirement 5.4, Property 7: the
Async_Purity_Check detects no blocking pattern in adapters/fastapi/ today, and introducing one
fails the checker itself).
"""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_async_purity


def _check_source(tmp_path: Path, source: str) -> list[check_async_purity.Violation]:
    file_path = tmp_path / "sample.py"
    file_path.write_text(textwrap.dedent(source), encoding="utf-8")
    return check_async_purity.check_file(file_path)


def test_current_fastapi_adapter_is_clean():
    """The real target directory, as it stands today, has zero violations — this is the
    regression guard: it fails the moment someone reintroduces a blocking call."""
    violations = check_async_purity.check_directory()
    assert violations == [], "\n".join(str(v) for v in violations)


def test_unawaited_sync_port_method_call_is_flagged(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        async def handler(user_repo):
            user = user_repo.get_by_id(1)
            return user
        """,
    )
    assert len(violations) == 1
    assert "get_by_id" in violations[0].message


def test_awaited_call_to_the_same_method_name_is_not_flagged(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        async def handler(user_repo):
            user = await user_repo.get_by_id(1)
            return user
        """,
    )
    assert violations == []


def test_generic_dict_like_get_is_not_flagged(tmp_path):
    """`get`/`set`/`create`/`update`/`delete` are deliberately excluded — see module docstring —
    since they collide with dict.get, Headers.get, session.get, etc."""
    violations = _check_source(
        tmp_path,
        """
        async def handler(request):
            value = request.headers.get("X-Foo")
            return value
        """,
    )
    assert violations == []


def test_sync_function_nested_in_async_is_out_of_scope(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        async def handler(user_repo):
            def helper():
                return user_repo.get_by_id(1)
            return helper()
        """,
    )
    assert violations == []


def test_requests_verb_call_is_flagged(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        import requests

        async def handler():
            return requests.get("https://example.com")
        """,
    )
    assert len(violations) == 1
    assert "requests.get" in violations[0].message


def test_time_sleep_is_flagged(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        import time

        async def handler():
            time.sleep(1)
        """,
    )
    assert len(violations) == 1
    assert "time.sleep" in violations[0].message


def test_bare_open_is_flagged(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        async def handler():
            with open("file.txt") as f:
                return f.read()
        """,
    )
    assert len(violations) == 1
    assert "open(...)" in violations[0].message


def test_open_inside_to_thread_is_not_flagged(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        import asyncio

        def _read(path):
            with open(path) as f:
                return f.read()

        async def handler():
            return await asyncio.to_thread(_read, "file.txt")
        """,
    )
    assert violations == []


def test_ignore_comment_suppresses_a_violation(tmp_path):
    violations = _check_source(
        tmp_path,
        """
        async def handler(user_repo):
            return user_repo.get_by_id(1)  # async-purity: ignore[reviewed false positive]
        """,
    )
    assert violations == []


def test_module_level_sync_code_is_out_of_scope(tmp_path):
    """Only `async def` bodies are scanned — a plain sync function calling a sync port method
    is exactly what it's supposed to do."""
    violations = _check_source(
        tmp_path,
        """
        def handler(user_repo):
            return user_repo.get_by_id(1)
        """,
    )
    assert violations == []
