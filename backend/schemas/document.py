"""AEGIS AI — Pydantic v2 Schemas for Documents & Knowledge Bases
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str
    title: str
    filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    status: str
    error_message: str | None = None
    doc_metadata: dict[str, Any] | None = None
    chunks_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 20


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str = "Document uploaded and indexed successfully."


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    embedding_model: str = Field(default="all-MiniLM-L6-v2", max_length=100)
    chunk_size: int = Field(default=500, ge=100, le=4000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: str | None = None
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    documents_count: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    items: list[KnowledgeBaseResponse]
    total: int
