from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, asc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
import math

from app.core.deps import require_admin
from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog, ActionType
from app.schemas.audit_log import AuditLogResponse, PaginatedAuditLogsResponse

router = APIRouter(prefix="/admin/audit-logs", tags=["admin-audit"])

@router.get("", response_model=PaginatedAuditLogsResponse)
async def get_audit_logs(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    email: Optional[str] = Query(None, description="Filter by user email"),
    action_type: Optional[ActionType] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. USER, DOCUMENT, CHAT_THREAD)"),
    sort_by: Optional[str] = Query(None, description="Sort column (created_at or user_email)"),
    sort_order: Optional[str] = Query(None, description="Sort direction (asc or desc)"),
):
    """Get paginated audit logs with optional filtering and sorting (Admin only)."""
    
    query = select(AuditLog)
    
    # 1. Filters
    if email:
        query = query.where(AuditLog.user_email.ilike(f"%{email}%"))
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    if entity_type:
        # Match case-insensitive just in case
        query = query.where(cast(AuditLog.entity_type, String).ilike(f"%{entity_type.upper()}%"))
        
    # 2. Count Total BEFORE Pagination
    # Import func for count if you haven't, assuming `from sqlalchemy import func`
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = max(1, math.ceil(total / limit))
    
    # 3. Sorting
    order_column = AuditLog.created_at
    if sort_by == 'user_email':
        order_column = AuditLog.user_email
        
    if sort_order and sort_order.lower() == 'asc':
        query = query.order_by(asc(order_column))
    else:
        # Default is desc for created_at
        query = query.order_by(desc(order_column))
        
    # 4. Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # 5. Execute
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Serialize the list
    log_responses = [AuditLogResponse.model_validate(log) for log in logs]
    
    return PaginatedAuditLogsResponse(
        data=log_responses,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )
