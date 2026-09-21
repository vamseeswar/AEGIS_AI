"""AEGIS AI — Pydantic v2 Schemas for RAG & Semantic Retrieval
"""

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    knowledge_base_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.0, ge=-1.0, le=1.0)


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    filename: str
    page_number: int | None
    content: str
    score: float
    citation_token: str


class RAGQueryResponse(BaseModel):
    query: str
    total_retrieved: int
    results: list[SearchResultItem]
    formatted_context: str


class ReindexDocumentResponse(BaseModel):
    document_id: str
    chunks_created: int
    message: str = "Document parsed, chunked, and vector indexed successfully."
