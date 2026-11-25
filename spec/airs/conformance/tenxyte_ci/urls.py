"""
URLconf for the ephemeral Tenxyte conformance CI instance (spec z_aud_2, task 4.4).

Mounts the real `tenxyte.urls` at the conventional `{API_PREFIX}/auth/` prefix (matching
tests/integration/django/urls.py and docs/en/endpoints.md), plus the two demo probe endpoints
the Conformance Suite is pointed at via --airs-conformance-probe-path / --airs-hitl-probe-path.
"""

from django.urls import include, path

from tenxyte.conf import auth_settings

from . import demo_views

api_prefix = auth_settings.API_PREFIX.strip("/")

urlpatterns = [
    path(f"{api_prefix}/auth/", include("tenxyte.urls")),
    path(f"{api_prefix}/auth/ai/_conformance_probe/", demo_views.conformance_probe, name="conformance_probe"),
    path(f"{api_prefix}/auth/ai/_hitl_probe/", demo_views.hitl_probe, name="hitl_probe"),
]
