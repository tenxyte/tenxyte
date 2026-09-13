"""
A deterministic, offline fake LLM for the CrewAI example (spec z_aud_2, Requirement 6.3).

No API key, no network call to any LLM provider — cycles through a fixed script of responses so
the demo's control flow (tool calls, HITL pause, budget suspension) is fully reproducible.
Swap for a real LLM by setting `USE_REAL_LLM=1` and configuring your provider's API key; see
README.md.
"""

from __future__ import annotations

import itertools
from typing import Any

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM


class FakeScriptedLLM(LLM):
    """A LangChain-compatible LLM that returns a fixed sequence of responses, looping at the end."""

    responses: list[str]
    _cycle: Any = None

    def __init__(self, responses: list[str], **kwargs: Any):
        super().__init__(responses=responses, **kwargs)
        object.__setattr__(self, "_cycle", itertools.cycle(responses))

    @property
    def _llm_type(self) -> str:
        return "fake-scripted"

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        return next(self._cycle)
