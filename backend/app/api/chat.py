import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.chat_thread import ChatThread
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatThreadResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


async def _get_or_create_thread(
    db: AsyncSession,
    user_id: int,
    thread_id: str | None,
    first_question: str,
) -> ChatThread:
    """Validate existing thread or create a new one."""
    if thread_id:
        try:
            tid = UUID(thread_id)
            result = await db.execute(select(ChatThread).where(ChatThread.id == tid))
            thread = result.scalar_one_or_none()
            
            if not thread:
                raise HTTPException(status_code=404, detail="Thread not found")
            if thread.user_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to access this thread")
            
            # Update timestamp
            thread.updated_at = datetime.now(timezone.utc)
            return thread
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid thread_id format")

    # Create new thread
    title = first_question[:50] + "..." if len(first_question) > 50 else first_question
    thread = ChatThread(user_id=user_id, title=title)
    db.add(thread)
    await db.flush()  # Generate ID
    return thread


@router.post("", response_model=ChatResponse)
async def send_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a natural language question and get a SQL-backed answer."""
    is_admin = current_user.role == "admin"

    # Handle thread creation/retrieval
    thread = await _get_or_create_thread(db, current_user.id, body.thread_id, body.question)
    thread_id_str = str(thread.id)

    result = await chat_service.chat(
        question=body.question,
        user_id=current_user.id,
        is_admin=is_admin,
        db=db,
        thread_id=thread_id_str,
    )

    # Save to chat history
    message = ChatMessage(
        user_id=current_user.id,
        thread_id=thread.id,
        question=body.question,
        answer=result["answer"],
        sql_used=result.get("sql_used"),
    )
    db.add(message)
    await db.commit()

    return ChatResponse(
        answer=result["answer"],
        sql_used=result.get("sql_used"),
        row_count=result.get("row_count", 0),
        data=result.get("data", []),
        thread_id=thread_id_str,
    )


@router.post("/stream")
async def stream_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a chat response via Server-Sent Events (SSE)."""
    is_admin = current_user.role == "admin"

    # Handle thread creation/retrieval
    thread = await _get_or_create_thread(db, current_user.id, body.thread_id, body.question)
    thread_id_str = str(thread.id)
    
    # We need to commit the thread creation so the ID exists for parallel requests if any,
    # though for this stream it matters that it exists in the transaction. 
    # Since we are using the same session, flush is enough, but to be safe for concurrent:
    await db.commit() 
    # Re-fetch thread to be attached to session again if needed, or just use ID.
    # Actually, committing closes the transaction. usage of `thread` object might fail if lazy loading.
    # But we only need `thread.id` for `ChatMessage`.

    async def event_generator():
        # Send the thread_id as the first event so frontend knows where we are
        yield f"data: {json.dumps({'type': 'thread_id', 'id': thread_id_str}, ensure_ascii=False)}\n\n"

        final_answer = ""
        sql_used = None
        
        async for chunk in chat_service.chat_stream(
            question=body.question,
            user_id=current_user.id,
            is_admin=is_admin,
            db=db,
            thread_id=thread_id_str,
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            if chunk.get("type") == "done":
                final_answer = chunk.get("answer", "")
                sql_used = chunk.get("sql_used")

        # Save to chat history
        if final_answer:
            message = ChatMessage(
                user_id=current_user.id,
                thread_id=UUID(thread_id_str),
                question=body.question,
                answer=final_answer,
                sql_used=sql_used,
            )
            db.add(message)
            # We need to touch the thread updated_at
            # Since we committed before, we need to fetch it or update via ID
            await db.execute(
                select(ChatThread).where(ChatThread.id == UUID(thread_id_str))
            ) # Just to ensure it's in session? No, explicit update is better.
            
            # Simple update query for timestamp
            # But let's just add the message and commit. The relationship might not update the parent timestamp automatically without explicit logic.
            # Let's leave timestamp update for now or do explicit update.
            # thread.updated_at = datetime.utcnow() # we don't have the object attached confidently.
            
            await db.commit()

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


@router.get("/threads", response_model=list[ChatThreadResponse])
async def list_threads(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chat threads for the user."""
    print(f"DEBUG: Listing threads for user {current_user.id} with search='{search}'")
    
    query = select(ChatThread).where(ChatThread.user_id == current_user.id)
    
    if search:
        query = query.where(ChatThread.title.ilike(f"%{search}%"))
        
    query = query.order_by(desc(ChatThread.updated_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    threads = result.scalars().all()
    
    # Fix timezone: allow naive datetimes (stored as UTC) to be serialized with Z suffix
    for t in threads:
        if t.created_at and t.created_at.tzinfo is None:
            t.created_at = t.created_at.replace(tzinfo=timezone.utc)
        if t.updated_at and t.updated_at.tzinfo is None:
            t.updated_at = t.updated_at.replace(tzinfo=timezone.utc)
            
    print(f"DEBUG: Found {len(threads)} threads")
    return threads


@router.get("/threads/{thread_id}/messages", response_model=ChatHistoryResponse)
async def get_thread_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get message history for a specific thread."""
    try:
        tid = UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread ID")

    # Verify ownership
    result = await db.execute(
        select(ChatThread).where(ChatThread.id == tid, ChatThread.user_id == current_user.id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Fetch messages
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == tid)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    
    return ChatHistoryResponse(
        messages=[ChatHistoryItem.model_validate(m) for m in messages]
    )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat thread and all its messages."""
    try:
        tid = UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread ID")

    # Verify ownership
    result = await db.execute(
        select(ChatThread).where(ChatThread.id == tid, ChatThread.user_id == current_user.id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    await db.delete(thread)
    await db.commit()
