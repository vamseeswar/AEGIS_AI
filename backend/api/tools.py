"""AEGIS AI — Model Context Protocol (MCP) Tools API Router
Provides tool discovery, schema inspection, and permission-gated invocation endpoints.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.mcp.protocol import MCPTool, MCPToolCallRequest, MCPToolResult
from backend.models.governance import AuditLog
from backend.security.dependencies import CurrentUser, get_current_user
from backend.tools.base import ToolExecutionContext
from backend.tools.registry import global_tool_registry

tools_router = APIRouter(prefix="/tools", tags=["MCP Tools"])


@tools_router.get(
    "",
    response_model=list[MCPTool],
    summary="List all registered MCP tools with JSON schemas",
)
async def list_tools(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[MCPTool]:
    """Returns catalog of all registered tools with MCP-compliant input schemas."""
    return global_tool_registry.list_tools()


@tools_router.get(
    "/{name}",
    response_model=MCPTool,
    summary="Get MCP specification for a specific tool",
)
async def get_tool(
    name: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> MCPTool:
    """Returns MCP tool specification including inputSchema and required permissions."""
    tool = global_tool_registry.get_tool(name)
    return tool.to_mcp_tool()


@tools_router.post(
    "/{name}/execute",
    response_model=MCPToolResult,
    status_code=status.HTTP_200_OK,
    summary="Execute an MCP tool with caller permissions and audit logging",
)
async def execute_tool(
    name: str,
    call_request: MCPToolCallRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MCPToolResult:
    """Executes a tool after validating user permissions, creating immutable audit logs."""
    context = ToolExecutionContext(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        user_permissions=current_user.permissions,
        user_role=current_user.role,
        db=db,
        agent_run_id=call_request.agent_run_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return await global_tool_registry.invoke(
        name=name,
        arguments=call_request.arguments,
        context=context,
    )


@tools_router.get(
    "/audit/logs",
    summary="List recent tool execution audit records for the tenant",
)
async def list_tool_audit_logs(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns recent tool execution audit trail for the tenant."""
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.organization_id == current_user.organization_id,
            AuditLog.action == "TOOL_EXECUTE",
        )
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [
        {
            "id": log.id,
            "tool_name": log.resource_id,
            "status": log.status,
            "user_id": log.user_id,
            "details": log.details_json,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
