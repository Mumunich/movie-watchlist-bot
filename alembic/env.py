import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# Добавляем путь к проекту
# указываем что смотреть нужно не только в текущей папке, но и на уровень выше.
# Без этого Alembic не найдёт папку Api
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Загружаем переменные окружения
load_dotenv()

# Получаем URL из .env и меняем asyncpg на psycopg2 (синхронный драйвер)
# Alembic синхронный, но по другому не работает
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("asyncpg", "psycopg2")

# Импортируем модели ПОСЛЕ загрузки .env,
# python регистрирует модели таблиц внутри объекта Base.metadata
from api.core.models import Base  # noqa: E402

# это конфигурационный объект Alembic
config = context.config

# Переопределяем sqlalchemy.url
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# передаем Алембику список всех своих «чертежей»
target_metadata = Base.metadata


# Вне докера запускается этот режим
def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    # Alembic берет соединение с базой и список чертежей,
    # он сравнивает их и выполняет нужные действия
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# в Docker запускается именно этот режим
def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Alembic берет соединение с базой и список чертежей,
    # он сравнивает их и выполняет нужные действия
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
