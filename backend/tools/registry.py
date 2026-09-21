"""AEGIS AI — Central Tool Registry & MCP Permission Engine
Orchestrates tool discovery, strict RBAC permission gating, execution auditing, and HITL hooks.
"""

import logging
import time
from typing import Any

from pydantic import ValidationError

from backend.core.errors import PermissionDeniedError, ResourceNotFoundError
from backend.mcp.protocol import MCPTool, MCPToolResult
from backend.models.agent import ToolCall
from backend.models.governance import AuditLog
from backend.tools.analyze_csv import AnalyzeCSVTool
from backend.tools.base import BaseTool, ToolExecutionContext
from backend.tools.detect_anomalies import DetectAnomaliesTool
from backend.tools.generate_report import GenerateReportTool
from backend.tools.get_system_status import GetSystemStatusTool
from backend.tools.query_database import QueryDatabaseTool
from backend.tools.run_forecast import RunForecastTool
from backend.tools.search_documents import SearchDocumentsTool
from backend.tools.search_web import SearchWebTool

logger = logging.getLogger("aegis.tools")


class ToolRegistry:
    """Central registry and execution manager for MCP-compliant tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Registers all platform standard tools."""
        tools = [
            SearchDocumentsTool(),
            QueryDatabaseTool(),
            AnalyzeCSVTool(),
            RunForecastTool(),
            DetectAnomaliesTool(),
            GenerateReportTool(),
            SearchWebTool(),
            GetSystemStatusTool(),
        ]
        for t in tools:
            self.register(t)

    def register(self, tool: BaseTool) -> None:
        """Registers a tool into the system catalog."""
        self._tools[tool.name] = tool
        logger.info(f"Registered MCP tool: {tool.name} (category: {tool.category})")

    def list_tools(self) -> list[MCPTool]:
        """Returns all registered tools in standard MCP specification format."""
        return [tool.to_mcp_tool() for tool in self._tools.values()]

    def get_tool(self, name: str) -> BaseTool:
        """Retrieves a specific tool instance by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ResourceNotFoundError("Tool", name)
        return tool

    async def invoke(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> MCPToolResult:
        """Invokes a tool with strict RBAC validation, execution timing, and audit logging."""
        tool = self.get_tool(name)
        start_time = time.perf_counter()

        # 1. Strict RBAC Permission Check
        # Caller must possess both the global 'tools.execute' permission and the tool's required_permission
        has_general_perm = "tools.execute" in context.user_permissions
        has_specific_perm = (
            tool.required_permission in context.user_permissions
            or "system.admin" in context.user_permissions
        )

        if not (has_general_perm and has_specific_perm):
            # Record BLOCKED in audit log
            blocked_audit = AuditLog(
                organization_id=context.organization_id,
                user_id=context.user_id,
                action="TOOL_EXECUTE",
                resource_type="tool",
                resource_id=name,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                status="BLOCKED",
                details_json={
                    "arguments": arguments,
                    "reason": f"Missing required permission: '{tool.required_permission}'",
                    "user_role": context.user_role,
                },
            )
            context.db.add(blocked_audit)
            await context.db.commit()

            raise PermissionDeniedError(
                f"Permission denied: Invoking tool '{name}' requires '{tool.required_permission}' and 'tools.execute'."
            )

        # 2. Human-in-the-Loop Approval Check
        if tool.requires_approval:
            approval_audit = AuditLog(
                organization_id=context.organization_id,
                user_id=context.user_id,
                action="TOOL_EXECUTE",
                resource_type="tool",
                resource_id=name,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                status="PENDING_APPROVAL",
                details_json={"arguments": arguments},
            )
            context.db.add(approval_audit)
            await context.db.commit()

            return MCPToolResult(
                tool_name=name,
                status="PENDING_APPROVAL",
                requires_approval=True,
                audit_log_id=approval_audit.id,
            )

        # 3. Argument Validation
        try:
            validated_args = tool.args_schema(**arguments)
            clean_args = validated_args.model_dump()
        except ValidationError as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            fail_audit = AuditLog(
                organization_id=context.organization_id,
                user_id=context.user_id,
                action="TOOL_EXECUTE",
                resource_type="tool",
                resource_id=name,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                status="FAILED",
                details_json={
                    "arguments": arguments,
                    "error": str(e),
                    "execution_time_ms": duration_ms,
                },
            )
            context.db.add(fail_audit)
            await context.db.commit()

            return MCPToolResult(
                tool_name=name,
                status="FAILED",
                error=f"Argument validation error: {e}",
                execution_time_ms=duration_ms,
                audit_log_id=fail_audit.id,
            )

        # 4. Tool Execution
        try:
            output = await tool.execute(arguments=clean_args, context=context)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 5. Persist Immutable Audit Log
            audit_log = AuditLog(
                organization_id=context.organization_id,
                user_id=context.user_id,
                action="TOOL_EXECUTE",
                resource_type="tool",
                resource_id=name,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                status="SUCCESS",
                details_json={
                    "arguments": clean_args,
                    "execution_time_ms": duration_ms,
                },
            )
            context.db.add(audit_log)

            # If inside an agent workflow run, also persist a ToolCall record
            tool_call_rec = ToolCall(
                organization_id=context.organization_id,
                agent_run_id=context.agent_run_id,
                tool_name=name,
                tool_input=clean_args,
                tool_output=output if isinstance(output, dict) else {"result": output},
                is_sensitive=tool.is_sensitive,
                status="SUCCESS",
                execution_time_ms=duration_ms,
            )
            context.db.add(tool_call_rec)

            await context.db.commit()

            return MCPToolResult(
                tool_name=name,
                status="SUCCESS",
                output=output,
                execution_time_ms=duration_ms,
                audit_log_id=audit_log.id,
            )

        except Exception as e:
            await context.db.rollback()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)

            error_audit = AuditLog(
                organization_id=context.organization_id,
                user_id=context.user_id,
                action="TOOL_EXECUTE",
                resource_type="tool",
                resource_id=name,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                status="FAILED",
                details_json={
                    "arguments": clean_args,
                    "error": str(e),
                    "execution_time_ms": duration_ms,
                },
            )
            context.db.add(error_audit)

            if context.agent_run_id:
                tool_call_fail = ToolCall(
                    organization_id=context.organization_id,
                    agent_run_id=context.agent_run_id,
                    tool_name=name,
                    tool_input=clean_args,
                    is_sensitive=tool.is_sensitive,
                    status="FAILED",
                    error_message=str(e),
                    execution_time_ms=duration_ms,
                )
                context.db.add(tool_call_fail)

            await context.db.commit()

            return MCPToolResult(
                tool_name=name,
                status="FAILED",
                error=str(e),
                execution_time_ms=duration_ms,
                audit_log_id=error_audit.id,
            )


# Global Singleton Registry
global_tool_registry = ToolRegistry()
