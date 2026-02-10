from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from typing import Callable, Dict, Any, Awaitable
from api.database import AsyncSessionLocal
from api.models import User
from sqlalchemy import select

from bot.logger import logger


class AccessMiddleware(BaseMiddleware):
    """Middleware для проверки доступа пользователей"""

    async def __call__(
            self,
            handler: Callable,
            event: Update,
            data: Dict[str, Any]
    ) -> Any:

        # 1. Извлекаем пользователя из события
        if event.message:
            user = event.message.from_user
            event_type = "message"
            message_text = event.message.text or ""
        elif event.callback_query:
            user = event.callback_query.from_user
            event_type = "callback_query"
            message_text = ""
        else:
            # Пропускаем другие типы событий
            return await handler(event, data)

        user_id = user.id
        logger.debug(f"Middleware: проверка доступа для {user_id} ({event_type})")

        # 2. ИСКЛЮЧЕНИЕ: Пропускаем команду /start без проверки
        if event.message and message_text.strip() == "/start":
            logger.info(f"Пропускаем проверку для /start от {user_id}")
            return await handler(event, data)

        # 3. ИСКЛЮЧЕНИЕ: Пропускаем команду /start с параметрами
        if event.message and message_text.strip().startswith("/start "):
            logger.info(f"Пропускаем проверку для /start с параметрами от {user_id}")
            return await handler(event, data)

        # 4. Проверяем пользователя в БД
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(
                    User.telegram_id == user_id,
                    User.is_active == True
                )
            )
            db_user = result.scalar_one_or_none()

        # 5. Если не найден - блокируем
        if not db_user:
            logger.warning(f"Доступ запрещён для {user_id}")

            if event.message:
                await event.message.answer(
                    "⛔ Доступ запрещён!\n\n"
                    f"Ваш Telegram ID: {user_id}\n\n"
                    "Это приватный бот для ограниченного круга лиц.\n"
                    "Свяжитесь с администратором для получения доступа."
                )
            elif event.callback_query:
                await event.callback_query.answer(
                    "⛔ Доступ запрещён! Свяжитесь с администратором",
                    show_alert=True
                )

            return None

        # 6. Добавляем данные пользователя
        data["user_id"] = user_id
        data["user"] = db_user
        logger.debug(f"Доступ разрешён для {user_id}")

        # 7. Продолжаем обработку
        return await handler(event, data)