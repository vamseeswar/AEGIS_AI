"""AEGIS AI — Agent Execution Service
Orchestrates LangGraph multi-agent execution, persists execution steps, and manages run lifecycles.
"""

import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.agents.graph import supervisor_graph
from backend.agents.state import SupervisorState
from backend.core.errors import ResourceNotFoundError, TenantIsolationError
from backend.models.agent import AgentRun, AgentStep, ToolCall


class AgentService:
    @staticmethod
    async def create_and_execute_run(
        db: AsyncSession,
        user_id: str,
        organization_id: str,
        prompt: str,
        lead_agent: str = "supervisor",
        workflow_name: str = "autonomous_supervisor",
        conversation_id: str | None = None,
    ) -> AgentRun:
        """Initializes an AgentRun, executes the LangGraph workflow, and persists step-by-step traces."""
        start_time = time.time()

        # 1. Create AgentRun record in database
        run = AgentRun(
            user_id=user_id,
            organization_id=organization_id,
            conversation_id=conversation_id,
            workflow_name=workflow_name,
            request_prompt=prompt,
            status="RUNNING",
            started_at=datetime.now(UTC),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        # 2. Build initial SupervisorState
        initial_state: SupervisorState = {
            "task": prompt,
            "organization_id": organization_id,
            "user_id": user_id,
            "agent_run_id": run.id,
            "lead_agent": lead_agent,
            "plan": [],
            "plan_descriptions": [],
            "next_agent": "supervisor",
            "current_step_index": 0,
            "completed_steps": [],
            "agent_outputs": {},
            "final_synthesis": "",
            "status": "RUNNING",
            "errors": [],
        }

        # 3. Execute LangGraph multi-agent workflow
        try:
            result = await supervisor_graph.ainvoke(initial_state, config={"recursion_limit": 50})

            # Persist completed steps
            completed_steps: list[dict[str, Any]] = result.get("completed_steps", [])
            for step_data in completed_steps:
                agent_name = step_data.get("agent_name", "agent")
                agent_output = result.get("agent_outputs", {}).get(agent_name)

                step_record = AgentStep(
                    organization_id=organization_id,
                    agent_run_id=run.id,
                    step_number=step_data.get("step_number", 1),
                    agent_name=agent_name,
                    input_state={"task": prompt, "lead_agent": lead_agent},
                    output_state=agent_output if isinstance(agent_output, dict) else {"summary": step_data.get("summary")},
                    status="COMPLETED",
                    duration_ms=step_data.get("duration_ms", 100.0),
                )
                db.add(step_record)

                # Record synthetic tool call audit
                tool_record = ToolCall(
                    organization_id=organization_id,
                    agent_run_id=run.id,
                    tool_name=f"{agent_name}_execute",
                    tool_input={"task": prompt},
                    tool_output=agent_output if isinstance(agent_output, dict) else {"summary": step_data.get("summary")},
                    is_sensitive=False,
                    status="SUCCESS",
                    execution_time_ms=step_data.get("duration_ms", 100.0),
                )
                db.add(tool_record)

            total_duration = round((time.time() - start_time) * 1000, 2)
            run.status = "COMPLETED"
            run.plan_json = {
                "plan": result.get("plan", []),
                "descriptions": result.get("plan_descriptions", []),
            }
            run.execution_summary = result.get("final_synthesis")
            run.total_duration_ms = total_duration
            run.completed_at = datetime.now(UTC)

        except Exception as exc:
            total_duration = round((time.time() - start_time) * 1000, 2)
            run.status = "FAILED"
            run.error_details = str(exc)
            run.total_duration_ms = total_duration
            run.completed_at = datetime.now(UTC)

        await db.commit()
        return await AgentService.get_agent_run(db, run.id, organization_id)

    @staticmethod
    async def list_agent_runs(
        db: AsyncSession,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Lists all agent runs for the caller's tenant."""
        count_stmt = (
            select(func.count(AgentRun.id))
            .where(AgentRun.organization_id == organization_id)
        )
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(
                AgentRun,
                func.count(AgentStep.id).label("step_count"),
            )
            .outerjoin(AgentStep, AgentStep.agent_run_id == AgentRun.id)
            .where(AgentRun.organization_id == organization_id)
            .group_by(AgentRun.id)
            .order_by(desc(AgentRun.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        rows = result.all()

        runs = []
        for run, step_count in rows:
            runs.append(
                {
                    "id": run.id,
                    "workflow_name": run.workflow_name,
                    "request_prompt": run.request_prompt,
                    "status": run.status,
                    "step_count": step_count,
                    "total_duration_ms": run.total_duration_ms,
                    "started_at": run.started_at,
                    "completed_at": run.completed_at,
                    "created_at": run.created_at,
                }
            )

        return runs, total

    @staticmethod
    async def get_agent_run(
        db: AsyncSession,
        run_id: str,
        organization_id: str,
    ) -> AgentRun:
        """Retrieves a single agent run trace with steps, tool calls, and approvals."""
        stmt = (
            select(AgentRun)
            .where(AgentRun.id == run_id)
            .options(
                selectinload(AgentRun.steps),
                selectinload(AgentRun.tool_calls),
                selectinload(AgentRun.approvals),
            )
        )
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            raise ResourceNotFoundError("AgentRun", run_id)

        if run.organization_id != organization_id:
            raise TenantIsolationError("Access to cross-tenant agent run denied.")

        return run

    @staticmethod
    async def cancel_agent_run(
        db: AsyncSession,
        run_id: str,
        organization_id: str,
    ) -> AgentRun:
        """Cancels an in-flight or pending agent run."""
        run = await AgentService.get_agent_run(db, run_id, organization_id)

        if run.status in ("RUNNING", "PENDING"):
            run.status = "FAILED"
            run.error_details = "Agent run cancelled by user."
            run.completed_at = datetime.now(UTC)
            await db.commit()
            return await AgentService.get_agent_run(db, run_id, organization_id)

        return run
