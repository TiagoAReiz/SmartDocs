from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentField, DocumentTable, DocumentStatus
from app.models.document_log import DocumentLog
from app.models.document_chunk import DocumentChunk
from app.services.conversion_service import convert_to_pdf
from app.services.extraction_service import extract_document
from app.services.storage_service import storage_service
from app.services.chunking_service import create_chunks
from app.services.embedding_service import generate_embeddings
from app.utils.file_utils import (
    get_extension,
    get_mime_type,
    needs_conversion,
    is_supported,
)


async def save_upload(
    file_content: bytes,
    filename: str,
    user_id: int,
    db: AsyncSession,
) -> Document:
    """
    Save an uploaded file to storage and create a database record.

    Returns:
        The created Document instance with status=uploaded.
    """
    if not is_supported(filename):
        raise ValueError(f"Extensão não suportada: {get_extension(filename)}")

    # Upload to Blob Storage (Azurite/Azure)
    mime_type = get_mime_type(filename)
    blob_url = await storage_service.upload_file(file_content, filename, mime_type)

    logger.info(f"Arquivo salvo no storage: {blob_url}")

    # Create database record
    doc = Document(
        user_id=user_id,
        filename=filename,
        original_extension=get_extension(filename).lstrip("."),
        mime_type=mime_type,
        status=DocumentStatus.UPLOADED,
        blob_url=blob_url,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Log the upload event
    log = DocumentLog(
        document_id=doc.id,
        event_type="upload",
        message=f"Arquivo {filename} recebido com sucesso",
    )
    db.add(log)

    return doc


async def process_document(document_id: int, db: AsyncSession) -> None:
    """
    Background task: download from storage, convert to PDF (if needed), extract data with Azure DI,
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

        # Step 1: Download from blob
        logger.info(f"Baixando documento do storage: {doc.blob_url}")
        file_bytes = await storage_service.get_blob_content(doc.blob_url)

        # Step 1.5: Convert to PDF if needed
        if needs_conversion(doc.filename):
            import tempfile

            suffix = Path(doc.filename).suffix
            # Use tempfile to save bytes for conversion tool
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            try:
                logger.info(f"Convertendo {doc.filename} para PDF...")
                converted_path = await convert_to_pdf(tmp_path)

                # Update file_bytes with converted content
                file_bytes = Path(converted_path).read_bytes()

                # Cleanup converted file
                Path(converted_path).unlink(missing_ok=True)

                log = DocumentLog(
                    document_id=doc.id,
                    event_type="conversion_complete",
                    message="Convertido para PDF (temp)",
                )
                db.add(log)
            finally:
                # Cleanup original temp
                Path(tmp_path).unlink(missing_ok=True)

        # Step 2: Extract data with Azure Document Intelligence
        logger.info(f"Iniciando extração para documento {doc.id}...")
        extraction = await extract_document(file_bytes)

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
            event_type="extraction_complete",
            message=f"{extraction['page_count']} páginas, "
            f"{len(extraction['fields'])} campos, "
            f"{len(extraction['tables'])} tabelas extraídos",
        )
        db.add(log)

        # Step 4: Create semantic chunks and embeddings for RAG
        try:
            extracted_text = extraction.get("extracted_text", "")
            if extracted_text and extracted_text.strip():
                chunks = create_chunks(extracted_text)
                if chunks:
                    logger.info(
                        f"Documento {doc.id}: {len(chunks)} chunks criados, "
                        f"gerando embeddings..."
                    )
                    texts = [c.content for c in chunks]
                    embeddings = await generate_embeddings(texts)

                    for chunk, embedding in zip(chunks, embeddings):
                        doc_chunk = DocumentChunk(
                            document_id=doc.id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            section_type=chunk.section_type,
                            token_count=chunk.token_count,
                            embedding=embedding,
                            metadata_json=chunk.metadata,
                        )
                        db.add(doc_chunk)

                    log = DocumentLog(
                        document_id=doc.id,
                        event_type="rag_indexing_complete",
                        message=f"{len(chunks)} chunks indexados para RAG",
                    )
                    db.add(log)
                    logger.info(
                        f"Documento {doc.id}: {len(chunks)} chunks indexados para RAG"
                    )
        except Exception as rag_err:
            # RAG indexing failure should NOT fail the whole document processing
            logger.warning(
                f"Documento {doc.id}: falha na indexação RAG (não-crítico): {rag_err}"
            )
            log = DocumentLog(
                document_id=doc.id,
                event_type="rag_indexing_failed",
                message=f"Falha na indexação RAG: {rag_err}",
            )
            db.add(log)

        await db.commit()
        logger.info(f"Documento {doc.id} processado com sucesso")

    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao processar documento {document_id}: {e}")

        # Update status to failed using a direct update to avoid "MissingGreenlet"
        # because 'doc' object is expired after rollback
        from sqlalchemy import update

        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status=DocumentStatus.FAILED, error_message=str(e))
        )

        log = DocumentLog(
            document_id=document_id,
            event_type="processing_failed",
            message=str(e),
        )
        db.add(log)

        await db.commit()
