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


async def extract_document(file_path: str) -> dict:
    """
    Extract text, fields, and tables from a document using Azure Document Intelligence.

    Args:
        file_path: Path to the PDF or image file to analyze.

    Returns:
        Dictionary with keys: extracted_text, fields, tables, page_count, raw_json
    """
    logger.info(f"Extraindo dados do documento: {file_path}")

    client = _get_client()

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Use prebuilt-document model for general extraction
    poller = client.begin_analyze_document(
        "prebuilt-document",
        analyze_request=file_bytes,
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
