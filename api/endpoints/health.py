from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db  # ← импортируем get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Проверка здоровья API и подключения к БД"""
    try:
        # Проверяем подключение к БД
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok",
        "service": "movie-bot-api",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
    }
