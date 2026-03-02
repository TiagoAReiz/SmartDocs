from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.deps import require_admin
from app.core.security import hash_password
from app.database import get_db, async_session
from app.models.user import User
from app.schemas.auth import UserCreate, UserResponse, UserUpdate
from app.services.audit_service import AuditService
from app.models.audit_log import ActionType

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=dict)
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all registered users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    return {"users": [UserResponse.model_validate(u) for u in users]}


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado",
        )

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()

    # Convert User dictionary data ignoring password
    new_data = {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role}

    AuditService.log_action(
        background_tasks=background_tasks,
        get_db_session_factory=async_session,
        user_id=admin.id,
        user_email=admin.email,
        entity_type="USER",
        entity_id=user.id,
        action_type=ActionType.CREATE,
        new_values=new_data
    )

    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user data (admin only). Password is optional."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    old_data = {"name": user.name, "email": user.email, "role": user.role}
    has_changes = False

    if body.name is not None and body.name != user.name:
        user.name = body.name
        has_changes = True
    if body.email is not None and body.email != user.email:
        # Check for duplicate email
        dup_result = await db.execute(select(User).where(User.email == body.email))
        if dup_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            )
        user.email = body.email
        has_changes = True
    if body.role is not None and body.role != user.role:
        user.role = body.role
        has_changes = True
    if body.password is not None:
        user.password_hash = hash_password(body.password)
        has_changes = True

    await db.flush()
    await db.refresh(user)
    await db.commit()

    if has_changes:
        new_data = {"name": user.name, "email": user.email, "role": user.role}
        if body.password is not None:
            new_data["password_changed"] = True
            
        AuditService.log_action(
            background_tasks=background_tasks,
            get_db_session_factory=async_session,
            user_id=admin.id,
            user_email=admin.email,
            entity_type="USER",
            entity_id=user.id,
            action_type=ActionType.UPDATE,
            old_values=old_data,
            new_values=new_data
        )

    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only). Cannot delete self."""
    if admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar seu próprio usuário",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    old_data = {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role}

    await db.delete(user)
    await db.commit()

    AuditService.log_action(
        background_tasks=background_tasks,
        get_db_session_factory=async_session,
        user_id=admin.id,
        user_email=admin.email,
        entity_type="USER",
        entity_id=old_data["id"],
        action_type=ActionType.DELETE,
        old_values=old_data
    )
