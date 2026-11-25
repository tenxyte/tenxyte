"""
A deterministic, offline fake LLM for the CrewAI example (spec z_aud_2, Requirement 6.3).

No API key, no network call to any LLM provider — cycles through a fixed script of responses so
the demo's control flow (tool calls, HITL pause, budget suspension) is fully reproducible.
Implements CrewAI's own `BaseLLM` interface (not LangChain's `LLM` — CrewAI's `Agent.llm` field
requires a `crewai.llm.BaseLLM` instance or a plain model-name string, not a LangChain object).
Swap for a real LLM by setting `USE_REAL_LLM=1` and configuring your provider's API key; see
README.md.
"""

from __future__ import annotations

import itertools
from typing import Any

from crewai.llm import BaseLLM


class FakeScriptedLLM(BaseLLM):
    """Returns a fixed sequence of responses, looping at the end — no provider, no network call."""

    def __init__(self, responses: list[str], **kwargs: Any):
        super().__init__(model="fake-scripted", **kwargs)
        object.__setattr__(self, "_cycle", itertools.cycle(responses))

    def call(
        self,
        messages: str | list[dict],
        tools: list[dict] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> str:
        return next(self._cycle)

    def supports_stop_words(self) -> bool:
        return False

    def supports_multimodal(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return 8192
