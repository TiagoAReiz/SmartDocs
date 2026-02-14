from datetime import datetime

from pydantic import BaseModel


class DocumentFieldSchema(BaseModel):
    field_key: str
    field_value: str | None = None
    confidence: float | None = None
    page_number: int | None = None

    model_config = {"from_attributes": True}


class DocumentTableSchema(BaseModel):
    table_index: int
    page_number: int | None = None
    headers: list[str] | None = None
    rows: list[list[str]] | None = None

    model_config = {"from_attributes": True}


class DocumentUploadItem(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    documents: list[DocumentUploadItem]


class DocumentListItem(BaseModel):
    id: int
    filename: str
    original_extension: str
    type: str | None = None
    upload_date: datetime | None = None
    page_count: int | None = None
    status: str

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class DocumentDetail(BaseModel):
    id: int
    filename: str
    original_extension: str
    mime_type: str | None = None
    type: str | None = None
    upload_date: datetime | None = None
    page_count: int | None = None
    status: str
    blob_url: str | None = None
    extracted_text: str | None = None
    fields: list[DocumentFieldSchema] = []
    tables: list[DocumentTableSchema] = []
    error_message: str | None = None

    model_config = {"from_attributes": True}


class ReprocessResponse(BaseModel):
    id: int
    status: str
    message: str
