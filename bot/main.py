import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from bot.handlers import router
from bot.logger import logger
from bot.middleware import AccessMiddleware

# Заполняем токен из окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.critical("TELEGRAM_BOT_TOKEN не найден в .env")

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
# Включаем middleware
dp.update.middleware(AccessMiddleware())


async def main():
    logger.info("=" * 50)
    logger.info("Запуск Movie Bot")
    logger.info("=" * 50)
    # Включаем роутер
    dp.include_router(router)
    # запускаем постоянный опрос событий
    logger.info("Бот инициализирован, запускаю поллинг...")
    await dp.start_polling(bot)


# стандартный запуск асинхронной программы
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
