"""
Tests for scripts/export_openapi.py (spec z_aud_3, Requirement 6.6, task 14.1, Property 12) — no
mocks: the schema-generation tests call the real drf-spectacular generator and the real FastAPI
app, same discipline as tests/test_parity_matrix.py.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import export_openapi


def test_export_django_schema_uses_prefix_free_paths():
    """Not the test project's root URLconf (which would bake in its `/auth/` mounting choice) —
    see export_openapi.py's module docstring."""
    schema = export_openapi.export_django_schema()
    assert "/register/" in schema["paths"]
    assert "post" in schema["paths"]["/register/"]


def test_export_fastapi_schema_uses_prefix_free_paths():
    schema = export_openapi.export_fastapi_schema()
    assert "/register/" in schema["paths"]
    assert "post" in schema["paths"]["/register/"]
    # organizations_enabled override applied, same as parity_matrix.get_fastapi_routes()'s own.
    assert "/organizations/" in schema["paths"]


def test_status_codes_extracts_response_keys():
    schema = {"paths": {"/x/": {"post": {"responses": {"200": {}, "400": {}}}}}}
    assert export_openapi._status_codes(schema, "POST", "/x/") == {"200", "400"}


def test_status_codes_missing_operation_is_empty_set():
    schema = {"paths": {}}
    assert export_openapi._status_codes(schema, "GET", "/does-not-exist/") == set()


def test_compute_drift_flags_only_mismatched_endpoints():
    django_schema = {
        "paths": {
            "/a/": {"post": {"responses": {"200": {}, "400": {}}}},
            "/b/": {"get": {"responses": {"200": {}}}},
        }
    }
    fastapi_schema = {
        "paths": {
            "/a/": {"post": {"responses": {"200": {}, "422": {}}}},  # mismatched
            "/b/": {"get": {"responses": {"200": {}}}},  # matches
        }
    }
    rows = export_openapi.compute_drift(django_schema, fastapi_schema, [("POST", "/a/"), ("GET", "/b/")])

    assert len(rows) == 1
    assert rows[0]["method"] == "POST"
    assert rows[0]["path"] == "/a/"
    assert rows[0]["django_codes"] == ["200", "400"]
    assert rows[0]["fastapi_codes"] == ["200", "422"]


def test_load_drift_exceptions_parses_valid_entries(tmp_path, monkeypatch):
    exceptions_file = tmp_path / "openapi_drift_exceptions.toml"
    exceptions_file.write_text(
        '[[exception]]\nendpoint = "POST /register/"\nreason = "FastAPI auto-422 vs Django 400"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(export_openapi, "DRIFT_EXCEPTIONS_PATH", exceptions_file)

    exceptions = export_openapi.load_drift_exceptions()

    assert exceptions == {("POST", "/register/"): "FastAPI auto-422 vs Django 400"}


def test_load_drift_exceptions_rejects_empty_reason(tmp_path, monkeypatch):
    exceptions_file = tmp_path / "openapi_drift_exceptions.toml"
    exceptions_file.write_text('[[exception]]\nendpoint = "GET /x/"\nreason = ""\n', encoding="utf-8")
    monkeypatch.setattr(export_openapi, "DRIFT_EXCEPTIONS_PATH", exceptions_file)

    with pytest.raises(ValueError, match="empty reason"):
        export_openapi.load_drift_exceptions()


def test_load_drift_exceptions_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(export_openapi, "DRIFT_EXCEPTIONS_PATH", tmp_path / "does-not-exist.toml")
    assert export_openapi.load_drift_exceptions() == {}


class TestMainCLI:
    def _isolate(self, tmp_path, monkeypatch):
        monkeypatch.setattr(export_openapi, "OPENAPI_DIR", tmp_path / "openapi")
        monkeypatch.setattr(export_openapi, "DJANGO_SCHEMA_PATH", tmp_path / "openapi" / "tenxyte-django.json")
        monkeypatch.setattr(export_openapi, "FASTAPI_SCHEMA_PATH", tmp_path / "openapi" / "tenxyte-fastapi.json")
        monkeypatch.setattr(export_openapi, "DRIFT_EXCEPTIONS_PATH", tmp_path / "openapi_drift_exceptions.toml")

    def test_report_only_never_fails(self, tmp_path, monkeypatch):
        self._isolate(tmp_path, monkeypatch)
        assert export_openapi.main([]) == 0
        assert (tmp_path / "openapi" / "tenxyte-django.json").exists()
        assert (tmp_path / "openapi" / "tenxyte-fastapi.json").exists()

    def test_check_drift_fails_without_exceptions_file(self, tmp_path, monkeypatch):
        self._isolate(tmp_path, monkeypatch)
        assert export_openapi.main(["--check-drift"]) == 1

    def test_bootstrap_then_check_drift_passes(self, tmp_path, monkeypatch):
        self._isolate(tmp_path, monkeypatch)
        assert export_openapi.main(["--bootstrap-exceptions"]) == 0
        assert (tmp_path / "openapi_drift_exceptions.toml").exists()
        assert export_openapi.main(["--check-drift"]) == 0
