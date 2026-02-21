from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.models import User
from api.dependencies import get_db
from api.schemas import UserCreate, UserSchema

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/setup", response_model=UserSchema)
async def setup_first_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Регистрация ПЕРВОГО пользователя (администратора).
    Этот endpoint доступен БЕЗ авторизации и работает ТОЛЬКО один раз!
    """
    # Проверяем, есть ли вообще пользователи в системе
    result = await db.execute(select(User))
    existing_users = result.scalars().all()

    if existing_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup mode is disabled - users already exist",
        )

    # Проверяем, нет ли уже такого пользователя
    existing = await db.execute(
        select(User).where(User.telegram_id == user_data.telegram_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )

    # Создаём админа
    user = User(
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        is_admin=True,  # Первый пользователь - всегда админ!
        is_active=True,
        created_at=datetime.now(UTC),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.get("/setup/status")
async def check_setup_status(db: AsyncSession = Depends(get_db)):
    """Проверить, был ли уже выполнен setup"""
    result = await db.execute(select(User))
    users = result.scalars().all()

    return {"setup_completed": len(users) > 0, "users_count": len(users)}
