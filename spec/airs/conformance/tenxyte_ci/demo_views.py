"""
Demo business endpoints for the ephemeral Tenxyte conformance CI instance (spec z_aud_2, task 4.4).

These are ordinary integrator endpoints protected by Tenxyte's own `@require_agent_clearance`
decorator — exactly what any real Tenxyte integration would write. They exist only so the
black-box Conformance Suite has something concrete to exercise Double Validation and the HITL
contract against, since those are properties of the decorator applied to *integrator* code, not
of a fixed Tenxyte REST endpoint (see spec/airs/conformance/README.md).
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from tenxyte.decorators import require_agent_clearance

CONFORMANCE_PROBE_PERMISSION = "conformance.test"


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_agent_clearance(permission_code=CONFORMANCE_PROBE_PERMISSION)
def conformance_probe(request):
    return JsonResponse({"executed": True})


@csrf_exempt
@require_http_methods(["POST"])
@require_agent_clearance(permission_code=CONFORMANCE_PROBE_PERMISSION, human_in_the_loop_required=True)
def hitl_probe(request):
    return JsonResponse({"executed": True})
