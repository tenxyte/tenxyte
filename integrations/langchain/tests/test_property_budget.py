"""
Feature: z_aud_2, Property 6: Le callback budget rapporte l'agrégation exacte

Validates: Requirements 4.5
"""

import httpx
import respx
from hypothesis import HealthCheck, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from tenxyte_langchain import TenxyteAIRSClient
from tenxyte_langchain.callbacks import TenxyteBudgetCallbackHandler

BASE_URL = "https://airs.test"


class _FakeLLMResult:
    def __init__(self, prompt_tokens, completion_tokens, style="legacy"):
        if style == "legacy":
            self.llm_output = {"token_usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}}
            self.generations = []
        else:
            self.llm_output = {}

            class _Msg:
                def __init__(self):
                    self.usage_metadata = {"input_tokens": prompt_tokens, "output_tokens": completion_tokens}

            class _Gen:
                def __init__(self):
                    self.message = _Msg()

            self.generations = [[_Gen()]]


@hyp_settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    usages=st.lists(
        st.tuples(st.integers(min_value=0, max_value=5000), st.integers(min_value=0, max_value=5000)),
        min_size=1,
        max_size=15,
    ),
    style=st.sampled_from(["legacy", "usage_metadata"]),
)
def test_property_6_reported_usage_sums_exactly(usages, style):
    """The sum of prompt/completion tokens reported to report-usage equals the sum emitted."""
    reported = []

    with respx.mock(assert_all_called=False) as router:

        def _record(request):
            import json

            body = json.loads(request.content)
            reported.append((body["prompt_tokens"], body["completion_tokens"]))
            return httpx.Response(200, json={"status": "ok"})

        router.get(f"{BASE_URL}/ai/.well-known/airs/").respond(
            200,
            json={
                "airs_version": "1.0",
                "conformance": ["core", "budget"],
                "endpoints": {"report_usage": "/ai/tokens/{id}/report-usage/"},
                "limits": {},
            },
        )
        router.post(f"{BASE_URL}/ai/tokens/1/report-usage/").mock(side_effect=_record)

        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        handler = TenxyteBudgetCallbackHandler(client, 1, cost_per_prompt_token=0.0, cost_per_completion_token=0.0)

        for prompt_tokens, completion_tokens in usages:
            handler.on_llm_end(_FakeLLMResult(prompt_tokens, completion_tokens, style=style))

    expected_prompt = sum(p for p, _ in usages)
    expected_completion = sum(c for _, c in usages)
    assert sum(p for p, _ in reported) == expected_prompt
    assert sum(c for _, c in reported) == expected_completion
    assert len(reported) == len(usages)  # no loss, no double counting
