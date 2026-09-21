"""AEGIS AI — Document & Knowledge Base API Endpoints
Provides secure file upload, retrieval, download, deletion, and knowledge base partition management.
"""

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
)
from backend.security.dependencies import CurrentUser, require_permission
from backend.services.document_service import (
    create_knowledge_base,
    delete_document,
    download_document,
    get_document,
    get_knowledge_base,
    list_documents,
    list_knowledge_bases,
    upload_document,
)

router = APIRouter(prefix="/documents", tags=["Document Management"])
kb_router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Base Management"])


# ------------------------------------------------------------
# Documents Endpoints
# ------------------------------------------------------------


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document",
)
async def upload_file_endpoint(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    knowledge_base_id: str | None = Form(None),
    current_user: CurrentUser = Depends(require_permission("documents.upload")),
    db: AsyncSession = Depends(get_db),
):
    """Uploads a document file (PDF, DOCX, TXT, CSV, JSON), stores it under tenant directory,
    and indexes document metadata.
    """
    file_bytes = await file.read()
    doc_response = await upload_document(
        file_bytes=file_bytes,
        original_filename=file.filename or "uploaded_file.txt",
        content_type=file.content_type,
        title=title,
        current_user=current_user,
        knowledge_base_id=knowledge_base_id,
        db=db,
    )
    return DocumentUploadResponse(
        document=doc_response,
        message=f"Document '{doc_response.filename}' uploaded and indexed successfully.",
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents for current organization",
)
async def list_documents_endpoint(
    search: str | None = Query(None, description="Search by title or filename"),
    status: str | None = Query(None, description="Filter by status (PENDING, INDEXED, FAILED)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
):
    """Lists indexed documents scoped strictly to caller's organization."""
    return await list_documents(
        current_user=current_user,
        search=search,
        status_filter=status,
        page=page,
        page_size=page_size,
        db=db,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document_endpoint(
    document_id: str,
    current_user: CurrentUser = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves document record with tenant access validation."""
    doc = await get_document(document_id, current_user, db)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/download",
    summary="Download original document file",
)
async def download_document_endpoint(
    document_id: str,
    current_user: CurrentUser = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
):
    """Streams original document content with appropriate MIME headers."""
    content, filename, mime_type = await download_document(document_id, current_user, db)
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/{document_id}",
    summary="Delete document",
)
async def delete_document_endpoint(
    document_id: str,
    current_user: CurrentUser = Depends(require_permission("documents.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Deletes physical file and database records."""
    await delete_document(document_id, current_user, db)
    return {"message": "Document deleted successfully.", "id": document_id}


# ------------------------------------------------------------
# Knowledge Base Endpoints
# ------------------------------------------------------------


@kb_router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new knowledge base",
)
async def create_kb_endpoint(
    request: KnowledgeBaseCreateRequest,
    current_user: CurrentUser = Depends(require_permission("knowledgebase.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Creates a vector store knowledge base collection for the tenant."""
    return await create_knowledge_base(request, current_user, db)


@kb_router.get(
    "",
    response_model=KnowledgeBaseListResponse,
    summary="List knowledge bases",
)
async def list_kbs_endpoint(
    current_user: CurrentUser = Depends(require_permission("knowledgebase.read")),
    db: AsyncSession = Depends(get_db),
):
    """Lists all knowledge bases belonging to the caller's organization."""
    return await list_knowledge_bases(current_user, db)


@kb_router.get(
    "/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="Get knowledge base details",
)
async def get_kb_endpoint(
    kb_id: str,
    current_user: CurrentUser = Depends(require_permission("knowledgebase.read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves knowledge base details."""
    return await get_knowledge_base(kb_id, current_user, db)
