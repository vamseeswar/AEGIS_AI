"""AEGIS AI — Model Context Protocol (MCP) Tool Specifications
Defines MCP-compliant schemas, tool metadata, call requests, and structured result payloads.
"""

from typing import Any

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    """Model Context Protocol Tool Schema."""

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Detailed description of tool functionality")
    inputSchema: dict[str, Any] = Field(..., description="JSON Schema defining input parameters")
    category: str = Field(default="GENERAL", description="Categorization: RAG, DATABASE, ANALYTICS, ML, REPORTING, WEB, SYSTEM")
    required_permission: str = Field(default="tools.execute", description="Required RBAC permission string")
    requires_approval: bool = Field(default=False, description="Whether human approval is mandated before execution")
    is_sensitive: bool = Field(default=False, description="Whether tool writes data or causes external side effects")
    rate_limit_per_minute: int = Field(default=60, description="Max allowed invocations per minute per tenant")


class MCPToolCallRequest(BaseModel):
    """Payload for executing a tool."""

    arguments: dict[str, Any] = Field(default_factory=dict, description="Input parameters matching tool's inputSchema")
    agent_run_id: str | None = Field(default=None, description="Optional associated Agent Run ID")


class MCPToolResult(BaseModel):
    """Execution output from an MCP tool."""

    tool_name: str
    status: str = Field(..., description="Execution status: SUCCESS, FAILED, BLOCKED, PENDING_APPROVAL")
    output: Any | None = None
    error: str | None = None
    execution_time_ms: float = 0.0
    requires_approval: bool = False
    audit_log_id: str | None = None
