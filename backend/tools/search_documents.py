"""AEGIS AI — Search Documents MCP Tool
Performs vector semantic search across tenant-isolated document knowledge bases.
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.rag.retriever import retrieve_relevant_chunks
from backend.tools.base import BaseTool, ToolExecutionContext


class SearchDocumentsArgs(BaseModel):
    query: str = Field(..., description="Natural language search query to locate relevant context")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of most similar text chunks to return")
    knowledge_base_id: str | None = Field(default=None, description="Optional filter for a specific knowledge base")


class SearchDocumentsTool(BaseTool):
    name = "search_documents"
    description = (
        "Searches indexed organizational documents and knowledge bases using dense vector semantic retrieval. "
        "Returns chunk excerpts, similarity scores, and citation identifiers."
    )
    category = "RAG"
    required_permission = "documents.read"
    args_schema = SearchDocumentsArgs

    async def execute(self, arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
        args = self.args_schema(**arguments)
        results = await retrieve_relevant_chunks(
            query=args.query,
            organization_id=context.organization_id,
            db=context.db,
            knowledge_base_id=args.knowledge_base_id,
            top_k=args.top_k,
        )

        chunks_data = [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "document_title": r.document_title,
                "filename": r.filename,
                "page_number": r.page_number,
                "content": r.content,
                "similarity_score": round(float(r.score), 4),
                "citation_token": r.citation_token,
            }
            for r in results
        ]

        return {
            "query": args.query,
            "total_retrieved": len(chunks_data),
            "results": chunks_data,
        }
