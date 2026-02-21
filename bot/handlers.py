from datetime import datetime
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# Импорты для работы с Кинопоиском
from bot.kinopoisk import (
    POSTER_PLACEHOLDER_URL,
    build_movie_caption,
    get_movie,
    get_random_title,
    navigate_info_movie,
    send_movie_card_with_nav,
)
from bot.logger import logger
from bot.services.api_client import api_client

router = Router()


# Состояния
class AddMovieState(StatesGroup):
    waiting_for_title = State()


class InfoMovieState(StatesGroup):
    waiting_for_title = State()
    viewing = State()


class RandomMovieState(StatesGroup):
    viewing = State()


# === КЛАВИАТУРЫ ===
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Список")],
        [KeyboardButton(text="ℹ️ Инфо"), KeyboardButton(text="🎭 Жанры")],
        [KeyboardButton(text="🎲 Случайный"), KeyboardButton(text="❓ Помощь")],
        [KeyboardButton(text="😊 Обо мне")],
    ],
    resize_keyboard=True,
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Список")],
        [KeyboardButton(text="ℹ️ Инфо"), KeyboardButton(text="🎭 Жанры")],
        [KeyboardButton(text="🎲 Случайный"), KeyboardButton(text="❓ Помощь")],
        [KeyboardButton(text="👥 Пользователи")],
    ],
    resize_keyboard=True,
)


# === КОМАНДА СТАРТ ===
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Основная команда старта"""
    user_id = message.from_user.id
    username = message.from_user.username or "друг"

    logger.info(f"Команда /start от пользователя: {user_id} (@{username})")

    # 1. Сначала пробуем получить пользователя (если он уже есть)
    try:
        user = await api_client.get_current_user(user_id)
        if user and user.get("is_active"):
            # Пользователь уже есть и активен
            if user.get("is_admin"):
                await message.answer(
                    f"Привет, админ {username}! 👑\n\n"
                    f"Добро пожаловать в систему управления фильмами.",
                    reply_markup=admin_kb,
                )
            else:
                await message.answer(
                    f"Привет, {username}! 👋\n\n"
                    f"Добро пожаловать в систему управления фильмами.",
                    reply_markup=main_kb,
                )
            return
    except Exception as e:
        # 401 - пользователь не найден, продолжаем
        if "401" not in str(e):
            logger.error(f"Ошибка проверки пользователя: {e}")

    # 2. Проверяем, был ли уже выполнен setup
    try:
        setup_status = await api_client.check_setup_status()
        is_first = not setup_status.get("setup_completed", True)
    except Exception as e:
        logger.error(f"Ошибка проверки статуса setup: {e}")
        is_first = False

    # 3. Если это первый пользователь - регистрируем через setup endpoint
    if is_first:
        try:
            user_data = {
                "telegram_id": user_id,
                "username": username,
                "is_admin": True,  # Первый пользователь - админ
            }

            user = await api_client.setup_first_user(user_data)
            logger.info(f"✅ Первый пользователь создан через /auth/setup: {user_id}")

            await message.answer(
                f"🎉 Вы первый пользователь! Вы зарегистрированы как АДМИНИСТРАТОР!\n\n"
                f"Telegram ID: {user['telegram_id']}\n"
                f"Username: @{user.get('username') or '—'}\n\n"
                f"Теперь вы можете:\n"
                f"• Добавлять других пользователей командой /add_user\n"
                f"• Управлять списком фильмов\n"
                f"• Просматривать всех пользователей\n\n"
                f"Напишите /start ещё раз для продолжения",
                reply_markup=admin_kb,
            )
        except Exception as e:
            logger.error(f"Ошибка регистрации первого пользователя: {e}")
            await message.answer("❌ Ошибка при регистрации. Попробуйте позже.")
    else:
        # 4. Не первый пользователь - проверяем, зарегистрирован ли он
        try:
            user = await api_client.get_current_user(user_id)
            if user:
                # Пользователь есть, но не активен
                await message.answer(
                    f"Привет, {username}! 👋\n\n"
                    f"Ваш Telegram ID: {user_id}\n\n"
                    "⛔ Ваш аккаунт ещё не активирован администратором.\n\n"
                    "Ожидайте активации или свяжитесь с администратором."
                )
            else:
                # Пользователя нет в системе
                await message.answer(
                    f"Привет, {username}! 👋\n\n"
                    f"Ваш Telegram ID: {user_id}\n\n"
                    "⛔ Это приватный бот для ограниченного круга лиц.\n\n"
                    "Что делать:\n"
                    "1. Отправьте свой ID администратору\n"
                    "2. Администратор добавит вас в систему командой /add_user\n"
                    "3. После этого напишите /start снова"
                )
        except Exception:
            # Пользователь не найден
            await message.answer(
                f"Привет, {username}! 👋\n\n"
                f"Ваш Telegram ID: {user_id}\n\n"
                "⛔ Это приватный бот для ограниченного круга лиц.\n\n"
                "Что делать:\n"
                "1. Отправьте свой ID администратору\n"
                "2. Администратор добавит вас в систему командой /add_user\n"
                "3. После этого напишите /start снова"
            )


# === АДМИН КОМАНДЫ ===
@router.message(F.text == "👥 Пользователи")
async def cmd_list_users(message: Message):
    """Список всех пользователей (только для админа)"""
    try:
        users = await api_client.get_users(message.from_user.id)

        if not users:
            await message.answer("📭 В системе нет пользователей")
            return

        text_lines = ["📋 Список пользователей:\n"]
        for i, user in enumerate(users, 1):
            status = "👑 АДМИН" if user.get("is_admin") else "👤 ПОЛЬЗОВАТЕЛЬ"
            active = "✅" if user.get("is_active") else "❌"
            username = user.get("username") or "—"
            text_lines.append(
                f"{i}. {active} {status}\n"
                f"   ID: {user['telegram_id']}\n"
                f"   Username: @{username}\n"
            )

        await message.answer("\n".join(text_lines))
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        await message.answer("❌ Ошибка при получении списка пользователей")


@router.message(Command("add_user"))
async def cmd_add_user(message: Message):
    """Добавить пользователя в систему (только для админа)"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            raise ValueError("Не указан ID пользователя")

        new_user_id = int(parts[1])
        username = parts[2] if len(parts) > 2 else None

        user_data = {
            "telegram_id": new_user_id,
            "username": username,
            "is_admin": False,
        }

        # Создаём пользователя
        await api_client.create_user(message.from_user.id, user_data)

        # Сразу активируем
        await api_client.activate_user(message.from_user.id, new_user_id)

        await message.answer(
            f"✅ Пользователь {new_user_id} успешно добавлен и активирован!\n"
            f"Username: @{username or '—'}"
        )

    except ValueError:
        await message.answer(
            "❌ Неверный формат команды\n\n"
            "Использование:\n"
            "<code>/add_user 123456789</code>\n"
            "или\n"
            "<code>/add_user 123456789 username</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        if "уже существует" in str(e).lower():
            await message.answer("⚠️ Пользователь уже существует")
        else:
            logger.error(f"Ошибка добавления пользователя: {e}")
            await message.answer("❌ Ошибка при добавлении пользователя")


# === ИНФОРМАЦИЯ О СЕБЕ ===
@router.message(F.text == "😊 Обо мне")
@router.message(Command("me"))
async def cmd_myinfo(message: Message):
    """Информация о текущем пользователе"""
    try:
        user = await api_client.get_current_user(message.from_user.id)
        if not user:
            await message.answer("❌ Вы не авторизованы. Напишите /start")
            return

        status = "👑 АДМИН" if user.get("is_admin") else "👤 ПОЛЬЗОВАТЕЛЬ"
        active = "✅ Активен" if user.get("is_active") else "❌ Не активен"
        username = user.get("username") or "—"

        # Форматируем дату если есть
        created_at = ""
        if user.get("created_at"):
            try:
                dt = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
                created_at = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, KeyError, TypeError):
                created_at = str(user["created_at"])

        text = (
            f"📋 Ваши данные:\n\n"
            f"Telegram ID: <code>{user['telegram_id']}</code>\n"
            f"Username: @{username}\n"
            f"Роль: {status}\n"
            f"Статус: {active}\n"
            f"Дата регистрации: {created_at}"
        )

        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка получения информации: {e}")
        await message.answer("❌ Ошибка получения информации")


# === ОСНОВНЫЕ КОМАНДЫ ===
@router.message(Command("genre"))
async def cmd_update_genres(message: Message):
    """Ручное обновление жанров из Кинопоиска"""
    try:
        result = await api_client.sync_genres(message.from_user.id)
        await message.answer(f"✅ {result.get('message', 'Жанры обновлены!')}")
    except Exception as e:
        logger.error(f"Ошибка синхронизации жанров: {e}")
        await message.answer(
            "❌ Не удалось обновить жанры. Возможно, у вас нет прав администратора."
        )


@router.message(Command("types"))
async def cmd_update_types(message: Message):
    """Ручное обновление типов из Кинопоиска"""
    try:
        result = await api_client.sync_types(message.from_user.id)
        await message.answer(f"✅ {result.get('message', 'Типы обновлены!')}")
    except Exception as e:
        logger.error(f"Ошибка синхронизации типов: {e}")
        await message.answer(
            "❌ Не удалось обновить типы. Возможно, у вас нет прав администратора."
        )


# === ОБРАБОТЧИКИ КНОПОК ===
@router.message(F.text == "➕ Добавить")
async def handle_add_button(message: Message, state: FSMContext):
    await message.answer("Введите название фильма или сериала:")
    await state.set_state(AddMovieState.waiting_for_title)


@router.message(F.text == "ℹ️ Инфо")
async def handle_info_button(message: Message, state: FSMContext):
    await message.answer("Введите название фильма из вашего списка:")
    await state.set_state(InfoMovieState.waiting_for_title)


@router.message(F.text == "📋 Список")
async def handle_list_button(message: Message):
    """Показать список всех фильмов"""
    try:
        movies = await api_client.get_movies(message.from_user.id)
        if not movies:
            await message.answer("Ваш список пуст.")
            return

        lines = []
        for movie in movies:
            icon = "🎬" if movie.get("type") == "movie" else "📺"
            status = "✅" if movie.get("watched") else ""
            line = f"{icon} {movie['title']} {status}"
            if movie.get("year"):
                line += f" ({movie['year']})"
            lines.append(line)

        await message.answer("\n".join(lines))
    except Exception as e:
        logger.error(f"Ошибка при получении списка: {e}")
        await message.answer("❌ Не удалось получить список фильмов")


@router.message(F.text == "🎭 Жанры")
async def handle_genres_button(message: Message):
    """Показать кнопки с жанрами (автоматическая загрузка если нет)"""
    try:
        # Используем ensure_genres - загрузит автоматически если надо
        genres = await api_client.ensure_genres(message.from_user.id)

        if not genres:
            await message.answer("❌ Не удалось загрузить жанры. Попробуйте позже.")
            return

        # Создаём кнопки с жанрами
        buttons = []
        row = []
        for genre in genres:
            row.append(
                InlineKeyboardButton(text=genre, callback_data=f"filter_genre_{genre}")
            )
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        await message.answer(
            "Выберите жанр:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки жанров: {e}")
        await message.answer("❌ Не удалось загрузить жанры.")


@router.message(F.text == "🎲 Случайный")
async def handle_random_button(message: Message):
    """Выбор случайного фильма (автоматическая загрузка типов если нет)"""
    try:
        # Используем ensure_types - загрузит автоматически если надо
        types = await api_client.ensure_types(message.from_user.id)

        if not types:
            await message.answer("❌ Не удалось загрузить типы. Попробуйте позже.")
            return

        # Создаём кнопки
        buttons = []
        row = []
        for t in types:
            row.append(InlineKeyboardButton(text=t, callback_data=f"random_type_{t}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        await message.answer(
            "Выберите тип:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки типов: {e}")
        await message.answer("❌ Не удалось загрузить типы.")


@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    try:
        user = await api_client.get_current_user(message.from_user.id)

        if not user:
            await message.answer("❌ Вы не авторизованы. Напишите /start")
            return

        if user.get("is_admin"):
            text = (
                "👑 <b>Администраторские команды:</b>\n"
                "• /add_user [ID] [username] - добавить пользователя\n"
                "• /users - список всех пользователей\n"
                "• /me - информация о себе\n\n"
                "🎬 <b>Основные команды:</b>\n"
                "• ➕ Добавить - найти и сохранить фильм\n"
                "• 📋 Список - показать все фильмы\n"
                "• ℹ️ Инфо - подробности о фильме\n"
                "• 🎭 Жанры - фильтровать по жанрам\n"
                "• 🎲 Случайный - случайный фильм\n\n"
                "<i>Используйте кнопки или команды!</i>"
            )
        else:
            text = (
                "👤 <b>Основные команды:</b>\n"
                "• ➕ Добавить - найти и сохранить фильм\n"
                "• 📋 Список - показать все фильмы\n"
                "• ℹ️ Инфо - подробности о фильме\n"
                "• 🎭 Жанры - фильтровать по жанрам\n"
                "• 🎲 Случайный - случайный фильм\n"
                "• 😊 Обо мне - ваши данные\n\n"
                "<i>Используйте кнопки для удобства!</i>"
            )

        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка в справке: {e}")
        await message.answer("❌ Ошибка загрузки справки")


# === FSM: ДОБАВЛЕНИЕ ФИЛЬМА ===
@router.message(AddMovieState.waiting_for_title)
async def process_add_title(message: Message, state: FSMContext):
    """Обработка ввода названия фильма для добавления"""
    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return

    # Ищем на Кинопоиске
    movie_data = await get_movie(title)
    if not movie_data:
        await message.answer("Фильм не найден. Попробуйте другое название.")
        await state.clear()
        return

    # Сохраняем через API
    try:
        movie = await api_client.create_movie(message.from_user.id, movie_data)
        await message.answer(f"✅ «{movie['title']}» добавлен!")
    except Exception as e:
        if "уже существует" in str(e).lower():
            await message.answer(f"✅ «{movie_data['title']}» уже в списке!")
        else:
            logger.error(f"Ошибка сохранения фильма: {e}")
            await message.answer("❌ Ошибка при сохранении фильма")

    await state.clear()


# === FSM: ПОЛУЧЕНИЕ ИНФОРМАЦИИ ===
@router.message(InfoMovieState.waiting_for_title)
async def process_info_title(message: Message, state: FSMContext):
    """Обработка ввода названия фильма для просмотра информации"""
    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return

    try:
        # Получаем все фильмы
        movies = await api_client.get_movies(message.from_user.id)

        if not movies:
            await message.answer("Ваш список пуст.")
            await state.clear()
            return

        # Ищем фильм по названию
        target_movie = None
        target_index = None

        # Проходим по всему списку фильмов, сохраняем выбранный фильм
        # и его индекс в списке
        for i, movie in enumerate(movies):
            if movie["title"].lower() == title.lower():
                target_movie = movie
                target_index = i
                break

        if not target_movie:
            await message.answer("Фильм не найден в вашем списке.")
            await state.clear()
            return

        # Создаём временный объект для send_movie_card_with_nav
        from api.core.models import Movie

        temp_movie = Movie(
            id=target_movie["id"],
            title=target_movie["title"],
            year=target_movie.get("year"),
            type=target_movie.get("type", "movie"),
            description=target_movie.get("description"),
            poster_url=target_movie.get("poster_url"),
            rating=target_movie.get("rating"),
            genres=target_movie.get("genres", ""),
            watched=target_movie.get("watched", False),
        )

        movie_ids = [m["id"] for m in movies]
        await state.update_data(movie_ids=movie_ids, current_index=target_index)
        await send_movie_card_with_nav(message, temp_movie, target_index, len(movies))
        await state.set_state(InfoMovieState.viewing)

    except Exception as e:
        logger.error(f"Ошибка получения информации о фильме: {e}")
        await message.answer("❌ Ошибка при получении информации о фильме")
        await state.clear()


# === ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК ===
@router.callback_query(F.data.startswith("mark_watched_"))
async def mark_watched(callback: CallbackQuery):
    """Отметить фильм как просмотренный"""
    movie_id = int(callback.data.split("_")[2])

    try:
        await api_client.update_movie(
            callback.from_user.id, movie_id, {"watched": True}
        )
        await callback.answer("✅ Отмечено!")

        if callback.message.caption:
            new_caption = callback.message.caption + "\n\n✅ Просмотрено!"
            await callback.message.edit_caption(
                caption=new_caption, reply_markup=callback.message.reply_markup
            )
    except Exception as e:
        logger.error(f"Ошибка отметки просмотра: {e}")
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("delete_movie_"))
async def delete_movie(callback: CallbackQuery):
    """Удалить фильм"""
    movie_id = int(callback.data.split("_")[2])

    try:
        await api_client.delete_movie(callback.from_user.id, movie_id)
        await callback.answer("🗑️ Удалено")
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Ошибка удаления фильма: {e}")
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data == "info_nav_prev", InfoMovieState.viewing)
async def info_nav_prev(callback: CallbackQuery, state: FSMContext):
    await navigate_info_movie(callback, state, direction=-1)


@router.callback_query(F.data == "info_nav_next", InfoMovieState.viewing)
async def info_nav_next(callback: CallbackQuery, state: FSMContext):
    await navigate_info_movie(callback, state, direction=1)


@router.callback_query(F.data == "info_close", InfoMovieState.viewing)
async def info_close(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("filter_genre_"))
async def filter_by_genre(callback: CallbackQuery):
    """Фильтрация фильмов по жанру"""
    genre_name = callback.data[len("filter_genre_") :]

    try:
        movies = await api_client.filter_by_genre(callback.from_user.id, genre_name)

        if not movies:
            await callback.message.answer(
                f"Фильмов жанра «{genre_name}» нет в вашем списке."
            )
        else:
            lines = []
            for movie in movies:
                icon = "🎬" if movie.get("type") == "movie" else "📺"
                status = "✅" if movie.get("watched") else ""
                line = f"{icon} {movie['title']} {status}"
                if movie.get("year"):
                    line += f" ({movie['year']})"
                lines.append(line)

            await callback.message.answer("\n".join(lines))
    except Exception as e:
        logger.error(f"Ошибка фильтрации: {e}")
        await callback.message.answer("❌ Ошибка при фильтрации")

    await callback.answer()


@router.callback_query(F.data.startswith("random_type_"))
async def random_select_genre(callback: CallbackQuery, state: FSMContext):
    """Выбор жанра для случайного фильма"""
    type_name = callback.data.split("_", 2)[2]
    await state.update_data(selected_type=type_name)

    try:
        # Используем ensure_genres - загрузит автоматически если надо
        genres = await api_client.ensure_genres(callback.from_user.id)

        if not genres:
            await callback.message.edit_text("❌ Не удалось загрузить жанры.")
            await callback.answer()
            return

        # Создаём кнопки
        buttons = []
        row = []
        for genre in genres:
            row.append(
                InlineKeyboardButton(text=genre, callback_data=f"random_genre_{genre}")
            )
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        await callback.message.edit_text(
            "Выберите жанр:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки жанров: {e}")
        await callback.message.edit_text("❌ Ошибка загрузки жанров")

    await callback.answer()


@router.callback_query(F.data.startswith("random_genre_"))
async def show_random_movie(callback: CallbackQuery, state: FSMContext):
    """Показать случайный фильм"""
    genre_name = callback.data.split("_", 2)[2]
    data = await state.get_data()
    type_name = data.get("selected_type")

    if not type_name:
        await callback.answer("Ошибка: тип не выбран.")
        return

    # Получаем случайный фильм с Кинопоиска
    movie_data = await get_random_title(type_name, genre_name)
    if not movie_data:
        await callback.message.edit_text(
            "Не удалось найти случайный фильм. Попробуйте другой жанр."
        )
        await state.clear()
        return

    # Создаём временный объект для caption
    from api.core.models import Movie

    temp_movie = Movie(
        title=movie_data.get("title", ""),
        year=movie_data.get("year"),
        kp_id=movie_data.get("kp_id"),
        type=movie_data.get("type", "movie"),
        description=movie_data.get("description"),
        poster_url=movie_data.get("poster_url"),
        rating=movie_data.get("rating"),
        genres=movie_data.get("genres", ""),
    )

    caption = build_movie_caption(temp_movie)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить",
                    callback_data=f"add_random_{movie_data['kp_id']}",
                )
            ]
        ]
    )

    poster_to_use = movie_data.get("poster_url") or POSTER_PLACEHOLDER_URL

    try:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=poster_to_use,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.edit_text(
            caption, reply_markup=keyboard, parse_mode="HTML"
        )

    await state.update_data(random_movie=movie_data)
    await state.set_state(RandomMovieState.viewing)
    await callback.answer()


@router.callback_query(F.data.startswith("add_random_"), RandomMovieState.viewing)
async def add_random_movie(callback: CallbackQuery, state: FSMContext):
    """Добавить случайный фильм в список"""
    data = await state.get_data()
    movie_data = data.get("random_movie")

    if not movie_data:
        await callback.answer("Ошибка: данные фильма утеряны.")
        return

    try:
        movie = await api_client.create_movie(callback.from_user.id, movie_data)
        await callback.answer(f"✅ «{movie['title']}» добавлен!")
    except Exception as e:
        if "уже существует" in str(e).lower():
            await callback.answer(f"✅ «{movie_data['title']}» уже в списке!")
        else:
            logger.error(f"Ошибка добавления случайного фильма: {e}")
            await callback.answer("❌ Ошибка при добавлении")

    await state.clear()


# === ЗАЩИТА ОТ НЕИЗВЕСТНЫХ СООБЩЕНИЙ ===
@router.message(F.text)
async def fallback_handler(message: Message):
    await message.answer("Неизвестная команда. Используйте кнопки.")
