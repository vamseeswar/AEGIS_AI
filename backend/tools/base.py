"""AEGIS AI — Base Tool Interface and Execution Context
Defines the foundation for all MCP-compatible operational tools.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.mcp.protocol import MCPTool


class ToolExecutionContext:
    """Contextual metadata passed to a tool during invocation."""

    def __init__(
        self,
        user_id: str,
        organization_id: str,
        user_permissions: set[str],
        user_role: str,
        db: AsyncSession,
        agent_run_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.user_permissions = user_permissions
        self.user_role = user_role
        self.db = db
        self.agent_run_id = agent_run_id
        self.ip_address = ip_address
        self.user_agent = user_agent


class BaseTool(ABC):
    """Abstract Base Class for all operational tools."""

    name: str
    description: str
    category: str = "GENERAL"
    required_permission: str = "tools.execute"
    requires_approval: bool = False
    is_sensitive: bool = False
    rate_limit_per_minute: int = 60
    args_schema: type[BaseModel]

    def to_mcp_tool(self) -> MCPTool:
        """Converts this tool into an MCP-compliant tool specification."""
        schema = self.args_schema.model_json_schema()
        # Clean title & definitions for MCP client compatibility
        input_schema = {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        }
        return MCPTool(
            name=self.name,
            description=self.description,
            inputSchema=input_schema,
            category=self.category,
            required_permission=self.required_permission,
            requires_approval=self.requires_approval,
            is_sensitive=self.is_sensitive,
            rate_limit_per_minute=self.rate_limit_per_minute,
        )

    @abstractmethod
    async def execute(self, arguments: dict[str, Any], context: ToolExecutionContext) -> Any:
        """Executes the tool logic with validated arguments and security context."""
        pass
