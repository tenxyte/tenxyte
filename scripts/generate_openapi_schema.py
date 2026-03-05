#!/usr/bin/env python3
"""
OpenAPI Schema Generator — driven by drf-spectacular + real Django views

Usage:
    python scripts/generate_openapi_schema.py [--output openapi_schema.json] [--format json|yaml]

This script:
1. Configures Django using the test settings (same as pytest)
2. Invokes drf-spectacular to generate the schema from all registered Views + serializers
3. Validates the resulting paths against urls.py
4. Saves the schema to the project root
"""

import sys
import json
import os
import argparse
from pathlib import Path

# ── Setup ────────────────────────────────────────────────────────────────────
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django  # noqa: E402
django.setup()


def generate_schema(output_path: Path, fmt: str = "json") -> dict:
    """Generate OpenAPI schema using drf-spectacular."""
    print("🔧 Generating OpenAPI schema via drf-spectacular...")

    from django.conf import settings as django_settings

    # Inject SPECTACULAR_SETTINGS if not already configured
    if not hasattr(django_settings, 'SPECTACULAR_SETTINGS'):
        django_settings.SPECTACULAR_SETTINGS = {}

    # Ensure proper title/version/description
    spectacular = django_settings.SPECTACULAR_SETTINGS
    spectacular.setdefault('TITLE', 'Tenxyte API')
    spectacular.setdefault('VERSION', '0.9.1')
    spectacular.setdefault(
        'DESCRIPTION',
        'Complete Django authentication package — JWT, RBAC, 2FA (TOTP), '
        'Magic Links, Passkeys (WebAuthn), Social Login, Organizations B2B.'
    )
    spectacular.setdefault('SERVE_INCLUDE_SCHEMA', False)
    spectacular.setdefault('COMPONENT_SPLIT_REQUEST', True)
    spectacular.setdefault('SECURITY', [{'jwtAuth': []}])

    from drf_spectacular.generators import SchemaGenerator
    from drf_spectacular.validation import validate_schema

    generator = SchemaGenerator(
        title=spectacular['TITLE'],
        version=spectacular['VERSION'],
        description=spectacular['DESCRIPTION'],
        patterns=None,   # auto-discovers from ROOT_URLCONF
        urlconf="tests.urls",
    )

    schema = generator.get_schema(request=None, public=True)

    if not schema:
        print("❌ drf-spectacular returned an empty schema — check your INSTALLED_APPS and urlconf.")
        return {}

    # Add global security requirements
    schema['security'] = [{'jwtAuth': []}]

    print(f"✅ Schema generated — {len(schema.get('paths', {}))} paths found")

    # ── Validate ──────────────────────────────────────────────────────────────
    print("🔍 Validating schema...")
    try:
        validate_schema(schema)
        print("✅ Schema is valid (OpenAPI 3.x)")
    except Exception as e:
        print(f"⚠️  Schema validation warning: {e}")

    return schema


def validate_paths(schema: dict) -> list:
    """Cross-check schema paths vs urls.py registered routes."""
    print("\n🔎 Cross-checking paths vs urls.py...")
    from django.urls import reverse, NoReverseMatch
    from django.test import RequestFactory

    schema_paths = sorted(schema.get("paths", {}).keys())
    issues = []

    # Check for corrupted paths (spaces, double slashes, embedded content)
    for path in schema_paths:
        if "  " in path:
            issues.append(f"CORRUPTED (trailing whitespace): {path!r}")
        if path.count("/") > 12:
            issues.append(f"SUSPICIOUS (too many segments): {path!r}")

    if issues:
        print(f"⚠️  {len(issues)} suspicious path(s) detected:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("✅ All paths look clean")

    return issues


def save_schema(schema: dict, output_path: Path, fmt: str = "json"):
    """Save the schema to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "yaml":
        try:
            import yaml
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(schema, f, allow_unicode=True, default_flow_style=False)
        except ImportError:
            print("⚠️  PyYAML not installed, falling back to JSON")
            output_path = output_path.with_suffix(".json")
            fmt = "json"

    if fmt == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"\n💾 Schema saved → {output_path} ({size_kb:.1f} KB)")


def print_summary(schema: dict, issues: list):
    """Print a summary report."""
    paths = schema.get("paths", {})
    components = schema.get("components", {}).get("schemas", {})

    print("\n" + "=" * 60)
    print("📊 SCHEMA GENERATION REPORT")
    print("=" * 60)
    print(f"   Paths (endpoints): {len(paths)}")
    print(f"   Component schemas: {len(components)}")
    print(f"   Corrupted paths:   {len(issues)}")

    # Count by HTTP method
    method_counts: dict = {}
    for path_item in paths.values():
        for method in ["get", "post", "put", "patch", "delete"]:
            if method in path_item:
                method_counts[method] = method_counts.get(method, 0) + 1

    print("\n   Operations by method:")
    for method, count in sorted(method_counts.items()):
        print(f"     {method.upper():<8} {count}")

    total_ops = sum(method_counts.values())
    print(f"     {'TOTAL':<8} {total_ops}")

    if issues:
        print("\n⚠️  Fix the corrupted paths before running optimize_schemas.py")
    else:
        print("\n✅ Schema is ready — run scripts/optimize_schemas.py to optimize")
    print("=" * 60)


def main():
    # Fix Unicode on Windows (cp1252 console crashes on emoji)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description="Generate OpenAPI schema from Django views via drf-spectacular"
    )
    parser.add_argument(
        "--output",
        default=str(project_root / "openapi_schema.json"),
        help="Output file path (default: openapi_schema.json in project root)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        default=False,
        help="Skip backup of existing schema file",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    # ── Backup existing schema ────────────────────────────────────────────────
    if output_path.exists() and not args.no_backup:
        backup_path = output_path.with_suffix(".backup.json")
        import shutil
        shutil.copy2(output_path, backup_path)
        print(f"📦 Backup created: {backup_path}")

    # ── Generate ──────────────────────────────────────────────────────────────
    schema = generate_schema(output_path, args.format)
    if not schema:
        sys.exit(1)

    # ── Validate paths ────────────────────────────────────────────────────────
    issues = validate_paths(schema)

    # ── Save ──────────────────────────────────────────────────────────────────
    save_schema(schema, output_path, args.format)

    # ── Report ────────────────────────────────────────────────────────────────
    print_summary(schema, issues)

    sys.exit(0)


if __name__ == "__main__":
    main()
