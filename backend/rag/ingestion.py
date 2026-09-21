"""AEGIS AI — Document Ingestion & Vector Indexing Pipeline
Extracts, chunks, embeds, and persists DocumentChunk records to database.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import ResourceNotFoundError
from backend.models.document import Document, DocumentChunk, KnowledgeBaseDocument
from backend.rag.chunking import RecursiveCharacterChunker
from backend.rag.embeddings import get_embedding_provider
from backend.rag.parsers import parse_document
from backend.security.dependencies import CurrentUser, enforce_tenant_access
from backend.storage import get_storage_provider


async def ingest_and_index_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> int:
    """Parses, chunks, embeds, and indexes a stored document into the vector store.
    Returns total chunk count created.
    """
    # 1. Resolve Document with tenant validation
    doc_res = await db.execute(select(Document).where(Document.id == document_id))
    document = doc_res.scalar_one_or_none()

    if not document:
        raise ResourceNotFoundError("Document", document_id)

    enforce_tenant_access(document.organization_id, current_user)

    # 2. Retrieve file content from storage provider
    storage = get_storage_provider()
    file_bytes = await storage.get_file(document.storage_path)

    # 3. Parse into pages
    parsed_pages = parse_document(
        file_bytes=file_bytes,
        file_type=document.file_type,
        original_filename=document.filename,
    )

    # 4. Chunk parsed text
    chunker = RecursiveCharacterChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    text_chunks = chunker.chunk_pages(parsed_pages)

    if not text_chunks:
        return 0

    # 5. Generate vector embeddings in batch
    embedder = get_embedding_provider()
    raw_texts = [c.content for c in text_chunks]
    embeddings = await embedder.embed_texts(raw_texts)

    # 6. Resolve associated Knowledge Base ID if linked
    kb_res = await db.execute(
        select(KnowledgeBaseDocument.knowledge_base_id).where(
            KnowledgeBaseDocument.document_id == document.id
        )
    )
    kb_id = kb_res.scalar_one_or_none()

    # 7. Clean up existing chunks for this document (idempotent re-indexing)
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    # 8. Persist new DocumentChunk entities
    for chunk, embedding in zip(text_chunks, embeddings, strict=False):
        db_chunk = DocumentChunk(
            organization_id=document.organization_id,
            document_id=document.id,
            knowledge_base_id=kb_id,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            content=chunk.content,
            chunk_metadata=chunk.metadata,
            embedding_vector=embedding,
        )
        db.add(db_chunk)

    document.status = "INDEXED"
    document.error_message = None
    meta = dict(document.doc_metadata or {})
    meta["chunks_count"] = len(text_chunks)
    document.doc_metadata = meta
    await db.commit()

    return len(text_chunks)
