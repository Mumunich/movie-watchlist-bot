from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.database import AsyncSessionLocal
from api.core.models import User

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    telegram_id: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Dependency для получения текущего пользователя по Telegram ID"""
    if not telegram_id:
        return None

    try:
        user_id = int(telegram_id)
    except ValueError:
        return None

    result = await db.execute(
        select(User).where(User.telegram_id == user_id, User.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_current_admin(user: User | None = Depends(get_current_user)) -> User:
    """Dependency для проверки, что пользователь - админ"""
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора",
        )
    return user
