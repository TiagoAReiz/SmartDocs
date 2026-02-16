from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User | None:
    """Authenticate a user by email and password."""
    email_value = email.lower()
    result = await db.execute(select(User).where(func.lower(User.email) == email_value))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        return None

    return user


async def create_user(
    name: str,
    email: str,
    password: str,
    role: str,
    db: AsyncSession,
) -> User:
    """Create a new user with hashed password."""
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def generate_token(user: User) -> str:
    """Generate a JWT token for a user."""
    return create_access_token(user.id, user.email, user.role)
