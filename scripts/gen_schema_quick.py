"""Quick OpenAPI schema regeneration using the test Django settings."""
import sys
import json
import os
import warnings

sys.path.insert(0, "src")
sys.path.insert(0, "tests/integration/django")
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

import django  # noqa: E402
django.setup()

warnings.filterwarnings("ignore")

from drf_spectacular.generators import SchemaGenerator  # noqa: E402

generator = SchemaGenerator(
    title="Tenxyte API",
    version="0.9.6.4",
    description=(
        "Framework-agnostic Python authentication — JWT, RBAC, 2FA, Magic Links, "
        "Passkeys, Social Login, B2B Organizations, multi-tenant support. "
        "Works with Django, FastAPI, and more."
    ),
)

schema = generator.get_schema(public=True)

output_path = "openapi_schema.json"
with open(output_path, "w", encoding="utf-8") as fh:
    json.dump(schema, fh, indent=2, ensure_ascii=False)

paths = list(schema.get("paths", {}).keys())
schemas = list(schema.get("components", {}).get("schemas", {}).keys())
print("Saved %d paths and %d component schemas to %s" % (len(paths), len(schemas), output_path))

new_paths = [p for p in paths if "otp" in p or "set-initial" in p]
print("New/OTP-related paths: %s" % new_paths)
