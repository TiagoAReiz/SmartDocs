from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
from loguru import logger

from app.config import settings


def _get_client() -> DocumentIntelligenceClient:
    """Create an Azure Document Intelligence client."""
    return DocumentIntelligenceClient(
        endpoint=settings.AZURE_DI_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_DI_KEY),
    )


async def extract_document(file_source: str | bytes) -> dict:
    """
    Extract text, fields, and tables from a document using Azure Document Intelligence.

    Args:
        file_source: Path to the PDF/image file OR raw bytes.

    Returns:
        Dictionary with keys: extracted_text, fields, tables, page_count, raw_json
    """
    client = None
    if settings.AZURE_DI_ENDPOINT and settings.AZURE_DI_KEY:
        try:
            client = _get_client()
        except Exception as e:
            logger.warning(f"Falha ao criar cliente Azure DI: {e}. Usando mock.")
    
    if not client:
        logger.warning("Credenciais do Azure Document Intelligence ausentes. Usando extração MOCK.")
        # Mock response
        return {
            "extracted_text": "Texto extraído simulado (MOCK). Configure AZURE_DI_ENDPOINT e AZURE_DI_KEY para extração real.",
            "fields": [
                {"field_key": "VendorName", "field_value": "Mock Vendor", "confidence": 0.99, "page_number": 1},
                {"field_key": "InvoiceDate", "field_value": "2023-10-27", "confidence": 0.98, "page_number": 1},
                {"field_key": "Total", "field_value": "123.45", "confidence": 0.95, "page_number": 1}
            ],
            "tables": [],
            "page_count": 1,
            "raw_json": {"mock": True}
        }

    
    if isinstance(file_source, str):
        logger.info(f"Extraindo dados do documento: {file_source}")
        with open(file_source, "rb") as f:
            file_bytes = f.read()
    else:
        logger.info(f"Extraindo dados de bytes em memória ({len(file_source)} bytes)")
        file_bytes = file_source

    # Use prebuilt-document model for general extraction
    poller = client.begin_analyze_document(
        "prebuilt-document",
        file_bytes,
        content_type="application/octet-stream",
    )

    result = poller.result()

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
                fields.append({
                    "field_key": key,
                    "field_value": value,
                    "confidence": round(confidence, 4),
                    "page_number": page_number,
                })

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

            tables.append({
                "table_index": idx,
                "page_number": page_number,
                "headers": headers,
                "rows": rows_data,
            })

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
