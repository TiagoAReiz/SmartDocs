from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.document_processing_job import JobStatus


class DocumentProcessingJobBase(BaseModel):
    document_id: int
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    error_log: Optional[str] = None


class DocumentProcessingJobCreate(BaseModel):
    document_id: int


class DocumentProcessingJobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    attempts: Optional[int] = None
    error_log: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DocumentProcessingJobResponse(DocumentProcessingJobBase):
    id: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
