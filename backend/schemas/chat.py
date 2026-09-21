"""AEGIS AI — Chat and Conversation Schemas
Pydantic v2 schemas for multi-turn conversations, messages, streaming events, and source citations.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New Conversation", min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    organization_id: str
    title: str
    status: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class ChatCitationItem(BaseModel):
    citation_token: str
    document_id: str
    document_title: str
    filename: str
    page_number: int | None = None
    excerpt: str
    score: float


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    user_id: str | None = None
    role: str
    content: str
    citations_json: list[dict[str, Any]] | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]
    total: int


class ChatStreamRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1)
    knowledge_base_id: str | None = None
    model: str | None = None
    temperature: float = 0.2
