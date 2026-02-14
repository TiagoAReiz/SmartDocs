import os
import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, DocumentField, DocumentTable, DocumentStatus
from app.models.document_log import DocumentLog
from app.services.conversion_service import convert_to_pdf
from app.services.extraction_service import extract_document
from app.utils.file_utils import (
    get_extension,
    get_mime_type,
    needs_conversion,
    is_supported,
    ensure_upload_dir,
    safe_filename,
)


async def save_upload(
    file_content: bytes,
    filename: str,
    user_id: int,
    db: AsyncSession,
) -> Document:
    """
    Save an uploaded file to disk and create a database record.

    Returns:
        The created Document instance with status=uploaded.
    """
    if not is_supported(filename):
        raise ValueError(f"Extensão não suportada: {get_extension(filename)}")

    upload_dir = ensure_upload_dir(settings.UPLOAD_DIR)
    safe_name = safe_filename(filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = upload_dir / unique_name

    # Save file to disk
    file_path.write_bytes(file_content)
    logger.info(f"Arquivo salvo: {file_path}")

    # Create database record
    doc = Document(
        user_id=user_id,
        filename=filename,
        original_extension=get_extension(filename).lstrip("."),
        mime_type=get_mime_type(filename),
        status=DocumentStatus.UPLOADED,
        blob_url=str(file_path),  # MVP: local path
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Log the upload event
    log = DocumentLog(
        document_id=doc.id,
        event="upload",
        details=f"Arquivo {filename} recebido com sucesso",
    )
    db.add(log)

    return doc


async def process_document(document_id: int, db: AsyncSession) -> None:
    """
    Background task: convert to PDF (if needed), extract data with Azure DI,
    and save results to the database.
    """
    from sqlalchemy import select

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if doc is None:
        logger.error(f"Documento {document_id} não encontrado para processamento")
        return

    try:
        # Update status to processing
        doc.status = DocumentStatus.PROCESSING
        await db.flush()

        file_path = doc.blob_url  # MVP: this is the local file path

        # Step 1: Convert to PDF if needed
        if needs_conversion(doc.filename):
            logger.info(f"Convertendo {doc.filename} para PDF...")
            file_path = await convert_to_pdf(file_path)

            log = DocumentLog(
                document_id=doc.id,
                event="conversion_complete",
                details=f"Convertido para PDF: {file_path}",
            )
            db.add(log)

        # Step 2: Extract data with Azure Document Intelligence
        logger.info(f"Iniciando extração para documento {doc.id}...")
        extraction = await extract_document(file_path)

        # Step 3: Save extracted data
        doc.extracted_text = extraction["extracted_text"]
        doc.page_count = extraction["page_count"]
        doc.raw_json = extraction["raw_json"]

        # Save fields
        for field_data in extraction["fields"]:
            field = DocumentField(
                document_id=doc.id,
                field_key=field_data["field_key"],
                field_value=field_data["field_value"],
                confidence=field_data["confidence"],
                page_number=field_data["page_number"],
            )
            db.add(field)

        # Save tables
        for table_data in extraction["tables"]:
            table = DocumentTable(
                document_id=doc.id,
                table_index=table_data["table_index"],
                page_number=table_data["page_number"],
                headers=table_data["headers"],
                rows=table_data["rows"],
            )
            db.add(table)

        # Update status
        doc.status = DocumentStatus.PROCESSED
        doc.error_message = None

        log = DocumentLog(
            document_id=doc.id,
            event="extraction_complete",
            details=f"{extraction['page_count']} páginas, "
                    f"{len(extraction['fields'])} campos, "
                    f"{len(extraction['tables'])} tabelas extraídos",
        )
        db.add(log)

        await db.commit()
        logger.info(f"Documento {doc.id} processado com sucesso")

    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao processar documento {doc.id}: {e}")

        # Update status to failed
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)

        log = DocumentLog(
            document_id=doc.id,
            event="processing_failed",
            details=str(e),
        )
        db.add(log)

        await db.commit()
