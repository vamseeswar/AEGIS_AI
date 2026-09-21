"""AEGIS AI — Document & Knowledge Base Management Service
Handles secure ingestion, storage persistence, metadata extraction, and tenant-scoped retrieval.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.errors import ResourceNotFoundError
from backend.db.base import generate_uuid
from backend.models.document import Document, KnowledgeBase, KnowledgeBaseDocument
from backend.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
)
from backend.security.dependencies import CurrentUser, enforce_tenant_access
from backend.storage import get_storage_provider
from backend.storage.validation import validate_upload_file


async def upload_document(
    file_bytes: bytes,
    original_filename: str,
    content_type: str | None,
    title: str | None,
    current_user: CurrentUser,
    knowledge_base_id: str | None,
    db: AsyncSession,
) -> DocumentResponse:
    """Validates, stores file on disk, and creates a tenant-isolated database record."""
    # 1. Validate file security policies (MIME, extension, size limit)
    clean_filename, file_type, mime_type, file_size = validate_upload_file(
        filename=original_filename,
        content=file_bytes,
        content_type=content_type,
    )

    doc_id = generate_uuid()
    storage = get_storage_provider()

    # 2. Persist to isolated tenant storage directory
    storage_path = await storage.save_file(
        tenant_id=current_user.organization_id,
        document_id=doc_id,
        filename=clean_filename,
        content=file_bytes,
    )

    doc_title = title.strip() if title and title.strip() else clean_filename

    # 3. Create database Document record
    document = Document(
        id=doc_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        title=doc_title,
        filename=clean_filename,
        file_type=file_type,
        mime_type=mime_type,
        file_size_bytes=file_size,
        storage_path=storage_path,
        status="INDEXED",  # Ready for chunking in Phase 6
        error_message=None,
        doc_metadata={
            "original_filename": original_filename,
            "uploader_email": current_user.email,
        },
    )
    db.add(document)
    await db.flush()

    # 4. Associate with KnowledgeBase if provided or resolve default KB
    target_kb_id = knowledge_base_id
    if not target_kb_id:
        # Check if default KB exists for tenant, otherwise create one
        kb_query = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.organization_id == current_user.organization_id
            )
        )
        default_kb = kb_query.scalars().first()
        if not default_kb:
            default_kb = KnowledgeBase(
                organization_id=current_user.organization_id,
                name="Default Knowledge Base",
                description="Default tenant knowledge repository",
            )
            db.add(default_kb)
            await db.flush()
        target_kb_id = default_kb.id

    kb_link = KnowledgeBaseDocument(
        organization_id=current_user.organization_id,
        knowledge_base_id=target_kb_id,
        document_id=document.id,
    )
    db.add(kb_link)
    await db.commit()
    await db.refresh(document)

    # Attempt automatic chunking and indexing on upload
    try:
        from backend.rag.ingestion import ingest_and_index_document
        await ingest_and_index_document(document.id, current_user, db)
        await db.refresh(document)
    except Exception:
        pass

    return DocumentResponse.model_validate(document)


async def list_documents(
    current_user: CurrentUser,
    search: str | None,
    status_filter: str | None,
    page: int,
    page_size: int,
    db: AsyncSession,
) -> DocumentListResponse:
    """Lists documents scoped to current tenant with optional search, status filtering, and pagination."""
    query = select(Document).where(Document.organization_id == current_user.organization_id)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            Document.title.ilike(search_pattern) | Document.filename.ilike(search_pattern)
        )

    if status_filter:
        query = query.where(Document.status == status_filter.upper())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = (
        query.options(selectinload(Document.chunks))
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(query)
    documents = res.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession,
) -> Document:
    """Retrieves document record ensuring strict tenant isolation."""
    query = await db.execute(select(Document).where(Document.id == document_id))
    document = query.scalar_one_or_none()

    if not document:
        raise ResourceNotFoundError("Document", document_id)

    enforce_tenant_access(document.organization_id, current_user)
    return document


async def download_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession,
) -> tuple[bytes, str, str]:
    """Reads raw file bytes from storage for download, verifying tenant boundaries.
    Returns (file_bytes, filename, mime_type).
    """
    document = await get_document(document_id, current_user, db)
    storage = get_storage_provider()
    content = await storage.get_file(document.storage_path)
    return content, document.filename, document.mime_type


async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession,
) -> bool:
    """Deletes physical file from storage and removes DB record with cascade."""
    document = await get_document(document_id, current_user, db)
    storage = get_storage_provider()

    # Delete physical file from disk
    await storage.delete_file(document.storage_path)

    # Delete database record
    await db.delete(document)
    await db.commit()
    return True


async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession,
) -> KnowledgeBaseResponse:
    """Creates a new knowledge base partition for the tenant."""
    kb = KnowledgeBase(
        organization_id=current_user.organization_id,
        name=request.name,
        description=request.description,
        embedding_model=request.embedding_model,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    return KnowledgeBaseResponse(
        id=kb.id,
        organization_id=kb.organization_id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        documents_count=0,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


async def list_knowledge_bases(
    current_user: CurrentUser,
    db: AsyncSession,
) -> KnowledgeBaseListResponse:
    """Lists all knowledge base collections for the tenant."""
    query = (
        select(KnowledgeBase)
        .where(KnowledgeBase.organization_id == current_user.organization_id)
        .options(selectinload(KnowledgeBase.documents))
        .order_by(KnowledgeBase.created_at.desc())
    )
    res = await db.execute(query)
    kbs = res.scalars().all()

    items = [
        KnowledgeBaseResponse(
            id=kb.id,
            organization_id=kb.organization_id,
            name=kb.name,
            description=kb.description,
            embedding_model=kb.embedding_model,
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
            documents_count=len(kb.documents),
            created_at=kb.created_at,
            updated_at=kb.updated_at,
        )
        for kb in kbs
    ]
    return KnowledgeBaseListResponse(items=items, total=len(items))


async def get_knowledge_base(
    kb_id: str,
    current_user: CurrentUser,
    db: AsyncSession,
) -> KnowledgeBaseResponse:
    """Retrieves knowledge base details with tenant check."""
    query = (
        select(KnowledgeBase)
        .where(KnowledgeBase.id == kb_id)
        .options(selectinload(KnowledgeBase.documents))
    )
    res = await db.execute(query)
    kb = res.scalar_one_or_none()

    if not kb:
        raise ResourceNotFoundError("KnowledgeBase", kb_id)

    enforce_tenant_access(kb.organization_id, current_user)

    return KnowledgeBaseResponse(
        id=kb.id,
        organization_id=kb.organization_id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        documents_count=len(kb.documents),
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )
