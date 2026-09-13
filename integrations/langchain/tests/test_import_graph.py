"""
Feature: z_aud_2, Property 11 (volet LangChain): Étanchéité HTTP des intégrations

`tenxyte_langchain` must never import the `tenxyte` package (design.md D2, the HTTP_Only_Rule):
if a connector needs an internal import, the AIRS specification is incomplete — that's the
whole point of dogfooding it through a real connector.

Validates: Requirements 4.2, 9.3
"""

import ast
import importlib
import pathlib
import sys

import tenxyte_langchain

PACKAGE_ROOT = pathlib.Path(tenxyte_langchain.__file__).parent


def _imported_top_level_names(source_path: pathlib.Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_no_source_file_imports_tenxyte():
    offenders = {}
    for py_file in PACKAGE_ROOT.rglob("*.py"):
        imported = _imported_top_level_names(py_file)
        if "tenxyte" in imported:
            offenders[str(py_file)] = imported

    assert not offenders, f"tenxyte_langchain must never import 'tenxyte': {offenders}"


def test_no_tenxyte_module_in_sys_modules_after_import():
    # Reload defensively in case an earlier test in the same process imported the real `tenxyte`
    # package for unrelated reasons (e.g. a monorepo test runner) — this connector's own import
    # must not be what pulls it in.
    importlib.reload(tenxyte_langchain)
    assert not any(name == "tenxyte" or name.startswith("tenxyte.") for name in sys.modules)


def test_declared_dependencies_exclude_tenxyte():
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    assert '"tenxyte"' not in content
    assert "tenxyte>=" not in content
    assert "tenxyte==" not in content
