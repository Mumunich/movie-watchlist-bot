import allure
import pytest
from httpx import AsyncClient


@allure.title("Получение списка пользователей, когда их нет")
@allure.description(
    "GET /users/ должен вернуть пустой массив, если в БД нет пользователей."
)
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_get_users_empty(client: AsyncClient):
    """Тест получения списка пользователей, когда их нет"""
    with allure.step("Отправить GET-запрос к /users/"):
        response = await client.get("/users/")

    with allure.step("Проверить статус ответа (200 OK)"):
        assert response.status_code == 200

    with allure.step("Проверить, что тело ответа — пустой список"):
        assert response.json() == []


@allure.title("Создание обычного пользователя (админом)")
@allure.description("POST /users/ должен создать неактивного пользователя (не админа).")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """Тест создания пользователя (админ создаёт обычного)"""
    user_data = {"telegram_id": 123456, "username": "new_user", "is_admin": False}

    with allure.step(
        f"Отправить POST-запрос на создание пользователя "
        f"с ID {user_data['telegram_id']}"
    ):
        response = await client.post("/users/", json=user_data)

    with allure.step("Проверить статус ответа (201 Created)"):
        assert response.status_code == 201

    with allure.step("Проверить поля созданного пользователя"):
        data = response.json()
        assert data["telegram_id"] == 123456
        assert data["is_active"] is False  # обычный пользователь неактивен
        assert data["is_admin"] is False


@allure.title("Создание пользователя с уже существующим telegram_id")
@allure.description(
    "Попытка создать пользователя с существующим ID должна вернуть ошибку 400."
)
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_create_user_duplicate(client: AsyncClient):
    """Тест создания пользователя с уже существующим telegram_id"""
    user_data = {"telegram_id": 123456, "username": "new_user", "is_admin": False}

    with allure.step("Создать пользователя первый раз"):
        await client.post("/users/", json=user_data)

    with allure.step("Попытаться создать пользователя с тем же ID повторно"):
        response = await client.post("/users/", json=user_data)

    with allure.step("Проверить статус ответа (400 Bad Request)"):
        assert response.status_code == 400

    with allure.step("Проверить сообщение об ошибке"):
        assert "уже существует" in response.json()["detail"]


@allure.title("Получение информации о текущем пользователе")
@allure.description(
    "GET /users/me должен вернуть данные тестового пользователя (админа)."
)
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """Тест получения информации о текущем пользователе"""
    with allure.step("Отправить GET-запрос к /users/me"):
        response = await client.get("/users/me")

    with allure.step("Проверить статус ответа (200 OK)"):
        assert response.status_code == 200

    with allure.step(
        "Проверить данные пользователя (из фикстуры override_get_current_user)"
    ):
        data = response.json()
        assert data["telegram_id"] == 12345  # из фикстуры
        assert data["username"] == "test_admin"
        assert data["is_admin"] is True
