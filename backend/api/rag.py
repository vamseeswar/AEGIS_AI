"""AEGIS AI — RAG Retrieval & Indexing API Endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.rag.citation import format_context_with_citations
from backend.rag.ingestion import ingest_and_index_document
from backend.rag.retriever import retrieve_relevant_chunks
from backend.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    ReindexDocumentResponse,
    SearchResultItem,
)
from backend.security.dependencies import CurrentUser, require_permission

router = APIRouter(tags=["RAG & Semantic Retrieval"])


@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    summary="Semantic vector retrieval with citations",
)
async def query_rag_endpoint(
    request: RAGQueryRequest,
    current_user: CurrentUser = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves relevant document chunks matching user query from tenant knowledge bases."""
    results = await retrieve_relevant_chunks(
        query=request.query,
        organization_id=current_user.organization_id,
        db=db,
        knowledge_base_id=request.knowledge_base_id,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )

    formatted_context = format_context_with_citations(results)

    return RAGQueryResponse(
        query=request.query,
        total_retrieved=len(results),
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_title=r.document_title,
                filename=r.filename,
                page_number=r.page_number,
                content=r.content,
                score=r.score,
                citation_token=r.citation_token,
            )
            for r in results
        ],
        formatted_context=formatted_context,
    )


@router.post(
    "/documents/{document_id}/reindex",
    response_model=ReindexDocumentResponse,
    summary="Parse, chunk, embed, and index document",
)
async def reindex_document_endpoint(
    document_id: str,
    current_user: CurrentUser = Depends(require_permission("documents.upload")),
    db: AsyncSession = Depends(get_db),
):
    """Triggers recursive chunking and embedding generation for a stored document."""
    chunks_created = await ingest_and_index_document(
        document_id=document_id,
        current_user=current_user,
        db=db,
    )
    return ReindexDocumentResponse(
        document_id=document_id,
        chunks_created=chunks_created,
        message=f"Document successfully parsed into {chunks_created} chunks and vector indexed.",
    )
