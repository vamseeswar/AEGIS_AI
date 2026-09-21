"""AEGIS AI — LangGraph Multi-Agent State Machine & Supervisor Runtime
Constructs the compiled execution DAG with conditional supervisor routing across 8 specialized agents.
"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.agents.specialized import (
    data_agent_node,
    doc_intel_agent_node,
    ml_agent_node,
    rag_agent_node,
    report_agent_node,
    sql_agent_node,
    validation_agent_node,
)
from backend.agents.state import SupervisorState


async def supervisor_node(state: SupervisorState) -> dict[str, Any]:
    """Supervisor Agent: plans execution graph, selects next agent, and synthesizes final output."""
    plan = list(state.get("plan", []))
    descriptions = list(state.get("plan_descriptions", []))

    # 1. Initialize plan if not yet created
    if not plan:
        task_lower = state["task"].lower()
        lead_agent = state.get("lead_agent", "supervisor")

        if lead_agent in (
            "rag_agent",
            "sql_agent",
            "data_agent",
            "ml_agent",
            "doc_intel_agent",
            "validation_agent",
            "report_agent",
        ):
            plan.append(lead_agent)
            descriptions.append(f"Execute primary lead agent task via {lead_agent}.")

        # Auto-detect domains from query
        if any(w in task_lower for w in ["search", "document", "knowledge", "sop", "policy", "rag"]):
            if "rag_agent" not in plan:
                plan.append("rag_agent")
                descriptions.append("Retrieve grounded context and citations from tenant knowledge base.")

        if any(w in task_lower for w in ["sql", "database", "query", "table", "schema", "events"]):
            if "sql_agent" not in plan:
                plan.append("sql_agent")
                descriptions.append("Formulate read-only SQL query with AST safety verification.")

        if any(w in task_lower for w in ["metric", "analytic", "statistic", "throughput", "distribution", "data"]):
            if "data_agent" not in plan:
                plan.append("data_agent")
                descriptions.append("Perform statistical distribution analysis and chart formatting.")

        if any(w in task_lower for w in ["forecast", "predict", "machine learning", "ml", "anomaly", "growth"]):
            if "ml_agent" not in plan:
                plan.append("ml_agent")
                descriptions.append("Execute ML time-series forecasting and anomaly risk scoring.")

        if any(w in task_lower for w in ["contract", "extract", "clause", "sla", "entity"]):
            if "doc_intel_agent" not in plan:
                plan.append("doc_intel_agent")
                descriptions.append("Extract named entities, SLA metrics, and compliance commitments.")

        # Default fallback workflow if no specific keywords triggered
        if not plan:
            plan = ["rag_agent", "data_agent", "validation_agent", "report_agent"]
            descriptions = [
                "Retrieve grounded tenant knowledge.",
                "Calculate operational telemetry metrics.",
                "Validate facts and check hallucination markers.",
                "Synthesize executive operations briefing.",
            ]
        else:
            # Always conclude with validation and report if not already included
            if "validation_agent" not in plan:
                plan.append("validation_agent")
                descriptions.append("Validate factual grounding against retrieved sources.")
            if "report_agent" not in plan:
                plan.append("report_agent")
                descriptions.append("Compile executive briefing.")

    # 2. Determine next agent
    current_index = state.get("current_step_index", 0)

    if current_index < len(plan):
        next_agent = plan[current_index]
        return {
            "plan": plan,
            "plan_descriptions": descriptions,
            "next_agent": next_agent,
            "status": "RUNNING",
        }

    # 3. All steps completed -> synthesize final response
    final_text = state.get("final_synthesis")
    if not final_text:
        outputs = state.get("agent_outputs", {})
        parts = [f"**AEGIS Autonomous Workflow Completed**: '{state['task']}'\n"]
        for agent_name, out in outputs.items():
            parts.append(f"### Output from {agent_name.replace('_', ' ').title()}\n{out}\n")
        final_text = "\n".join(parts)

    return {
        "plan": plan,
        "plan_descriptions": descriptions,
        "next_agent": "FINISH",
        "status": "COMPLETED",
        "final_synthesis": final_text,
    }


def route_supervisor(state: SupervisorState) -> str:
    """Conditional router determining the next branch in the LangGraph DAG."""
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "FINISH" or state.get("status") == "COMPLETED":
        return END
    return next_agent


def build_supervisor_graph():
    """Builds and compiles the multi-agent LangGraph execution graph."""
    workflow = StateGraph(SupervisorState)

    # Add agent nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("rag_agent", rag_agent_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("data_agent", data_agent_node)
    workflow.add_node("ml_agent", ml_agent_node)
    workflow.add_node("doc_intel_agent", doc_intel_agent_node)
    workflow.add_node("validation_agent", validation_agent_node)
    workflow.add_node("report_agent", report_agent_node)

    # Set supervisor as entry point
    workflow.add_edge(START, "supervisor")

    # Conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "rag_agent": "rag_agent",
            "sql_agent": "sql_agent",
            "data_agent": "data_agent",
            "ml_agent": "ml_agent",
            "doc_intel_agent": "doc_intel_agent",
            "validation_agent": "validation_agent",
            "report_agent": "report_agent",
            END: END,
        },
    )

    # Route every specialized agent back to supervisor
    for agent in [
        "rag_agent",
        "sql_agent",
        "data_agent",
        "ml_agent",
        "doc_intel_agent",
        "validation_agent",
        "report_agent",
    ]:
        workflow.add_edge(agent, "supervisor")

    return workflow.compile()


# Compiled singleton graph
supervisor_graph = build_supervisor_graph()
