"""
Contract_Suite — Parity_Group E / Organizations (spec z_aud_3, task 11.2): the same assertions,
written once against the `api` fixture, run unchanged against both the Django_Adapter and the
FastAPI_Adapter.

Unlike Groups D/F, Group E's `create_organization`/`list_organizations` endpoints need only
`@require_jwt` — no RBAC permission promotion the `api` fixture can't grant — so a fresh
`register_and_login()`-ed user can immediately exercise a *real, successful* round trip on both
backends (create an org, become its owner, list it back), not just prove the two adapters agree
on an auth/permission gate. This file therefore compares real response shapes for those two
endpoints, plus one gate-level proof for `get_organization` (missing `X-Org-Slug`) — the same
narrower-than-A-C pattern used in `test_group_d_shapes.py`/`test_group_f_shapes.py` for the same
underlying reason (see below) applies to everything requiring an actual `X-Org-Slug` to resolve
successfully.

**Why `X-Org-Slug`-resolved endpoints (`get_organization` on success, `update_organization`,
member/invitation endpoints, ...) aren't covered here**: `DjangoContractClient` drives views
directly via `APIRequestFactory`, which never runs Django's middleware stack — so
`OrganizationContextMiddleware` (the thing that actually resolves `X-Org-Slug` into
`request.organization`) never executes, and there is no `request.organization` for the view to see
regardless of what header is sent. The *missing*-header case still works correctly by accident
(`hasattr(request, "organization")` is simply `False` on a bare `APIRequestFactory` request, which
is exactly what `require_org_context` treats as "no context provided" — no middleware simulation
needed), which is what `test_organization_detail_requires_context_identically` below exercises.
Reproducing the *success* case would require hand-simulating the middleware inside the contract
client itself — a bigger, dedicated change to shared test infrastructure, not a Group E task.
"""

import pytest

from tests.contract.conftest import register_and_login

_ORGANIZATION_FIELDS = {
    "id",
    "name",
    "slug",
    "description",
    "parent",
    "metadata",
    "is_active",
    "max_members",
    "member_count",
    "created_at",
    "updated_at",
    "created_by_email",
    "user_role",
}
"""Deliberately excludes `parent_name` — a real, Contract_Suite-caught DRF quirk (see
`org_service.py`'s `serialize_organization_async` docstring): a dotted-source `CharField`
(`source="parent.name"`) is omitted from the response entirely, not `null`, when its first hop
(`parent`) is `None` — which every organization a fresh `register_and_login()`-ed user creates
here always is (no parent given)."""

_PAGINATED_ENVELOPE_FIELDS = {"count", "page", "page_size", "total_pages", "next", "previous", "results"}


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_create_organization_identical_shape(api):
    access_token, _email = await register_and_login(api)

    response = await api.post(
        "/organizations/",
        json={"name": "Acme Corp"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 201
    assert set(response.body.keys()) == _ORGANIZATION_FIELDS
    assert response.body["name"] == "Acme Corp"
    assert response.body["slug"] == "acme-corp"
    assert response.body["user_role"] == "owner"
    assert response.body["member_count"] == 1
    assert response.body["is_active"] is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_list_organizations_after_create_identical_shape(api):
    access_token, _email = await register_and_login(api)
    headers = {"Authorization": f"Bearer {access_token}"}

    await api.post("/organizations/", json={"name": "Acme Corp"}, headers=headers)
    response = await api.get("/organizations/list/", headers=headers)

    assert response.status_code == 200
    assert set(response.body.keys()) == _PAGINATED_ENVELOPE_FIELDS
    assert response.body["count"] == 1
    assert len(response.body["results"]) == 1
    assert set(response.body["results"][0].keys()) == _ORGANIZATION_FIELDS


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_organization_detail_requires_context_identically(api):
    access_token, _email = await register_and_login(api)

    response = await api.get("/organizations/detail/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 400
    assert response.body == {
        "error": "Organization context required. Please provide X-Org-Slug header.",
        "code": "ORG_CONTEXT_REQUIRED",
    }
