from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sql_used: str | None = None
    row_count: int = 0
    data: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []


class ChatHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryItem]
