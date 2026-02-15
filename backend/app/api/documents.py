import math
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db, async_session
from app.models.document import Document, DocumentField, DocumentTable, DocumentStatus
from app.models.user import User
from app.schemas.document import (
    DocumentDetail,
    DocumentFieldSchema,
    DocumentListItem,
    DocumentListResponse,
    DocumentTableSchema,
    DocumentUploadItem,
    DocumentUploadResponse,
    ReprocessResponse,
)

from app.services.document_service import process_document, save_upload
from app.services.storage_service import storage_service
from app.utils.file_utils import is_supported

router = APIRouter(prefix="/documents", tags=["documents"])


async def _background_process(document_id: int):
    """Background task wrapper — creates its own session."""
    async with async_session() as db:
        await process_document(document_id, db)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_documents(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more files. Returns 202 and starts background processing."""
    documents = []

    for file in files:
        if not file.filename or not is_supported(file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de arquivo não suportado: {file.filename}",
            )

        content = await file.read()
        doc = await save_upload(content, file.filename, current_user.id, db)
        documents.append(doc)

    # Commit to get IDs
    await db.commit()

    # Schedule background processing for each document
    for doc in documents:
        background_tasks.add_task(_background_process, doc.id)

    return DocumentUploadResponse(
        documents=[
            DocumentUploadItem(
                id=doc.id,
                filename=doc.filename,
                status=doc.status,
                created_at=doc.created_at,
            )
            for doc in documents
        ]
    )


@router.post("/{document_id}/reprocess", response_model=ReprocessResponse, status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reprocess a failed document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado",
        )

    if doc.status == DocumentStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Documento já está sendo processado",
        )

    # Reset status and clear previous extraction data
    doc.status = DocumentStatus.UPLOADED
    doc.extracted_text = None
    doc.raw_json = None
    doc.error_message = None
    doc.page_count = None
    await db.commit()

    # Schedule reprocessing
    background_tasks.add_task(_background_process, doc.id)

    return ReprocessResponse(
        id=doc.id,
        status="processing",
        message="Reprocessamento iniciado",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    search: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents with search, status filter, and pagination."""
    query = select(Document).where(Document.user_id == current_user.id)

    # Apply search filter
    if search:
        query = query.where(Document.filename.ilike(f"%{search}%"))

    # Apply status filter
    if status_filter:
        query = query.where(Document.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    total_pages = max(1, math.ceil(total / per_page))
    offset = (page - 1) * per_page
    query = query.order_by(Document.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentListItem(
                id=doc.id,
                filename=doc.filename,
                original_extension=doc.original_extension,
                type=doc.type,
                upload_date=doc.created_at,
                page_count=doc.page_count,
                status=doc.status,
            )
            for doc in docs
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full document details with extracted fields and tables."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.fields), selectinload(Document.tables))
        .where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado",
        )

    return DocumentDetail(
        id=doc.id,
        filename=doc.filename,
        original_extension=doc.original_extension,
        mime_type=doc.mime_type,
        type=doc.type,
        upload_date=doc.created_at,
        page_count=doc.page_count,
        status=doc.status,
        blob_url=doc.blob_url,
        extracted_text=doc.extracted_text,
        fields=[DocumentFieldSchema.model_validate(f) for f in doc.fields],
        tables=[DocumentTableSchema.model_validate(t) for t in doc.tables],
        error_message=doc.error_message,
    )


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the original uploaded file."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado",
        )

    # Retrieve from blob storage
    try:
        file_bytes = await storage_service.get_blob_content(doc.blob_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo não encontrado no storage: {e}",
        )

    return Response(
        content=file_bytes,
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )
