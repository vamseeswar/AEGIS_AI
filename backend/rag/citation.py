"""AEGIS AI — Grounding & Citation Attribution Engine
Formats retrieved contexts with unambiguous citation tokens and validates references in AI outputs.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from backend.rag.retriever import SearchResult


@dataclass
class VerifiedCitation:
    citation_token: str
    document_id: str
    document_title: str
    filename: str
    page_number: int | None
    excerpt: str
    score: float


def format_context_with_citations(chunks: Sequence[SearchResult]) -> str:
    """Formats retrieved chunks into an XML-bounded context block with explicit citation tokens."""
    if not chunks:
        return "No relevant context found in tenant knowledge bases."

    formatted_blocks: list[str] = ["<context_documents>"]

    for idx, chunk in enumerate(chunks, start=1):
        block = (
            f'  <document index="{idx}" token="{chunk.citation_token}" title="{chunk.document_title}" '
            f'page="{chunk.page_number or 1}">\n'
            f"    {chunk.content.strip()}\n"
            f"  </document>"
        )
        formatted_blocks.append(block)

    formatted_blocks.append("</context_documents>")
    return "\n".join(formatted_blocks)


def extract_and_verify_citations(
    llm_output: str, retrieved_chunks: Sequence[SearchResult]
) -> tuple[list[VerifiedCitation], list[str]]:
    """Extracts citation tokens from generated text and verifies them against retrieved context.
    Returns (verified_citations, unverified_tokens).
    """
    token_map = {chunk.citation_token: chunk for chunk in retrieved_chunks}

    # Match tokens like [doc_id:p.1] or [source:1] or [doc-1234:p.3]
    raw_tokens = re.findall(r"\[[\w\-]+:(?:p\.?|\b)\d+\]", llm_output)

    verified: list[VerifiedCitation] = []
    unverified: list[str] = []
    seen_tokens = set()

    for token in raw_tokens:
        if token in seen_tokens:
            continue
        seen_tokens.add(token)

        if token in token_map:
            chunk = token_map[token]
            verified.append(
                VerifiedCitation(
                    citation_token=chunk.citation_token,
                    document_id=chunk.document_id,
                    document_title=chunk.document_title,
                    filename=chunk.filename,
                    page_number=chunk.page_number,
                    excerpt=chunk.content[:200] + ("..." if len(chunk.content) > 200 else ""),
                    score=chunk.score,
                )
            )
        else:
            unverified.append(token)

    return verified, unverified
