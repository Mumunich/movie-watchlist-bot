from datetime import UTC, datetime
from unittest.mock import AsyncMock
import allure
import pytest
from aiogram.types import Message
from aiogram.types import User as TgUser
from httpx import ASGITransport, AsyncClient
from api.core.models import User
from api.dependencies import get_current_user, get_db
from api.main import app
from bot.handlers import handle_list_button
from bot.services.api_client import api_client


@pytest.fixture
async def test_api_client(db_session):
    """Клиент для интеграционных тестов с подменой зависимостей."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return User(
            id=1,
            telegram_id=12345,
            username="test_admin",
            is_admin=True,
            is_active=True,
            created_at=datetime.now(UTC),
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Создаём реальный HTTP-клиент к тестовому API напрямую в памяти
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Подменяем base_url у api_client, чтобы он ходил в тестовый API
        original_base_url = api_client.base_url
        api_client.base_url = "http://test"
        yield client
        api_client.base_url = original_base_url

    app.dependency_overrides.clear()


@pytest.mark.skip(
    reason="Требуется доработка: api_client должен использовать тестовый клиент"
)
@allure.title(
    "Интеграционный тест: бот запрашивает список фильмов после создания через API"
)
@allure.description("""
    Проверяет цепочку:
    1. Создаём фильм через API.
    2. Вызываем хендлер бота handle_list_button.
    3. Бот через api_client обращается к тестовому API.
    4. Проверяем, что бот отправил сообщение с названием фильма.
""")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_integration_list_movies(test_api_client):
    """Интеграционный тест получения списка фильмов."""
    # Сначала создадим фильм через API
    movie_data = {
        "title": "Тестовый фильм",
        "year": 2023,
        "type": "movie",
        "genres": "тест",
        "kp_id": 999999,
        "rating": 5.0,
        "watched": False,
        "poster_url": None,
    }

    with allure.step("Создать тестовый фильм через API"):
        resp = await test_api_client.post("/movies/", json=movie_data)
        assert resp.status_code == 200, "Не удалось создать фильм через API"

    # Теперь вызываем хендлер бота
    message = AsyncMock(spec=Message)
    message.from_user = TgUser(id=12345, is_bot=False, first_name="Test")
    message.answer = AsyncMock()

    with allure.step(
        "Вызвать хендлер handle_list_button "
        "(бот запросит список фильмов через api_client)"
    ):
        await handle_list_button(message)

    with allure.step("Проверить, что бот отправил сообщение с названием фильма"):
        message.answer.assert_called_once()
        args, kwargs = message.answer.call_args
        assert "Тестовый фильм" in args[0], f"Бот не упомянул фильм, ответ: {args[0]}"
