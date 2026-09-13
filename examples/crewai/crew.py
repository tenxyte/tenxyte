"""
CrewAI example for AIRS/1.0 (spec z_aud_2, Requirement 6): two agents — a Researcher and a
Finance Writer — sharing one delegated Agent Token, demonstrating in one run:

  1. Agent_Token issuance by a human (this script logs in as the demo user and issues one).
  2. Every tool call authenticated with AgentBearer via tenxyte-langchain.
  3. An HITL-gated tool ("file_expense_report") — 202 -> human confirmation -> replay.
  4. A budget suspension triggered live by reported usage.

Runs with a deterministic FakeScriptedLLM by default — no API key, fully reproducible. Set
USE_REAL_LLM=1 (and configure your provider) to run against a real model instead; see README.md.

See MT-4 in specs/z_aud_2/manual_tests.md for the walkthrough this script is meant to satisfy.
"""

from __future__ import annotations

import os
import sys
import time

import httpx
from crewai import Agent, Crew, Process, Task
from crewai.tools import tool
from fake_llm import FakeScriptedLLM

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "integrations", "langchain", "src"))
from tenxyte_langchain import (
    TenxyteAIRSClient,
    TenxyteBudgetExceededError,
    TenxyteHITLPending,
)

BASE_URL = os.environ.get("TENXYTE_BASE_URL", "http://localhost:8000/api/v1/auth")
DEMO_USER_EMAIL = "conformance-suite@example.com"
DEMO_USER_PASSWORD = "Conformance-Suite-P4ssw0rd!"
BUDGET_LIMIT_USD = float(os.environ.get("CREWAI_DEMO_BUDGET_USD", "0.05"))


def _login() -> str:
    response = httpx.post(
        f"{BASE_URL}/login/email/", json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD}, timeout=10
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _issue_agent_token(user_jwt: str) -> dict:
    response = httpx.post(
        f"{BASE_URL}/ai/tokens/",
        headers={"Authorization": f"Bearer {user_jwt}"},
        json={
            "agent_id": "crewai-demo-crew",
            "permissions": ["conformance.test"],
            "budget_limit_usd": BUDGET_LIMIT_USD,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _wait_for_human_confirmation(client: TenxyteAIRSClient, user_jwt: str, confirmation_token: str) -> None:
    """
    Poll for the human to confirm the pending action via Tenxyte's own API — this script never
    confirms it itself (No_Privilege_Amplification_Rule). In this demo, we auto-confirm after a
    short delay to keep the walkthrough non-interactive; a real deployment notifies a human
    (email, Slack, ...) and waits for real approval.
    """
    print(f"\n>>> HITL: action pending human approval. confirmation_token={confirmation_token}")
    print(">>> A human approves via: POST {BASE_URL}/ai/pending-actions/<token>/confirm/  (Bearer <human JWT>)")
    auto_confirm = os.environ.get("CREWAI_DEMO_AUTO_CONFIRM", "1") == "1"
    if not auto_confirm:
        input(">>> Press Enter once a human has confirmed the action...")
        return

    print(">>> CREWAI_DEMO_AUTO_CONFIRM=1: confirming automatically for this walkthrough.")
    time.sleep(1)
    confirm_path = client.endpoint("pending_action_confirm", confirmation_token=confirmation_token)
    resp = httpx.post(
        f"{client.base_url}{confirm_path}",
        headers={"Authorization": f"Bearer {user_jwt}"},
        json={"token": confirmation_token},
        timeout=10,
    )
    resp.raise_for_status()


def build_tools(client: TenxyteAIRSClient, user_jwt: str):
    @tool("log_research_note")
    def log_research_note(note: str) -> str:
        """Record a research finding against the agent's delegated permissions (non-HITL)."""
        client.request("GET", "/api/v1/auth/ai/_conformance_probe/")
        return f"Logged: {note}"

    @tool("file_expense_report")
    def file_expense_report(amount_usd: float, description: str) -> str:
        """File an expense report. Sensitive — requires human confirmation (HITL)."""
        try:
            client.request(
                "POST", "/api/v1/auth/ai/_hitl_probe/", json={"amount_usd": amount_usd, "description": description}
            )
        except TenxyteHITLPending as pending:
            _wait_for_human_confirmation(client, user_jwt, pending.confirmation_token)
            pending.resume()
        return f"Expense report filed: ${amount_usd:.2f} — {description}"

    @tool("report_llm_usage")
    def report_llm_usage(cost_usd: float) -> str:
        """Report this step's LLM cost against the token's budget. Raises when exceeded."""
        client.report_usage(_TOKEN_ID, cost_usd=cost_usd, prompt_tokens=100, completion_tokens=50)
        return f"Reported ${cost_usd:.4f}"

    return [log_research_note, file_expense_report, report_llm_usage]


_TOKEN_ID: int | None = None


def main() -> None:
    global _TOKEN_ID

    print(f"Logging in as the demo user at {BASE_URL} ...")
    user_jwt = _login()

    print(f"Issuing a delegated Agent Token (budget_limit_usd={BUDGET_LIMIT_USD:.2f}) ...")
    issued = _issue_agent_token(user_jwt)
    _TOKEN_ID = issued["id"]
    print(f"Agent Token id={_TOKEN_ID}, status={issued['status']}")

    client = TenxyteAIRSClient(BASE_URL, agent_token=issued["token"])
    tools = build_tools(client, user_jwt)

    use_real_llm = os.environ.get("USE_REAL_LLM") == "1"
    llm = (
        None
        if use_real_llm
        else FakeScriptedLLM(
            responses=[
                "I will research the vendor and note my findings.",
                "Filing the expense report for the vendor payment now.",
                "Reporting LLM usage for this session.",
            ]
        )
    )

    researcher = Agent(
        role="Researcher",
        goal="Investigate the vendor invoice and record findings",
        backstory="A careful research analyst who never approves spending itself.",
        tools=[t for t in tools if t.name in ("log_research_note", "report_llm_usage")],
        llm=llm,
    )

    finance_writer = Agent(
        role="Finance Writer",
        goal="File the expense report for the reviewed vendor invoice",
        backstory="Handles paperwork, but every expense report needs human sign-off (HITL).",
        tools=[t for t in tools if t.name in ("file_expense_report", "report_llm_usage")],
        llm=llm,
    )

    research_task = Task(
        description="Research the vendor invoice for 'Acme Cloud Services' and log a note.",
        expected_output="A logged research note.",
        agent=researcher,
    )
    filing_task = Task(
        description="File an expense report of $42.50 for 'Acme Cloud Services — September invoice'.",
        expected_output="Confirmation the expense report was filed.",
        agent=finance_writer,
    )

    crew = Crew(agents=[researcher, finance_writer], tasks=[research_task, filing_task], process=Process.sequential)
    result = crew.kickoff()
    print("\n=== Crew result ===")
    print(result)

    print("\n=== Demonstrating budget suspension ===")
    try:
        while True:
            client.report_usage(_TOKEN_ID, cost_usd=BUDGET_LIMIT_USD / 3, prompt_tokens=100, completion_tokens=50)
            print("Usage reported; token still active.")
    except TenxyteBudgetExceededError as exc:
        print(f"Token suspended as expected: {exc}")


if __name__ == "__main__":
    main()
