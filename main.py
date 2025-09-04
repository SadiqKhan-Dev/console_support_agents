import asyncio
from typing import Optional, Literal

from pydantic import BaseModel, Field

# Core Agents SDK imports
from agents import (
    Agent,
    Runner,
    function_tool,
    OutputGuardrail,
    GuardrailFunctionOutput,
)
from agents.stream_events import RunItemStreamEvent, RawResponsesStreamEvent
from agents.run_context import RunContextWrapper  # to access shared context inside tools
import os
from dotenv import load_dotenv

# ---------------------------
# Load API Key
# ---------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("⚠ GEMINI_API_KEY is missing in .env")





# ---------------------------
# Shared Pydantic context
# ---------------------------
class SupportContext(BaseModel):
    name: Optional[str] = Field(default=None, description="User name, if known")
    is_premium_user: bool = Field(default=False, description="Premium status")
    issue_type: Optional[Literal["billing", "technical", "general"]] = Field(
        default=None, description="Latest classified issue type for current message"
    )
    account_id: Optional[str] = Field(
        default=None, description="User account identifier (if provided)"
    )


# ---------------------------
# Utility: small helper to coerce bool-ish strings from CLI
# ---------------------------
def to_bool(s: str) -> bool:
    return s.strip().lower() in {"1", "y", "yes", "true", "t"}


# ---------------------------
# TOOLS
# ---------------------------

# --- Triage helper: allow the triage agent to set/overwrite issue_type in shared context
@function_tool(
    description_override=(
        "Set the current issue_type in shared context. "
        "Call this when you infer the user's query type. "
        'Accepts one of: "billing", "technical", "general".'
    ),
    strict_mode=True,
)
def set_issue_type(ctx: RunContextWrapper[SupportContext], issue_type: Literal["billing", "technical", "general"]) -> str:
    """Sets the context.issue_type to guide handoff and tool gating."""
    ctx.context.issue_type = issue_type
    return f"issue_type set to '{issue_type}'"


# --- General helper: optionally set name or account id
@function_tool(
    description_override="Persist user name and/or account_id to shared context if provided.",
    strict_mode=True,
)
def update_user_profile(
    ctx: RunContextWrapper[SupportContext],
    name: Optional[str] = None,
    account_id: Optional[str] = None,
) -> str:
    """Updates shared context with name and/or account_id if present."""
    changed = []
    if name:
        ctx.context.name = name
        changed.append(f"name='{name}'")
    if account_id:
        ctx.context.account_id = account_id
        changed.append(f"account_id='{account_id}'")
    if not changed:
        return "No changes made."
    return "Updated: " + ", ".join(changed)


# --- Billing tools
@function_tool(
    description_override=(
        "Process a refund for a given order_id and amount (USD). "
        "Only permitted for premium users; otherwise the tool is disabled."
    ),
    # Dynamically enable this tool only for premium users
    is_enabled=lambda ctx, agent: bool(getattr(ctx.context, "is_premium_user", False)),
    strict_mode=True,
)
def refund(order_id: str, amount: float) -> str:
    """Issue a refund. Returns a confirmation string."""
    # In a real system you’d call your billing API here.
    return f"Refund issued for order {order_id}, amount ${amount:.2f}."


@function_tool(
    description_override="Provide the status of the latest invoice.",
)
def invoice_status(account_id: Optional[str] = None) -> str:
    """Returns mock invoice status for the account."""
    acct = account_id or "UNKNOWN"
    return f"Invoice status for {acct}: PAID on-time (mock)."


# --- Technical tools
@function_tool(
    description_override=(
        "Restart a backend service by name. "
        'Enabled only if context.issue_type == "technical".'
    ),
    is_enabled=lambda ctx, agent: getattr(ctx.context, "issue_type", None) == "technical",
    strict_mode=True,
)
def restart_service(service_name: str) -> str:
    """Restarts a service and returns a status message."""
    # In production: trigger infra orchestration here.
    return f"Service '{service_name}' restarted successfully."


@function_tool(description_override="Check the health of a backend service.")
def check_service_status(service_name: str) -> str:
    """Returns mock health status for a service."""
    return f"Service '{service_name}' status: HEALTHY (mock)."


# --- General/FAQ tools
@function_tool(description_override="Answer a frequently asked question from the built-in KB (mock).")
def faq(query: str) -> str:
    """Returns a mock answer from a KB."""
    return f"[KB] Answer to '{query}': This is a placeholder knowledge base response."


# ---------------------------
# GUARDRAIL (optional bonus)
# Block apology words in final output (e.g., 'sorry', 'apologize')
# ---------------------------

async def no_apologies_guardrail(ctx: RunContextWrapper[SupportContext], agent: Agent, final_text: str) -> GuardrailFunctionOutput:
    txt = (final_text or "").lower()
    banned = ("sorry", "apologize", "apologies", "apologise")
    triggered = any(word in txt for word in banned)
    return GuardrailFunctionOutput(output_info=None, tripwire_triggered=triggered)

no_apologies_output_guardrail = OutputGuardrail(guardrail_function=no_apologies_guardrail)


# ---------------------------
# AGENTS
# ---------------------------

# Billing specialist
billing_agent = Agent(
    name="Billing Specialist",
    handoff_description="Handles billing, invoices, refunds, and payments.",
    instructions=(
        "You are the Billing Specialist. "
        "Use billing tools for invoicing and refunds when appropriate. "
        "If the user is not premium, the refund tool will be disabled; in that case, explain upgrade paths "
        "without using apology words."
    ),
    tools=[refund, invoice_status],
    output_guardrails=[no_apologies_output_guardrail],
)

# Technical specialist
technical_agent = Agent(
    name="Technical Specialist",
    handoff_description="Handles technical issues, restarts, and service health.",
    instructions=(
        "You are the Technical Specialist. "
        "Use technical tools. Restart is gated by issue_type=='technical'. "
        "Avoid apology words."
    ),
    tools=[restart_service, check_service_status],
    output_guardrails=[no_apologies_output_guardrail],
)

# General support specialist
general_agent = Agent(
    name="General Support",
    handoff_description="Handles general questions and FAQs.",
    instructions=(
        "You are General Support. Prefer the FAQ tool for common queries. "
        "Avoid apology words."
    ),
    tools=[faq],
    output_guardrails=[no_apologies_output_guardrail],
)

# TRIAGE agent — decides handoff and sets context.issue_type via tool
triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "You are the entrypoint. Infer the user's intent (billing vs technical vs general).\n"
        "- First, call set_issue_type('billing'|'technical'|'general').\n"
        "- If the user states or implies their name or account id, call update_user_profile.\n"
        "- Then HANDOFF to the correct specialist using the available handoffs.\n"
        "Never use apology words."
    ),
    tools=[set_issue_type, update_user_profile],
    handoffs=[billing_agent, technical_agent, general_agent],
    output_guardrails=[no_apologies_output_guardrail],
)


# ---------------------------
# Streaming Printer
# ---------------------------

def print_stream_event(evt):
    """Pretty-print streaming events during a run."""
    if isinstance(evt, RunItemStreamEvent):
        if evt.name == "handoff_requested":
            to_agent = getattr(evt.item, "handoff_to", None)
            if to_agent:
                print(f"\n[handoff → {to_agent.name}]")
        elif evt.name == "handoff_occured":
            agent_now = getattr(evt.item, "message", None)
            if agent_now:
                print(f"[active agent] {agent_now.get('agent', {}).get('name', '—')}")
        elif evt.name == "tool_called":
            tool_name = getattr(evt.item, "tool_name", "tool")
            print(f"[tool call] {tool_name}")
        elif evt.name == "tool_output":
            output = getattr(evt.item, "output", "")
            print(f"[tool output] {output}")
        elif evt.name == "message_output_created":
            content = getattr(evt.item, "content", "")
            if content:
                print(f"\n{content}\n")
    elif isinstance(evt, RawResponsesStreamEvent):
        # Raw token stream from LLMs (optional to print; can be noisy)
        pass


# ---------------------------
# CLI app
# ---------------------------

WELCOME = """\
========================================================
 Console Support Agent System  —  OpenAI Agents SDK
 - Triage + Billing + Technical + General
 - Tools w/ dynamic is_enabled
 - Context sharing (Pydantic)
 - Agent-to-agent handoffs
 - Streaming event display
 - Output guardrail (blocks 'sorry'/'apologize')
========================================================
Type 'exit' to quit.
"""

async def run_console():
    print(WELCOME)

    # Gather initial context from CLI
    name = input("Enter your name (or leave blank): ").strip() or None
    is_premium = to_bool(input("Are you a premium user? [y/N]: ") or "n")
    account_id = input("Account ID (optional): ").strip() or None

    context = SupportContext(name=name, is_premium_user=is_premium, account_id=account_id)

    print("\nContext saved:", context.model_dump())
    print("\nAsk your question(s). Examples:")
    print(" - I want a refund for order 123, amount 49.99")
    print(" - Restart the payments service")
    print(" - What’s your delivery policy?\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        # Stream the whole orchestration starting at triage
        async for event in Runner.run_streamed(triage_agent, input=user_input, context=context):
            print_stream_event(event)

        # Note: context is mutable; triage tools may have updated it
        # (e.g., issue_type). Show the latest snapshot after each turn:
        print(f"[context] {context.model_dump()}\n")


if __name__ == "__main__":
    asyncio.run(run_console())
