from collections.abc import AsyncGenerator
from datetime import UTC, datetime
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from api.core.models import Base, User
from api.dependencies import get_current_user, get_db
from api.main import app

# Тестовая база данных (SQLite в памяти)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
async def engine():
    """Создаём движок для тестовой БД и инициализируем таблицы"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Утилизируем движок
    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Сессия БД для каждого теста (автоматический откат)"""
    # Открываем соединение на уровне фикстуры
    async with engine.connect() as connection:
        # Начинаем внешнюю транзакцию
        transaction = await connection.begin()
        # Создаём сессию, связанную с этим соединением
        async_session = AsyncSession(bind=connection, expire_on_commit=False)

        yield async_session

        # После теста откатываем транзакцию — все изменения в БД исчезают
        await async_session.close()
        await transaction.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Асинхронный HTTP-клиент для тестирования API.
    Переопределяем зависимости get_db и get_current_user.
    """

    # Функция, которая будет подставлена вместо get_db
    async def override_get_db():
        yield db_session

    # Функция, которая будет подставлена вместо get_current_user
    async def override_get_current_user():
        # Возвращаем тестового пользователя (админа)
        return User(
            id=1,
            telegram_id=12345,
            username="test_admin",
            is_admin=True,
            is_active=True,
            created_at=datetime.now(UTC),
        )

    # Подменяем зависимости в приложении
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Создаём и вызываем клиент для отправки запросов в API
    # При передаче параметр app=app в AsyncClient,
    # библиотека httpx переключается в специальный режим
    # вместо реальных сетевых запросов она создаёт ASGI-сообщения
    # и вызывает FastAPI напрямую
    # Всё происходит в памяти, клиент не отправляет реальные HTTP-запросы по сети
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # После тестов очищаем подмены
    app.dependency_overrides.clear()
