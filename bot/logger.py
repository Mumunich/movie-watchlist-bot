import logging
import sys
from pathlib import Path


def setup_logger(name: str = "movie_bot") -> logging.Logger:
    """
    Настройка логгера для проекта

    Уровни логирования:
    - DEBUG: отладочная информация (самый подробный)
    - INFO: обычные сообщения о работе
    - WARNING: предупреждения (что-то не так, но работает)
    - ERROR: ошибки (что-то сломалось)
    - CRITICAL: критичные ошибки (всё сломалось)
    """

    # Создаём логгер
    logger = logging.getLogger(name)

    # Устанавливаем уровень (DEBUG - самый подробный, можно поменять на INFO)
    logger.setLevel(logging.DEBUG)

    # Очищаем старые обработчики (если они есть)
    logger.handlers.clear()

    # Формат сообщений
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Вывод в консоль (StreamHandler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # В консоль только INFO и выше
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Вывод в файл (FileHandler)
    # Создаём папку logs если её нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Файл для всех логов
    file_handler = logging.FileHandler(logs_dir / "movie_bot.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # В файл пишем всё (DEBUG и выше)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Файл для ошибок (только ERROR и CRITICAL)
    error_handler = logging.FileHandler(logs_dir / "errors.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)  # Только ошибки
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    logger.info(f"Логгер '{name}' инициализирован")
    logger.info(f"Логи пишутся в папку: {logs_dir.absolute()}")

    return logger


# Создаём глобальный логгер
logger = setup_logger()
