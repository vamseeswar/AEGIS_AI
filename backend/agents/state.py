"""AEGIS AI — Multi-Agent State Definition
Typed state shared across all nodes in the LangGraph Supervisor state machine.
"""

from typing import Any, TypedDict


class SupervisorState(TypedDict):
    """Shared state container passed between LangGraph nodes during multi-agent execution."""

    task: str
    organization_id: str
    user_id: str
    agent_run_id: str
    lead_agent: str
    plan: list[str]
    plan_descriptions: list[str]
    next_agent: str
    current_step_index: int
    completed_steps: list[dict[str, Any]]
    agent_outputs: dict[str, Any]
    final_synthesis: str
    status: str
    errors: list[str]
