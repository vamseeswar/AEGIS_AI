"""AEGIS AI — Security Policies & Prompt Defense Schemas
"""

from typing import Any

from pydantic import BaseModel, Field


class SecurityPoliciesResponse(BaseModel):
    rate_limiting: dict[str, Any]
    security_headers: dict[str, Any]
    prompt_defense: dict[str, Any]
    path_traversal_defense: dict[str, Any]


class PromptDefenseTestRequest(BaseModel):
    user_query: str = Field(..., min_length=1)
    context_documents: list[dict[str, Any]] = Field(default_factory=list)
    system_instructions: str = Field(
        default="You are an enterprise AI assistant for AEGIS AI. Provide concise answers with citations."
    )


class PromptDefenseTestResponse(BaseModel):
    breakout_detected: bool
    breakout_tags: list[str]
    hardened_prompt: str
    is_safe: bool


class RateLimitStatusResponse(BaseModel):
    client_ip: str
    ip_status: dict[str, Any]
    tenant_status: dict[str, Any] | None = None
