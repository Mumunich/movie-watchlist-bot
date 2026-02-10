import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from api.models import Base
from bot.logger import logger

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def create_tables():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # Сначала УДАЛЯЕМ все таблицы
        await conn.run_sync(Base.metadata.drop_all)
        # Потом СОЗДАЁМ
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблицы успешно созданы!")

if __name__ == "__main__":
    asyncio.run(create_tables())

#Создаём таблицу в бд