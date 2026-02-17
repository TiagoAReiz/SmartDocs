import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryItem,
    ChatHistoryResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a natural language question and get a SQL-backed answer."""
    is_admin = current_user.role == "admin"

    result = await chat_service.chat(
        question=body.question,
        user_id=current_user.id,
        is_admin=is_admin,
        db=db,
    )

    # Save to chat history
    message = ChatMessage(
        user_id=current_user.id,
        question=body.question,
        answer=result["answer"],
        sql_used=result.get("sql_used"),
    )
    db.add(message)

    return ChatResponse(
        answer=result["answer"],
        sql_used=result.get("sql_used"),
        row_count=result.get("row_count", 0),
        data=result.get("data", []),
    )


@router.post("/stream")
async def stream_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a chat response via Server-Sent Events (SSE).

    Each SSE message is a JSON object with a "type" field:
    - {"type": "token", "content": "..."} — streamed text token
    - {"type": "tool_start", "name": "..."} — tool invocation started
    - {"type": "tool_end", "name": "...", "content": "..."} — tool finished
    - {"type": "done", "answer": "...", "sql_used": ..., "row_count": ...} — final result
    - {"type": "error", "content": "..."} — error occurred
    """
    is_admin = current_user.role == "admin"

    async def event_generator():
        final_answer = ""
        async for chunk in chat_service.chat_stream(
            question=body.question,
            user_id=current_user.id,
            is_admin=is_admin,
            db=db,
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # Capture the final answer for saving to history
            if chunk.get("type") == "done":
                final_answer = chunk.get("answer", "")

        # Save to chat history after streaming completes
        if final_answer:
            message = ChatMessage(
                user_id=current_user.id,
                question=body.question,
                answer=final_answer,
                sql_used=None,
            )
            db.add(message)
            await db.flush()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's chat message history."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        messages=[ChatHistoryItem.model_validate(m) for m in messages]
    )

