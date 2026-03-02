from typing import Optional, Any, Dict, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.audit_log import ActionType

class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[int] = None
    user_email: str
    entity_type: str
    entity_id: str
    action_type: ActionType
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PaginatedAuditLogsResponse(BaseModel):
    data: List[AuditLogResponse]
    total: int
    page: int
    limit: int
    total_pages: int
