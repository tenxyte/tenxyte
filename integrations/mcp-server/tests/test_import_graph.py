"""
Feature: z_aud_2, Property 11 (volet MCP): Étanchéité HTTP des intégrations

Validates: Requirements 5.2, 9.3
"""

import ast
import importlib
import pathlib
import sys

import tenxyte_mcp_server

PACKAGE_ROOT = pathlib.Path(tenxyte_mcp_server.__file__).parent


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
    assert not offenders, f"tenxyte_mcp_server must never import 'tenxyte': {offenders}"


def test_no_tenxyte_module_in_sys_modules_after_import():
    importlib.reload(tenxyte_mcp_server)
    assert not any(name == "tenxyte" or name.startswith("tenxyte.") for name in sys.modules)


def test_does_not_depend_on_tenxyte_langchain():
    """The two connectors are independent packages — neither depends on the other."""
    offenders = {}
    for py_file in PACKAGE_ROOT.rglob("*.py"):
        imported = _imported_top_level_names(py_file)
        if "tenxyte_langchain" in imported:
            offenders[str(py_file)] = imported
    assert not offenders, f"tenxyte_mcp_server must not depend on tenxyte_langchain: {offenders}"


def test_declared_dependencies_exclude_tenxyte():
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    assert '"tenxyte"' not in content
    assert "tenxyte-langchain" not in content
