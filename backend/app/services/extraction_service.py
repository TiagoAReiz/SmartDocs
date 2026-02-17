from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from loguru import logger

from app.config import settings


def _get_client() -> DocumentIntelligenceClient:
    return DocumentIntelligenceClient(
        endpoint=settings.AZURE_DI_ENDPOINT.strip(),
        credential=AzureKeyCredential(settings.AZURE_DI_KEY),
    )


async def _analyze_document(
    client: DocumentIntelligenceClient,
    model_id: str,
    file_bytes: bytes,
):
    poller = await client.begin_analyze_document(
        model_id,
        file_bytes,
        content_type="application/octet-stream",
        features=[
            DocumentAnalysisFeature.KEY_VALUE_PAIRS,
        ],
    )
    return await poller.result()


async def extract_document(file_source: str | bytes) -> dict:
    """
    Extract text, fields, and tables from a document using Azure Document Intelligence.

    Args:
        file_source: Path to the PDF/image file OR raw bytes.

    Returns:
        Dictionary with keys: extracted_text, fields, tables, page_count, raw_json
    """
    if not (settings.AZURE_DI_ENDPOINT and settings.AZURE_DI_KEY):
        raise RuntimeError("Azure Document Intelligence não configurado")

    if isinstance(file_source, str):
        logger.info(f"Extraindo dados do documento: {file_source}")
        with open(file_source, "rb") as f:
            file_bytes = f.read()
    else:
        logger.info(f"Extraindo dados de bytes em memória ({len(file_source)} bytes)")
        file_bytes = file_source

    logger.info(
        f"Azure DI endpoint={settings.AZURE_DI_ENDPOINT} model={settings.AZURE_DI_MODEL_ID}"
    )

    async with _get_client() as client:
        try:
            result = await _analyze_document(
                client, settings.AZURE_DI_MODEL_ID, file_bytes
            )
        except HttpResponseError as e:
            status_code = getattr(e, "status_code", None)
            error_code = getattr(getattr(e, "error", None), "code", None)
            should_fallback = (
                status_code == 404
                or error_code == "ModelNotFound"
                or "ModelNotFound" in str(e)
            )
            if should_fallback:
                fallback_model = "prebuilt-layout"
                logger.warning(
                    f"Modelo {settings.AZURE_DI_MODEL_ID} não encontrado. Tentando {fallback_model}."
                )
                result = await _analyze_document(client, fallback_model, file_bytes)
            else:
                raise

    # Extract text content
    extracted_text = result.content or ""

    # Extract page count
    page_count = len(result.pages) if result.pages else 0

    # Extract key-value pairs
    fields = []
    if result.key_value_pairs:
        for kvp in result.key_value_pairs:
            key = kvp.key.content if kvp.key else None
            value = kvp.value.content if kvp.value else None
            confidence = kvp.confidence or 0.0
            page_number = None
            if kvp.key and kvp.key.bounding_regions:
                page_number = kvp.key.bounding_regions[0].page_number

            if key:
                fields.append(
                    {
                        "field_key": key,
                        "field_value": value,
                        "confidence": round(confidence, 4),
                        "page_number": page_number,
                    }
                )
    elif extracted_text:
        for raw_line in extracted_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("•"):
                line = line.lstrip("•").strip()

            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            key = parts[0].strip()
            value = parts[1].strip()
            if not key or not value:
                continue
            if len(key) > 80:
                continue

            fields.append(
                {
                    "field_key": key,
                    "field_value": value,
                    "confidence": 0.0,
                    "page_number": None,
                }
            )
            if len(fields) >= 200:
                break

    # Extract tables
    tables = []
    if result.tables:
        for idx, table in enumerate(result.tables):
            headers = []
            rows_data: list[list[str]] = []

            # Organize cells into a grid
            max_row = max((c.row_index for c in table.cells), default=0)

            for row_idx in range(max_row + 1):
                row_cells = sorted(
                    [c for c in table.cells if c.row_index == row_idx],
                    key=lambda c: c.column_index,
                )
                row_values = [c.content or "" for c in row_cells]

                if row_idx == 0:
                    headers = row_values
                else:
                    rows_data.append(row_values)

            page_number = None
            if table.bounding_regions:
                page_number = table.bounding_regions[0].page_number

            tables.append(
                {
                    "table_index": idx,
                    "page_number": page_number,
                    "headers": headers,
                    "rows": rows_data,
                }
            )

    # Build raw JSON for storage
    raw_json = {
        "model_id": result.model_id,
        "page_count": page_count,
        "key_value_pairs_count": len(fields),
        "tables_count": len(tables),
    }

    logger.info(
        f"Extração concluída: {page_count} páginas, "
        f"{len(fields)} campos, {len(tables)} tabelas"
    )

    return {
        "extracted_text": extracted_text,
        "fields": fields,
        "tables": tables,
        "page_count": page_count,
        "raw_json": raw_json,
    }
