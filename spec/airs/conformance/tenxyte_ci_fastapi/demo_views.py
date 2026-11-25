"""
Demo business endpoints for the ephemeral FastAPI conformance CI instance (spec z_aud_2 task 4.4,
spec z_aud_3 task 9.2) — the FastAPI mirror of `tenxyte_ci/demo_views.py`.

These are ordinary integrator endpoints protected by `airs_clearance.require_agent_clearance` —
exactly what any real Tenxyte-FastAPI integration would write. They exist only so the black-box
Conformance Suite has something concrete to exercise Double Validation and the HITL contract
against, since those are properties of the dependency applied to *integrator* code, not of a
fixed Tenxyte REST endpoint (see spec/airs/conformance/README.md).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from tenxyte.adapters.fastapi.airs_clearance import AgentClearance, require_agent_clearance

CONFORMANCE_PROBE_PERMISSION = "conformance.test"

router = APIRouter()


_conformance_clearance = require_agent_clearance(permission_code=CONFORMANCE_PROBE_PERMISSION)
_hitl_clearance = require_agent_clearance(permission_code=CONFORMANCE_PROBE_PERMISSION, human_in_the_loop_required=True)


@router.api_route("/ai/_conformance_probe/", methods=["GET", "POST"])
async def conformance_probe(clearance: AgentClearance = Depends(_conformance_clearance)):  # noqa: B008
    return {"executed": True}


@router.post("/ai/_hitl_probe/")
async def hitl_probe(clearance: AgentClearance = Depends(_hitl_clearance)):  # noqa: B008
    return {"executed": True}
