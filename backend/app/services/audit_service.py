from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks
from app.models.audit_log import AuditLog, ActionType

class AuditService:
    @staticmethod
    async def _insert_audit_log(
        db: AsyncSession,
        user_id: Optional[int],
        user_email: str,
        entity_type: str,
        entity_id: Any,
        action_type: ActionType,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Internal asynchronous method to save the log entry to the database."""
        # Note: the db session provided to BackgroundTasks must be an independent 
        # session object created specifically for the background task to avoid 
        # Transaction context errors after the original Request finishes.
        try:
            audit_log = AuditLog(
                user_id=user_id,
                user_email=user_email,
                entity_type=entity_type,
                entity_id=str(entity_id),
                action_type=action_type,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address
            )
            db.add(audit_log)
            await db.commit()
        except Exception as e:
            # We don't want Audit errors to crash the system, but we should log them.
            import logging
            logging.error(f"Failed to insert audit log: {str(e)}")
            await db.rollback()
        finally:
            await db.close()

    @staticmethod
    def log_action(
        background_tasks: BackgroundTasks,
        get_db_session_factory,  # Function that yields/returns a new AsyncSession
        user_id: Optional[int],
        user_email: str,
        entity_type: str,
        entity_id: Any,
        action_type: ActionType,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """
        Dispatches the audit logging work to a FastAPI BackgroundTask.
        Requires a session factory function (e.g., SessionLocal) that can create
        a new un-attached DB session exclusive for the background operation.
        """
        # Create a new session specifically for this background task
        # since the main request session will be closed by FastAPI.
        db_session = get_db_session_factory()
        
        background_tasks.add_task(
            AuditService._insert_audit_log,
            db=db_session,
            user_id=user_id,
            user_email=user_email,
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address
        )
