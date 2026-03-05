#!/usr/bin/env python3
"""
Postman Collection Generator — Schema-Driven

This script generates a Postman collection **directly from the OpenAPI schema**:
1. Reads openapi_schema.json (or openapi_schema_optimized.json)
2. Groups all endpoints by their OpenAPI tags → Postman folders
3. Builds requests dynamically (method, URL, body examples, path params)
4. Does NOT hardcode any endpoint — 100% driven by the schema

Usage:
    python scripts/generate_postman_collection.py [--schema openapi_schema.json]
"""

import json
import sys
import uuid
import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Project setup ─────────────────────────────────────────────────────────────
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ── Helpers ───────────────────────────────────────────────────────────────────

HTTP_METHODS = ["get", "post", "put", "patch", "delete"]

# Canonical folder order (based on OpenAPI tags)
TAG_ORDER = [
    "Auth",
    "2FA",
    "OTP",
    "Password",
    "User",
    "RBAC",
    "Roles",
    "Permissions",
    "Applications",
    "Organizations",
    "Account",
    "GDPR",
    "Magic Link",
    "WebAuthn",
    "Social",
    "Agent",
    "AI",
    "Dashboard",
    "Admin",
    "Admin - Users",
    "Admin - Security",
    "Admin - GDPR",
]

# Emoji prefix per tag group
TAG_ICONS = {
    "Auth": "🔐",
    "2FA": "🔑",
    "OTP": "📱",
    "Password": "🔒",
    "User": "👤",
    "RBAC": "🛡️",
    "Roles": "🎭",
    "Permissions": "🔑",
    "Applications": "📦",
    "Organizations": "🏢",
    "Account": "🗑️",
    "GDPR": "🔏",
    "Magic Link": "✨",
    "WebAuthn": "🔐",
    "Social": "🌐",
    "Agent": "🤖",
    "AI": "🤖",
    "Dashboard": "📊",
    "Admin": "👑",
    "Admin - Users": "👑",
    "Admin - Security": "🛡️",
    "Admin - GDPR": "🔏",
}


def load_schema(schema_path: Path) -> Dict:
    """Load OpenAPI schema from disk (optimized version preferred)."""
    candidates = []
    if schema_path:
        candidates.append(schema_path)
    candidates += [
        project_root / "openapi_schema_optimized.json",
        project_root / "openapi_schema.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"📋 Loaded schema: {candidate.name} ({len(data.get('paths', {}))} paths)")
                return data
            except Exception as e:
                print(f"⚠️  Failed to load {candidate}: {e}")
    print("❌ No valid schema file found. Run scripts/generate_openapi_schema.py first.")
    return {}


def extract_example_body(operation: Dict) -> Optional[Dict]:
    """Extract the first example body from requestBody.content."""
    req_body = operation.get("requestBody", {})
    content = req_body.get("content", {})

    for content_type in ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]:
        ct_spec = content.get(content_type, {})
        if not ct_spec:
            continue

        # Try examples first (named example objects)
        examples = ct_spec.get("examples", {})
        if examples:
            # Pick the first non-error example if possible
            for ex_name, ex_obj in examples.items():
                val = ex_obj.get("value", {})
                if isinstance(val, dict) and not val.get("error"):
                    return val
            # Fall back to first example
            first = next(iter(examples.values()), {})
            return first.get("value")

        # Try inline example
        if "example" in ct_spec:
            return ct_spec["example"]

        # Try to construct from schema properties
        schema = ct_spec.get("schema", {})
        if schema:
            return schema_to_example(schema)

    return None


def schema_to_example(schema: Dict, depth: int = 0) -> Any:
    """Generate a minimal example value from a JSON Schema object."""
    if depth > 3:
        return None

    if "$ref" in schema:
        return {}

    stype = schema.get("type")
    fmt = schema.get("format", "")

    if stype == "object" or "properties" in schema:
        result = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            result[prop_name] = schema_to_example(prop_schema, depth + 1)
        return result
    elif stype == "array":
        items = schema.get("items", {})
        return [schema_to_example(items, depth + 1)]
    elif stype == "string":
        if fmt == "email":
            return "user@example.com"
        elif fmt == "date-time":
            return "2025-01-01T00:00:00Z"
        elif fmt == "date":
            return "2025-01-01"
        elif fmt == "uri":
            return "https://example.com"
        return schema.get("example", "string")
    elif stype == "integer":
        return schema.get("example", 1)
    elif stype == "number":
        return schema.get("example", 1.0)
    elif stype == "boolean":
        return schema.get("example", True)
    return None


def openapi_path_to_postman_url(path: str, base_url: str = "{{baseUrl}}") -> Dict:
    """Convert an OpenAPI path like /api/v1/auth/{user_id}/ to Postman URL."""
    # Replace {param} with :param style for Postman URL display
    # but keep {{}} for Postman variables
    raw = base_url + path

    # Split path into segments, replacing {param} with :param
    path_parts = []
    for segment in path.strip("/").split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            # Postman path variable
            param_name = segment[1:-1]
            path_parts.append(f":{param_name}")
        else:
            path_parts.append(segment)

    # For the raw URL display, keep original {param} syntax
    raw_display = base_url + path

    return {
        "raw": raw_display,
        "host": [base_url],
        "path": path.strip("/").split("/"),
        "variable": [
            {"key": seg[1:-1], "value": "", "description": f"Path parameter: {seg[1:-1]}"}
            for seg in path.strip("/").split("/")
            if seg.startswith("{") and seg.endswith("}")
        ],
    }


def build_request(path: str, method: str, operation: Dict) -> Dict:
    """Build a Postman request item from an OpenAPI operation."""
    summary = operation.get("summary", f"{method.upper()} {path}")
    description = operation.get("description", "")

    request: Dict[str, Any] = {
        "method": method.upper(),
        "header": [],
        "description": description or summary,
    }

    # URL
    request["url"] = openapi_path_to_postman_url(path)

    # Body (for POST/PUT/PATCH)
    if method in ("post", "put", "patch"):
        body_example = extract_example_body(operation)
        req_body = operation.get("requestBody", {})
        content = req_body.get("content", {})

        if "multipart/form-data" in content:
            # File upload
            fd_schema = content["multipart/form-data"].get("schema", {})
            formdata = []
            for prop_name, prop_schema in fd_schema.get("properties", {}).items():
                entry: Dict[str, Any] = {"key": prop_name, "type": "text", "value": ""}
                if prop_schema.get("format") == "binary":
                    entry["type"] = "file"
                formdata.append(entry)
            request["body"] = {"mode": "formdata", "formdata": formdata}
            request["header"].append({"key": "Content-Type", "value": "multipart/form-data"})
        elif body_example is not None:
            request["body"] = {
                "mode": "raw",
                "raw": json.dumps(body_example, indent=2, ensure_ascii=False),
                "options": {"raw": {"language": "json"}},
            }
            request["header"].append({"key": "Content-Type", "value": "application/json"})
        elif req_body:
            request["body"] = {"mode": "raw", "raw": "{}", "options": {"raw": {"language": "json"}}}
            request["header"].append({"key": "Content-Type", "value": "application/json"})

    # Query parameters
    query_params = [
        p for p in operation.get("parameters", []) if p.get("in") == "query"
    ]
    if query_params:
        request["url"]["query"] = [
            {
                "key": p["name"],
                "value": "",
                "description": p.get("description", ""),
                "disabled": True,
            }
            for p in query_params
        ]

    # Build a basic test script
    test_script = build_test_script(operation)

    item: Dict[str, Any] = {
        "name": f"{method.upper()} {summary}",
        "request": request,
    }
    if test_script:
        item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": test_script}}]

    return item


def build_test_script(operation: Dict) -> List[str]:
    """Generate a minimal Postman test script from the operation responses."""
    responses = operation.get("responses", {})
    success_codes = [int(c) for c in responses if str(c).startswith("2")]
    error_codes = [int(c) for c in responses if str(c).startswith("4")]

    lines = []
    if success_codes:
        codes_str = ", ".join(str(c) for c in success_codes)
        lines += [
            f"pm.test('Response is successful', function () {{",
            f"    pm.expect(pm.response.code).to.be.oneOf([{codes_str}]);",
            "});",
        ]

    lines += [
        "",
        "pm.test('Response time < 5000ms', function () {",
        "    pm.expect(pm.response.responseTime).to.be.below(5000);",
        "});",
    ]

    # Auto-extract tokens from login responses
    op_id = operation.get("operationId", "")
    if "login" in op_id.lower() or "token" in op_id.lower():
        lines += [
            "",
            "if (pm.response.code === 200) {",
            "    const r = pm.response.json();",
            "    if (r.access) pm.collectionVariables.set('accessToken', r.access);",
            "    if (r.refresh) pm.collectionVariables.set('refreshToken', r.refresh);",
            "}",
        ]

    return lines


def group_by_tags(schema: Dict) -> Dict[str, List[Tuple[str, str, Dict]]]:
    """Group (path, method, operation) triples by their first tag."""
    groups: Dict[str, List] = {}
    untagged: List = []

    for path, path_item in schema.get("paths", {}).items():
        for method in HTTP_METHODS:
            op = path_item.get(method)
            if not op:
                continue
            tags = op.get("tags", [])
            if tags:
                tag = tags[0]
            else:
                tag = "_Untagged"
            groups.setdefault(tag, []).append((path, method, op))

    # Sort tags: TAG_ORDER first, then alphabetical
    def tag_sort_key(t: str) -> Tuple[int, str]:
        try:
            return (TAG_ORDER.index(t), t)
        except ValueError:
            return (len(TAG_ORDER), t)

    return dict(sorted(groups.items(), key=lambda kv: tag_sort_key(kv[0])))


def build_collection(schema: Dict) -> Dict:
    """Build the full Postman collection from the schema."""
    info = schema.get("info", {})
    title = info.get("title") or "Tenxyte API"
    version = info.get("version") or "latest"

    collection: Dict[str, Any] = {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": f"{title} (v{version})",
            "description": (
                info.get("description")
                or "Generated from OpenAPI schema — schema-driven, no hardcoding."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "baseUrl", "value": "http://localhost:8000", "type": "string"},
            {"key": "accessToken", "value": "", "type": "string"},
            {"key": "refreshToken", "value": "", "type": "string"},
            {"key": "orgSlug", "value": "acme-corp", "type": "string"},
            {"key": "userEmail", "value": "user@example.com", "type": "string"},
            {"key": "userPassword", "value": "password123", "type": "string"},
        ],
        "event": [
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "// Global pre-request: inject JWT if available",
                        "const token = pm.collectionVariables.get('accessToken');",
                        "if (token) {",
                        "    pm.request.headers.upsert({ key: 'Authorization', value: 'Bearer ' + token });",
                        "}",
                        "const slug = pm.collectionVariables.get('orgSlug');",
                        "if (slug) {",
                        "    pm.request.headers.upsert({ key: 'X-Org-Slug', value: slug });",
                        "}",
                    ],
                },
            }
        ],
        "item": [],
    }

    groups = group_by_tags(schema)
    total_requests = 0

    for tag, operations in groups.items():
        icon = TAG_ICONS.get(tag, "📂")
        folder: Dict[str, Any] = {
            "name": f"{icon} {tag}",
            "item": [],
            "description": f"Endpoints tagged: {tag}",
        }

        for path, method, operation in operations:
            try:
                item = build_request(path, method, operation)
                folder["item"].append(item)
                total_requests += 1
            except Exception as e:
                print(f"  ⚠️  Skipped {method.upper()} {path}: {e}")

        collection["item"].append(folder)

    print(f"✅ Built collection: {len(groups)} folders, {total_requests} requests")
    return collection


def build_environment(base_url: str = "http://localhost:8000") -> Dict:
    """Build a Postman environment file."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Tenxyte API — Local",
        "values": [
            {"key": "baseUrl", "value": base_url, "type": "default", "enabled": True,
             "description": "Base URL of the Tenxyte API server"},
            {"key": "accessToken", "value": "", "type": "secret", "enabled": True,
             "description": "JWT access token (auto-populated after login)"},
            {"key": "refreshToken", "value": "", "type": "secret", "enabled": True,
             "description": "JWT refresh token (auto-populated after login)"},
            {"key": "orgSlug", "value": "acme-corp", "type": "default", "enabled": True,
             "description": "Organization slug for multi-tenant requests"},
            {"key": "userEmail", "value": "user@example.com", "type": "default", "enabled": True,
             "description": "Email for test login"},
            {"key": "userPassword", "value": "password123", "type": "secret", "enabled": True,
             "description": "Password for test login"},
        ],
    }


def save_json(data: Dict, path: Path) -> None:
    """Save JSON to file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    size_kb = path.stat().st_size / 1024
    print(f"💾 Saved: {path.name} ({size_kb:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Generate Postman collection from OpenAPI schema")
    parser.add_argument(
        "--schema",
        default=None,
        help="Path to OpenAPI schema JSON (default: auto-discover)",
    )
    parser.add_argument(
        "--output",
        default=str(project_root / "tenxyte_api_collection.postman_collection.json"),
        help="Output path for Postman collection",
    )
    parser.add_argument(
        "--env-output",
        default=str(project_root / "tenxyte_api_environment.postman_environment.json"),
        help="Output path for Postman environment",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the environment (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    schema_path = Path(args.schema) if args.schema else None

    # 1. Load schema
    schema = load_schema(schema_path)
    if not schema:
        sys.exit(1)

    # 2. Build collection
    print("\n📮 Building Postman collection...")
    collection = build_collection(schema)

    # 3. Build environment
    environment = build_environment(args.base_url)

    # 4. Save
    print()
    save_json(collection, Path(args.output))
    save_json(environment, Path(args.env_output))

    # 5. Summary
    def count_requests(items: list) -> int:
        count = 0
        for item in items:
            if "item" in item:
                count += count_requests(item["item"])
            elif "request" in item:
                count += 1
        return count

    total = count_requests(collection["item"])
    print(f"\n{'=' * 55}")
    print("📮 POSTMAN COLLECTION SUMMARY")
    print(f"{'=' * 55}")
    print(f"   Folders:  {len(collection['item'])}")
    print(f"   Requests: {total}")
    print(f"   Variables: {len(collection['variable'])}")
    print(f"\n   Import into Postman:")
    print(f"   1. File → Import → {Path(args.output).name}")
    print(f"   2. File → Import → {Path(args.env_output).name}")
    print(f"   3. Select 'Tenxyte API — Local' environment")
    print(f"   4. Run 'POST Login (email)' to get tokens")
    print(f"{'=' * 55}")

    sys.exit(0)


if __name__ == "__main__":
    main()
