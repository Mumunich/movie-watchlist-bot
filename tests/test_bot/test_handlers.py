from unittest.mock import AsyncMock, patch
import allure
import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import User as TgUser
from bot.handlers import cmd_start, handle_add_button, handle_list_button
from bot.services.api_client import api_client


# Фикстуры остаются без изменений
@pytest.fixture
def mock_message():
    # Создаём мок, который имитирует объект Message из aiogram.
    # Параметр spec указывает, что мок должен иметь все методы и атрибуты класса Message
    message = AsyncMock(spec=Message)
    message.from_user = TgUser(id=12345, is_bot=False, first_name="Test")
    message.text = "/start"
    # подменяем метод answer на мок, чтобы потом проверить, был ли он вызван
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    # По умолчанию .get_data вернёт пустой словарь
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


@allure.title("/start для первого пользователя")
@allure.description("При первом запуске бота должен создаться админ через API.")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.asyncio
async def test_cmd_start_first_user(mock_message):
    """Тест команды /start для первого пользователя"""
    with allure.step("Настроить моки API: пользователь не найден, setup не завершён"):
        # Подменяем в api_client, функцию get_current_user на новый AsyncMock
        # который при вызове вернёт None
        # и в остальных функциях по аналогии
        with (
            patch.object(
                api_client, "get_current_user", new=AsyncMock(return_value=None)
            ),
            patch.object(
                api_client,
                "check_setup_status",
                new=AsyncMock(return_value={"setup_completed": False}),
            ),
            patch.object(
                api_client,
                "setup_first_user",
                new=AsyncMock(
                    return_value={
                        "telegram_id": 12345,
                        "username": "Test",
                        "is_admin": True,
                    }
                ),
            ),
        ):
            with allure.step("Вызвать хендлер cmd_start"):
                await cmd_start(mock_message)

    with allure.step(
        "Проверить, что бот отправил сообщение о регистрации первого пользователя"
    ):
        # Проверяем, что ответ был отправлен и что mock_message.answer был вызван
        mock_message.answer.assert_called_once()
        # Получаем все аргументы с которыми был вызван answer
        # включая текст и всё остальное
        args, kwargs = mock_message.answer.call_args
        assert "первый пользователь" in args[0].lower()


@allure.title("/start для существующего активного пользователя")
@allure.description("Если пользователь уже есть в системе, бот показывает приветствие.")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_cmd_start_existing_user(mock_message, mock_state):
    """Тест команды /start для существующего пользователя"""
    existing_user = {
        "telegram_id": 12345,
        "username": "Test",
        "is_admin": False,
        "is_active": True,
    }

    with allure.step(
        "Настроить мок API: get_current_user возвращает существующего пользователя"
    ):
        with patch.object(
            api_client, "get_current_user", new=AsyncMock(return_value=existing_user)
        ):
            with allure.step("Вызвать хендлер cmd_start"):
                await cmd_start(mock_message)

    with allure.step("Проверить, что бот отправил приветствие"):
        mock_message.answer.assert_called_once()
        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        assert "Добро пожаловать" in args[0]


@allure.title("📋 Список фильмов — непустой список")
@allure.description("При наличии фильмов бот выводит их с эмодзи и статусом просмотра.")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_handle_list_button_with_movies(mock_message):
    """Тест кнопки 📋 Список с фильмами"""
    movies = [
        {"title": "Матрица", "type": "movie", "watched": False, "year": 1999},
        {"title": "Сериал", "type": "tv-series", "watched": True, "year": 2020},
    ]

    with allure.step("Настроить мок API: get_movies возвращает список фильмов"):
        with patch.object(api_client, "get_movies", new=AsyncMock(return_value=movies)):
            with allure.step("Вызвать хендлер handle_list_button"):
                await handle_list_button(mock_message)

    with allure.step(
        "Проверить, что бот отправил сообщение с правильным форматированием"
    ):
        mock_message.answer.assert_called_once()
        args, kwargs = mock_message.answer.call_args
        assert "🎬 Матрица" in args[0]
        assert "📺 Сериал ✅" in args[0]


@allure.title("📋 Список фильмов — пустой список")
@allure.description("Если фильмов нет, бот сообщает об этом.")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.asyncio
async def test_handle_list_button_empty(mock_message):
    """Тест кнопки 📋 Список, когда список пуст"""
    with allure.step("Настроить мок API: get_movies возвращает пустой список"):
        with patch.object(api_client, "get_movies", new=AsyncMock(return_value=[])):
            with allure.step("Вызвать хендлер handle_list_button"):
                await handle_list_button(mock_message)

    with allure.step("Проверить, что бот отправил сообщение о пустом списке"):
        mock_message.answer.assert_called_once_with("Ваш список пуст.")


@allure.title("➕ Добавить — переход в состояние ожидания названия")
@allure.description(
    "При нажатии кнопки бот запрашивает название "
    "и переводит FSM в состояние waiting_for_title."
)
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.asyncio
async def test_handle_add_button(mock_message, mock_state):
    """Тест кнопки ➕ Добавить"""
    with allure.step("Вызвать хендлер handle_add_button"):
        await handle_add_button(mock_message, mock_state)

    with allure.step("Проверить, что бот отправил запрос названия"):
        mock_message.answer.assert_called_once_with(
            "Введите название фильма или сериала:"
        )

    with allure.step("Проверить, что состояние FSM установлено в waiting_for_title"):
        mock_state.set_state.assert_called_once()
