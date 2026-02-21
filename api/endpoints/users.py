from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.models import User
from api.dependencies import get_current_admin, get_current_user, get_db
from api.schemas import UserCreate, UserSchema

router = APIRouter()


@router.get("/", response_model=list[UserSchema])
async def get_users(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Получить всех пользователей (только для админов)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация"
        )

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может просматривать список пользователей",
        )

    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return users


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован"
        )
    return current_user


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать пользователя (доступно всем авторизованным).

    - **telegram_id**: ID пользователя в Telegram (обязательно)
    - **username**: Имя пользователя (опционально)
    - **is_admin**: true/false (только админы могут создавать админов)
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация"
        )

    # Только админ может создавать других админов
    if user_data.is_admin and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может создавать администраторов",
        )

    # Проверяем, нет ли уже пользователя
    existing = await db.execute(
        select(User).where(User.telegram_id == user_data.telegram_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким Telegram ID уже существует",
        )

    # Обычные пользователи создаются как is_active=False
    # Админы создаются как is_active=True (только если создаёт админ)
    user = User(
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        is_admin=user_data.is_admin,
        is_active=user_data.is_admin,  # Админы сразу активны
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{telegram_id}/activate")
async def activate_user(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Активировать пользователя (только админ)"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    if user.is_active:
        return {"message": f"Пользователь {telegram_id} уже активирован"}

    user.is_active = True
    await db.commit()

    return {"message": f"Пользователь {telegram_id} активирован"}


@router.post("/{telegram_id}/deactivate")
async def deactivate_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Деактивировать пользователя (только админ)"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя деактивировать самого себя",
        )

    user.is_active = False
    await db.commit()

    return {"message": f"Пользователь {telegram_id} деактивирован"}
