"""
Tests for scripts/parity_matrix.py (spec z_aud_3, Requirements 4.5/5.1, Property 1: the parity
matrix is exhaustive and blocking — every Django route is either ported, justified-excluded, or
tracked as pending and only gates CI once its Parity_Group is named in --groups).
"""

import sys
from pathlib import Path
from typing import ClassVar

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import parity_matrix


def test_django_routes_are_introspected_for_real():
    """Not a hand-maintained list — this proves the introspection actually walks urlpatterns."""
    routes = parity_matrix.get_django_routes()
    assert ("POST", "/register/") in routes
    assert ("GET", "/me/") in routes
    assert ("PATCH", "/me/") in routes
    assert routes[("POST", "/register/")] == "RegisterView"
    assert len(routes) > 90  # ~114 (method, path) pairs across ~94 urlpatterns


def test_every_django_route_resolves_to_a_group():
    """Property 1's exhaustiveness depends on group_of() covering every real route — a route
    with no group would silently escape all --groups gating, which is exactly what Requirement
    4.5 forbids."""
    routes = parity_matrix.get_django_routes()
    ungrouped = [endpoint for endpoint in routes if parity_matrix.group_of(endpoint[1]) is None]
    assert ungrouped == []


def test_fastapi_routes_are_introspected_for_real():
    routes = parity_matrix.get_fastapi_routes()
    assert ("GET", "/health/") in routes


def test_normalize_django_path_converts_path_converters():
    assert parity_matrix._normalize_django_path("roles/<str:role_id>/permissions/") == "/roles/{role_id}/permissions/"
    assert parity_matrix._normalize_django_path("register/") == "/register/"


@pytest.mark.parametrize(
    "path,expected_group",
    [
        ("/register/", "A"),
        ("/me/roles/", "A"),
        ("/password/change/", "B"),
        ("/2fa/status/", "C"),
        ("/ai/tokens/", "F"),
        ("/admin/users/{user_id}/", "D"),
        ("/organizations/tree/", "E"),
        ("/webauthn/credentials/", "G"),
        ("/admin/deletion-requests/", "G"),
        ("/not-a-real-prefix/", None),
    ],
)
def test_group_of_classifies_known_prefixes(path, expected_group):
    assert parity_matrix.group_of(path) == expected_group


def test_load_exclusions_parses_valid_entries(tmp_path, monkeypatch):
    exclusions_file = tmp_path / "parity_exclusions.toml"
    exclusions_file.write_text(
        '[[exclusion]]\nendpoint = "GET /admin/django-specific/"\nreason = "Django admin, N/A outside Django"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(parity_matrix, "EXCLUSIONS_PATH", exclusions_file)

    exclusions = parity_matrix.load_exclusions()

    assert exclusions == {("GET", "/admin/django-specific/"): "Django admin, N/A outside Django"}


def test_load_exclusions_rejects_empty_reason(tmp_path, monkeypatch):
    exclusions_file = tmp_path / "parity_exclusions.toml"
    exclusions_file.write_text('[[exclusion]]\nendpoint = "GET /x/"\nreason = ""\n', encoding="utf-8")
    monkeypatch.setattr(parity_matrix, "EXCLUSIONS_PATH", exclusions_file)

    with pytest.raises(ValueError, match="empty reason"):
        parity_matrix.load_exclusions()


def test_load_exclusions_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(parity_matrix, "EXCLUSIONS_PATH", tmp_path / "does-not-exist.toml")
    assert parity_matrix.load_exclusions() == {}


class TestComputeMatrix:
    django_routes: ClassVar = {
        ("POST", "/register/"): "RegisterView",
        ("GET", "/admin/legacy/"): "LegacyAdminView",
        ("GET", "/ai/tokens/"): "AgentTokenListCreateView",
    }
    fastapi_routes: ClassVar = {("POST", "/register/"): "register"}
    exclusions: ClassVar = {("GET", "/admin/legacy/"): "Legacy Django-only admin view"}

    def test_route_present_on_both_is_ported(self):
        rows = parity_matrix.compute_matrix(self.django_routes, self.fastapi_routes, self.exclusions)
        row = next(r for r in rows if r["path"] == "/register/")
        assert row["status"] == "ported"

    def test_route_in_exclusions_is_excluded(self):
        rows = parity_matrix.compute_matrix(self.django_routes, self.fastapi_routes, self.exclusions)
        row = next(r for r in rows if r["path"] == "/admin/legacy/")
        assert row["status"] == "excluded"
        assert row["reason"] == "Legacy Django-only admin view"

    def test_route_missing_and_unexcused_is_pending(self):
        rows = parity_matrix.compute_matrix(self.django_routes, self.fastapi_routes, self.exclusions)
        row = next(r for r in rows if r["path"] == "/ai/tokens/")
        assert row["status"] == "pending"
        assert row["group"] == "F"


class TestGating:
    rows: ClassVar = [
        {"method": "GET", "path": "/ai/tokens/", "view": "x", "group": "F", "status": "pending", "reason": None},
        {"method": "POST", "path": "/register/", "view": "x", "group": "A", "status": "ported", "reason": None},
        {"method": "GET", "path": "/2fa/status/", "view": "x", "group": "C", "status": "pending", "reason": None},
    ]

    def test_resolve_groups_all(self):
        assert parity_matrix._resolve_groups("all") == set(parity_matrix.ALL_GROUPS)

    def test_resolve_groups_comma_list(self):
        assert parity_matrix._resolve_groups("a, b") == {"A", "B"}

    def test_resolve_groups_none_or_empty(self):
        assert parity_matrix._resolve_groups(None) == set()
        assert parity_matrix._resolve_groups("") == set()

    def test_gate_failure_only_for_named_groups(self):
        failures = parity_matrix.find_gate_failures(self.rows, {"F"})
        assert [r["path"] for r in failures] == ["/ai/tokens/"]

    def test_gate_no_failure_when_group_not_named(self):
        assert parity_matrix.find_gate_failures(self.rows, {"A"}) == []

    def test_gate_multiple_groups(self):
        failures = parity_matrix.find_gate_failures(self.rows, {"F", "C"})
        assert {r["path"] for r in failures} == {"/ai/tokens/", "/2fa/status/"}

    def test_ported_route_never_fails_gate_even_if_group_named(self):
        failures = parity_matrix.find_gate_failures(self.rows, {"A"})
        assert failures == []


class TestMainCLI:
    def _isolate_docs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(parity_matrix, "DOCS_EN_PATH", tmp_path / "en" / "parity_table.md")
        monkeypatch.setattr(parity_matrix, "DOCS_FR_PATH", tmp_path / "fr" / "parity_table.md")
        monkeypatch.setattr(parity_matrix, "EXCLUSIONS_PATH", tmp_path / "parity_exclusions.toml")

    def test_no_groups_never_fails(self, tmp_path, monkeypatch):
        self._isolate_docs(tmp_path, monkeypatch)
        assert parity_matrix.main([]) == 0

    def test_groups_all_fails_when_nothing_ported(self, tmp_path, monkeypatch):
        self._isolate_docs(tmp_path, monkeypatch)
        assert parity_matrix.main(["--groups=all"]) == 1

    def test_writes_both_language_docs_by_default(self, tmp_path, monkeypatch):
        self._isolate_docs(tmp_path, monkeypatch)
        parity_matrix.main([])
        assert (tmp_path / "en" / "parity_table.md").exists()
        assert (tmp_path / "fr" / "parity_table.md").exists()
        assert "Parity table" in (tmp_path / "en" / "parity_table.md").read_text(encoding="utf-8")
        assert "Table de parité" in (tmp_path / "fr" / "parity_table.md").read_text(encoding="utf-8")

    def test_no_docs_flag_skips_writing(self, tmp_path, monkeypatch):
        self._isolate_docs(tmp_path, monkeypatch)
        parity_matrix.main(["--no-docs"])
        assert not (tmp_path / "en" / "parity_table.md").exists()
