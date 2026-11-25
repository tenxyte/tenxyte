"""
`TenxyteBudgetCallbackHandler` — LangChain callback reporting LLM usage to AIRS's Budget
Guardrail (spec z_aud_2, Requirement 4.5; spec/airs/AIRS-1.0.md §6.3).

Tenxyte does not compute cost from token counts itself ([AIRS-BUDGET-2]) — that stays the
caller's responsibility, so this handler accepts either a linear per-token price or a custom
`cost_fn(prompt_tokens, completion_tokens) -> float`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import BaseCallbackHandler

if TYPE_CHECKING:
    from .client import TenxyteAIRSClient


def _extract_usage(response: Any) -> tuple[int, int]:
    """
    Read either LangChain usage shape: legacy `llm_output.token_usage`/`.usage` (OpenAI-style
    dict with `prompt_tokens`/`completion_tokens` or `input_tokens`/`output_tokens`), or the
    newer per-generation `message.usage_metadata` (`input_tokens`/`output_tokens`).
    """
    prompt_tokens = 0
    completion_tokens = 0

    llm_output = getattr(response, "llm_output", None) or {}
    usage = llm_output.get("token_usage") or llm_output.get("usage")
    if usage:
        prompt_tokens += usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        completion_tokens += usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        return prompt_tokens, completion_tokens

    for generation_list in getattr(response, "generations", None) or []:
        for generation in generation_list:
            message = getattr(generation, "message", None)
            usage_metadata = getattr(message, "usage_metadata", None) if message else None
            if usage_metadata:
                prompt_tokens += usage_metadata.get("input_tokens", 0) or 0
                completion_tokens += usage_metadata.get("output_tokens", 0) or 0

    return prompt_tokens, completion_tokens


class TenxyteBudgetCallbackHandler(BaseCallbackHandler):
    def __init__(
        self,
        client: TenxyteAIRSClient,
        token_id: object,
        *,
        cost_per_prompt_token: float = 0.0,
        cost_per_completion_token: float = 0.0,
        cost_fn: Callable[[int, int], float] | None = None,
    ):
        self._client = client
        self._token_id = token_id
        self._cost_per_prompt_token = cost_per_prompt_token
        self._cost_per_completion_token = cost_per_completion_token
        self._cost_fn = cost_fn

    def _cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        if self._cost_fn is not None:
            return self._cost_fn(prompt_tokens, completion_tokens)
        return prompt_tokens * self._cost_per_prompt_token + completion_tokens * self._cost_per_completion_token

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        prompt_tokens, completion_tokens = _extract_usage(response)
        cost_usd = self._cost_usd(prompt_tokens, completion_tokens)
        # Raises TenxyteBudgetExceededError if this report suspends the token ([AIRS-BUDGET-3]) —
        # intentionally not caught here: the agent stopping is the correct fail-safe behavior.
        self._client.report_usage(
            self._token_id, cost_usd=cost_usd, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )
