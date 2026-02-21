import allure
import pytest
from httpx import AsyncClient


@allure.title("Регистрация первого пользователя")
@allure.description("POST /auth/setup должен создать админа и вернуть его данные.")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_setup_first_user(client: AsyncClient):
    """Тест регистрации первого пользователя"""
    user_data = {
        "telegram_id": 999,
        "username": "first_user",
        "is_admin": False,  # но setup сделает его админом
    }

    with allure.step("Отправить POST-запрос на /auth/setup"):
        response = await client.post("/auth/setup", json=user_data)

    with allure.step("Проверить статус ответа (200 OK)"):
        assert response.status_code == 200

    with allure.step("Проверить, что пользователь создан как админ и активирован"):
        data = response.json()
        assert data["telegram_id"] == 999
        assert data["is_admin"] is True
        assert data["is_active"] is True


@allure.title("Повторная регистрация после первого пользователя")
@allure.description(
    "POST /auth/setup должен вернуть 403, если пользователи уже существуют."
)
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_setup_second_user_fails(client: AsyncClient):
    """Тест, что второй раз setup не работает"""
    # Сначала создаём первого
    user_data1 = {"telegram_id": 999, "username": "first_user", "is_admin": False}
    with allure.step("Создать первого пользователя"):
        await client.post("/auth/setup", json=user_data1)

    # Пытаемся ещё раз
    user_data2 = {"telegram_id": 1000, "username": "second_user", "is_admin": False}
    with allure.step("Попытаться создать второго пользователя через тот же эндпоинт"):
        response = await client.post("/auth/setup", json=user_data2)

    with allure.step("Проверить статус ответа (403 Forbidden)"):
        assert response.status_code == 403

    with allure.step("Проверить сообщение об ошибке"):
        assert "Setup mode is disabled" in response.json()["detail"]


@allure.title("Проверка статуса setup до регистрации")
@allure.description("GET /auth/setup/status должен показывать, что setup не выполнен.")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_setup_status_before(client: AsyncClient):
    """Тест проверки статуса setup до создания пользователя"""
    with allure.step("Отправить GET-запрос к /auth/setup/status"):
        response = await client.get("/auth/setup/status")

    with allure.step("Проверить статус ответа (200 OK)"):
        assert response.status_code == 200

    with allure.step("Проверить, что setup не завершён и пользователей нет"):
        data = response.json()
        assert data["setup_completed"] is False
        assert data["users_count"] == 0


@allure.title("Проверка статуса setup после регистрации")
@allure.description("GET /auth/setup/status должен показывать, что setup выполнен.")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_setup_status_after(client: AsyncClient):
    """Тест проверки статуса setup после создания пользователя"""
    # Создаём пользователя
    user_data = {"telegram_id": 999, "username": "first_user", "is_admin": False}
    with allure.step("Создать первого пользователя через /auth/setup"):
        await client.post("/auth/setup", json=user_data)

    with allure.step("Отправить GET-запрос к /auth/setup/status"):
        response = await client.get("/auth/setup/status")

    with allure.step("Проверить статус ответа (200 OK)"):
        assert response.status_code == 200

    with allure.step("Проверить, что setup завершён и есть пользователи"):
        data = response.json()
        assert data["setup_completed"] is True
        assert data["users_count"] >= 1
