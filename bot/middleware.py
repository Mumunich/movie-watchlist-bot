from collections.abc import Callable
from typing import Any
from aiogram import BaseMiddleware
from aiogram.types import Update
from bot.logger import logger
from bot.services.api_client import api_client


class AccessMiddleware(BaseMiddleware):
    """Middleware для проверки доступа пользователей через API"""

    async def __call__(
        self, handler: Callable, event: Update, data: dict[str, Any]
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
            return await handler(event, data)

        user_id = user.id
        logger.debug(f"Middleware: проверка доступа для {user_id} ({event_type})")

        # 2. ИСКЛЮЧЕНИЕ: Пропускаем команду /start и /auth/*
        if event.message:
            if message_text.strip() == "/start" or message_text.strip().startswith(
                "/start "
            ):
                logger.info(f"Пропускаем проверку для /start от {user_id}")
                return await handler(event, data)

            if message_text.strip() == "/auth" or message_text.strip().startswith(
                "/auth"
            ):
                logger.info(f"Пропускаем проверку для auth от {user_id}")
                return await handler(event, data)

        # 3. Проверяем пользователя через API
        try:
            db_user = await api_client.get_current_user(user_id)

            if not db_user:
                logger.warning(f"Пользователь {user_id} не найден в системе")

                if event.message:
                    await event.message.answer(
                        "⛔ Доступ запрещён!\n\n"
                        f"Ваш Telegram ID: {user_id}\n\n"
                        "Это приватный бот для ограниченного круга лиц.\n"
                        "Если вы первый пользователь,"
                        " напишите /start для регистрации.\n"
                        "Иначе свяжитесь с администратором."
                    )
                elif event.callback_query:
                    await event.callback_query.answer(
                        "⛔ Доступ запрещён! Свяжитесь с администратором",
                        show_alert=True,
                    )

                return None

            if not db_user.get("is_active"):
                logger.warning(f"Пользователь {user_id} не активирован")

                if event.message:
                    await event.message.answer(
                        "⛔ Ваш аккаунт ещё не активирован!\n\n"
                        "Ожидайте активации администратором."
                    )
                elif event.callback_query:
                    await event.callback_query.answer(
                        "⛔ Аккаунт не активирован", show_alert=True
                    )

                return None

            # 4. Пользователь найден и активен - добавляем в data
            data["user_id"] = user_id
            data["user"] = db_user
            logger.debug(f"Доступ разрешён для {user_id}")

        except Exception as e:
            logger.error(f"Ошибка при проверке пользователя {user_id}: {e}")
            # В случае ошибки API блокировать
            if event.message:
                await event.message.answer("❌ Ошибка сервера. Попробуйте позже.")
            return None

        # 5. Продолжаем обработку
        return await handler(event, data)
