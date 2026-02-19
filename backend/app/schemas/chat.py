from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sql_used: str | None = None
    row_count: int = 0
    data: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    thread_id: str | None = None


class ChatHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryItem]


class ChatThreadResponse(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
