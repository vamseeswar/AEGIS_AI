"""AEGIS AI — Agent and Multi-Agent Execution Schemas
Pydantic v2 schemas for agent fleet catalog, execution runs, step traces, and tool call audits.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentMetadataResponse(BaseModel):
    id: str
    name: str
    role: str
    icon: str
    description: str
    capabilities: list[str]
    default_tools: list[str]


class AgentRunCreateRequest(BaseModel):
    prompt: str = Field(min_length=3, description="Operational task prompt or directive")
    lead_agent: str = Field(default="supervisor", description="Lead agent to handle the task")
    workflow_name: str = Field(default="autonomous_supervisor", description="Workflow template name")
    conversation_id: str | None = None


class AgentStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    step_number: int
    agent_name: str
    input_state: dict[str, Any] | None = None
    output_state: dict[str, Any] | None = None
    status: str
    duration_ms: float | None = None


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tool_name: str
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    is_sensitive: bool = False
    status: str
    execution_time_ms: float | None = None


class AgentRunListItem(BaseModel):
    id: str
    workflow_name: str
    request_prompt: str
    status: str
    step_count: int = 0
    total_duration_ms: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AgentRunListResponse(BaseModel):
    runs: list[AgentRunListItem]
    total: int


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    organization_id: str
    conversation_id: str | None = None
    workflow_name: str
    request_prompt: str
    status: str
    plan_json: dict[str, Any] | None = None
    execution_summary: str | None = None
    error_details: str | None = None
    total_duration_ms: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    steps: list[AgentStepResponse] = []
    tool_calls: list[ToolCallResponse] = []
