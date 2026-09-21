"""AEGIS AI — Documents, Chunks, and Knowledge Base Models
"""

from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TenantScopedMixin, generate_uuid


class KnowledgeBase(Base, TenantScopedMixin):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(100), default="all-MiniLM-L6-v2", nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    documents: Mapped[list["KnowledgeBaseDocument"]] = relationship(
        "KnowledgeBaseDocument", back_populates="knowledge_base", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="knowledge_base", cascade="all, delete-orphan"
    )


class Document(Base, TenantScopedMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PDF, DOCX, TXT, CSV, JSON
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, PARSING, INDEXED, FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    kb_links: Mapped[list["KnowledgeBaseDocument"]] = relationship(
        "KnowledgeBaseDocument", back_populates="document", cascade="all, delete-orphan"
    )

    @property
    def chunks_count(self) -> int:
        if self.doc_metadata and isinstance(self.doc_metadata, dict) and "chunks_count" in self.doc_metadata:
            return int(self.doc_metadata["chunks_count"])
        try:
            return len(self.chunks) if self.chunks else 0
        except Exception:
            return 0



class KnowledgeBaseDocument(Base, TenantScopedMixin):
    __tablename__ = "knowledge_base_documents"
    __table_args__ = (UniqueConstraint("knowledge_base_id", "document_id", name="uq_kb_document"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    knowledge_base_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
    document: Mapped["Document"] = relationship("Document", back_populates="kb_links")


class DocumentChunk(Base, TenantScopedMixin):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=True, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Stored as JSON array of floats for universal compatibility (Postgres/SQLite), with vector indexing via pgvector
    embedding_vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    knowledge_base: Mapped[Optional["KnowledgeBase"]] = relationship("KnowledgeBase", back_populates="chunks")
