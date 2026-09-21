"""AEGIS AI — Agent Runtime & Multi-Agent Execution Endpoints
Provides fleet discovery, task dispatching, trace inspection, and run cancellation.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.registry import list_available_agents
from backend.db.session import get_db
from backend.schemas.agent import (
    AgentMetadataResponse,
    AgentRunCreateRequest,
    AgentRunListItem,
    AgentRunListResponse,
    AgentRunResponse,
    AgentStepResponse,
    ToolCallResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user, require_permission
from backend.services.agent_service import AgentService

agents_router = APIRouter(prefix="/agents", tags=["Autonomous Agents"])


@agents_router.get(
    "",
    response_model=list[AgentMetadataResponse],
    summary="List all available specialized agents in the fleet",
)
async def get_agents(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AgentMetadataResponse]:
    agents_data = list_available_agents()
    return [AgentMetadataResponse(**a) for a in agents_data]


@agents_router.post(
    "/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch a new multi-agent workflow run",
    dependencies=[Depends(require_permission("agents.execute"))],
)
async def create_agent_run(
    payload: AgentRunCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    run = await AgentService.create_and_execute_run(
        db=db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        prompt=payload.prompt,
        lead_agent=payload.lead_agent,
        workflow_name=payload.workflow_name,
        conversation_id=payload.conversation_id,
    )

    steps = [AgentStepResponse.model_validate(s) for s in run.steps]
    tools = [ToolCallResponse.model_validate(t) for t in run.tool_calls]

    return AgentRunResponse(
        id=run.id,
        user_id=run.user_id,
        organization_id=run.organization_id,
        conversation_id=run.conversation_id,
        workflow_name=run.workflow_name,
        request_prompt=run.request_prompt,
        status=run.status,
        plan_json=run.plan_json,
        execution_summary=run.execution_summary,
        error_details=run.error_details,
        total_duration_ms=run.total_duration_ms,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        steps=steps,
        tool_calls=tools,
    )


@agents_router.get(
    "/runs",
    response_model=AgentRunListResponse,
    summary="List agent runs for the current tenant",
    dependencies=[Depends(require_permission("agents.execute"))],
)
async def list_agent_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunListResponse:
    runs, total = await AgentService.list_agent_runs(
        db=db,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )
    return AgentRunListResponse(
        runs=[AgentRunListItem(**r) for r in runs],
        total=total,
    )


@agents_router.get(
    "/runs/{run_id}",
    response_model=AgentRunResponse,
    summary="Get detailed execution trace and step graph for an agent run",
    dependencies=[Depends(require_permission("agents.execute"))],
)
async def get_agent_run(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    run = await AgentService.get_agent_run(
        db=db,
        run_id=run_id,
        organization_id=current_user.organization_id,
    )

    steps = [AgentStepResponse.model_validate(s) for s in run.steps]
    tools = [ToolCallResponse.model_validate(t) for t in run.tool_calls]

    return AgentRunResponse(
        id=run.id,
        user_id=run.user_id,
        organization_id=run.organization_id,
        conversation_id=run.conversation_id,
        workflow_name=run.workflow_name,
        request_prompt=run.request_prompt,
        status=run.status,
        plan_json=run.plan_json,
        execution_summary=run.execution_summary,
        error_details=run.error_details,
        total_duration_ms=run.total_duration_ms,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        steps=steps,
        tool_calls=tools,
    )


@agents_router.post(
    "/runs/{run_id}/cancel",
    response_model=AgentRunResponse,
    summary="Cancel an active agent run",
    dependencies=[Depends(require_permission("agents.execute"))],
)
async def cancel_agent_run(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    run = await AgentService.cancel_agent_run(
        db=db,
        run_id=run_id,
        organization_id=current_user.organization_id,
    )
    steps = [AgentStepResponse.model_validate(s) for s in run.steps]
    tools = [ToolCallResponse.model_validate(t) for t in run.tool_calls]

    return AgentRunResponse(
        id=run.id,
        user_id=run.user_id,
        organization_id=run.organization_id,
        conversation_id=run.conversation_id,
        workflow_name=run.workflow_name,
        request_prompt=run.request_prompt,
        status=run.status,
        plan_json=run.plan_json,
        execution_summary=run.execution_summary,
        error_details=run.error_details,
        total_duration_ms=run.total_duration_ms,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        steps=steps,
        tool_calls=tools,
    )
