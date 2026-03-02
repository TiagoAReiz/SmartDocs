from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Integer
from sqlalchemy.sql import func
import uuid
import enum

from .base import Base


class ActionType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    PROCESS = "PROCESS"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ondelete="SET NULL" ensures the audit log stays even if the user is deleted
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String, index=True, nullable=False)
    
    entity_type = Column(String, index=True, nullable=False)
    entity_id = Column(String, index=True, nullable=False)
    
    action_type = Column(SQLEnum(ActionType), nullable=False, index=True)
    
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    ip_address = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
