"""AEGIS AI — Vector Store Retriever & Similarity Search
Provides tenant-isolated vector cosine search across DocumentChunk embeddings.
Compatible with PostgreSQL pgvector and fallback in-memory cosine computation for SQLite.
Includes keyword-boosted re-ranking for improved precision.
"""

import re
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.document import Document, DocumentChunk
from backend.rag.embeddings import get_embedding_provider


@dataclass
class SearchResult:
    """Represents a retrieved document chunk with similarity score and citation token."""
    chunk_id: str
    document_id: str
    document_title: str
    filename: str
    page_number: int | None
    content: str
    score: float
    citation_token: str


def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def _keyword_boost(query: str, content: str) -> float:
    """Computes a keyword overlap bonus to re-rank chunks that contain query terms.
    
    Returns a small boost value [0.0, 0.15] based on the fraction of query keywords
    found in the chunk content. This addresses the case where semantic similarity
    alone misses exact term matches (e.g., 'contact details', 'email', 'phone').
    """
    if not query or not content:
        return 0.0

    # Extract meaningful words from the query (ignore short stop words)
    stop_words = {"a", "an", "the", "is", "in", "of", "and", "or", "for", "to", "on",
                  "at", "by", "with", "from", "are", "was", "were", "has", "have",
                  "that", "this", "it", "its", "be", "do", "did", "as", "so", "but",
                  "what", "which", "who", "how", "when", "where", "me", "my", "your",
                  "i", "you", "he", "she", "they", "we", "file", "document", "provide",
                  "show", "tell", "give", "list", "find", "get", "about", "involved"}

    query_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())) - stop_words
    if not query_words:
        return 0.0

    content_lower = content.lower()
    matched = sum(1 for w in query_words if w in content_lower)
    ratio = matched / len(query_words)

    return min(ratio * 0.15, 0.15)  # Cap boost at 0.15


async def retrieve_relevant_chunks(
    query: str,
    organization_id: str,
    db: AsyncSession,
    knowledge_base_id: str | None = None,
    top_k: int = 8,
    score_threshold: float = 0.0,
) -> list[SearchResult]:
    """Embeds query and retrieves top_k most similar chunks belonging strictly to organization_id.
    
    Uses combined cosine similarity + keyword boost re-ranking to improve precision.
    """
    # 1. Generate query embedding
    embedder = get_embedding_provider()
    query_vector = await embedder.embed_query(query)

    # 2. Query chunks scoped to tenant
    stmt = (
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.organization_id == organization_id,
            DocumentChunk.embedding_vector.is_not(None),
        )
        .options(selectinload(DocumentChunk.document))
    )

    if knowledge_base_id:
        stmt = stmt.where(DocumentChunk.knowledge_base_id == knowledge_base_id)

    res = await db.execute(stmt)
    chunks = res.scalars().all()

    if not chunks:
        return []

    # 3. Compute cosine similarity + keyword boost for each chunk
    scored_results: list[SearchResult] = []

    for chunk in chunks:
        if not chunk.embedding_vector:
            continue

        cosine_score = compute_cosine_similarity(query_vector, chunk.embedding_vector)
        keyword_boost = _keyword_boost(query, chunk.content)
        combined_score = cosine_score + keyword_boost

        if combined_score >= score_threshold:
            page_str = f"p.{chunk.page_number}" if chunk.page_number else "p.1"
            doc_short_id = chunk.document_id[:8]
            citation_token = f"[{doc_short_id}:{page_str}]"

            scored_results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=chunk.document.title if chunk.document else "Document",
                    filename=chunk.document.filename if chunk.document else "file.txt",
                    page_number=chunk.page_number,
                    content=chunk.content,
                    score=round(combined_score, 4),
                    citation_token=citation_token,
                )
            )

    # 4. Sort descending by combined score and deduplicate by content similarity
    scored_results.sort(key=lambda x: x.score, reverse=True)

    # 5. Deduplicate: skip chunks whose content is >80% substring of an already-selected chunk
    deduplicated: list[SearchResult] = []
    seen_content_prefixes: set[str] = set()

    for result in scored_results:
        # Use first 100 chars as a fingerprint to detect near-duplicate chunks
        content_key = result.content[:100].strip().lower()
        if content_key not in seen_content_prefixes:
            seen_content_prefixes.add(content_key)
            deduplicated.append(result)

    return deduplicated[:top_k]
