from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from api.database import AsyncSessionLocal
from api.models import Movie, Genre, Types, User
from datetime import datetime, timezone

from bot.middleware import AccessMiddleware
# Импорты
from bot.services.movie_service import movie_service
from bot.kinopoisk import (
    get_movie, send_movie_card_with_nav, fetch_genres_from_kinopoisk,
    navigate_info_movie, fetch_types_from_kinopoisk, get_random_title,
    POSTER_PLACEHOLDER_URL, build_movie_caption, edit_movie_card
)
from bot.logger import logger

router = Router()

# Вспомогательная функция
def dict_to_movie_obj(data: dict) -> Movie:
    """Создаёт временный объект Movie из словаря"""
    return Movie(
        title=data.get("title", ""),
        year=data.get("year"),
        kp_id=data.get("kp_id"),
        type=data.get("type", "movie"),
        description=data.get("description"),
        poster_url=data.get("poster_url"),
        rating=data.get("rating"),
        genres=data.get("genres", "")
    )


# Состояния
class AddMovieState(StatesGroup):
    waiting_for_title = State()


class InfoMovieState(StatesGroup):
    waiting_for_title = State()
    viewing = State()


class RandomMovieState(StatesGroup):
    viewing = State()


# === ГЛАВНАЯ КЛАВИАТУРА (для авторизованных) ===
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Список")],
        [KeyboardButton(text="ℹ️ Инфо"), KeyboardButton(text="🎭 Жанры")],
        [KeyboardButton(text="🎲 Случайный"), KeyboardButton(text="❓ Помощь")],
        [KeyboardButton(text="😊 Обо мне")]
    ],
    resize_keyboard=True
)

# === АДМИН КЛАВИАТУРА ===
admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Список")],
        [KeyboardButton(text="ℹ️ Инфо"), KeyboardButton(text="🎭 Жанры")],
        [KeyboardButton(text="🎲 Случайный"), KeyboardButton(text="❓ Помощь")],
        [KeyboardButton(text="👥 Пользователи")]
    ],
    resize_keyboard=True
)


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
async def get_user_by_id(user_id: int) -> User | None:
    """Получаем пользователя по telegram_id"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        return result.scalar_one_or_none()


async def is_first_user() -> bool:
    """Проверяем, есть ли пользователи в системе"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return len(users) == 0


# === ОСНОВНЫЕ КОМАНДЫ ===
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Основная команда старта"""
    user_id = message.from_user.id
    username = message.from_user.username or "друг"

    logger.info(f"Команда /start от пользователя: {user_id} (@{username})")

    # Проверяем, есть ли пользователь в системе
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()

    if user and user.is_active:
        # Пользователь уже есть - показываем приветствие
        # ✅ ВАЖНО: Добавляем пользователя в data для middleware!
        from aiogram.types import Update
        # Нужно получить доступ к data из контекста
        # Лучший способ: использовать dependency injection

        if user.is_admin:
            await message.answer(
                f"Привет, админ {username}! 👑\n\n"
                f"Добро пожаловать в систему управления фильмами.",
                reply_markup=admin_kb
            )
        else:
            await message.answer(
                f"Привет, {username}! 👋\n\n"
                f"Добро пожаловать в систему управления фильмами.",
                reply_markup=main_kb
            )
    else:
        # Пользователь не найден
        # Если это первый пользователь - автоматически делаем его админом
        if await is_first_user():
            # Автоматически регистрируем первого пользователя как админа
            logger.info(f"Первый пользователь! Регистрируем как админа: {user_id}")
            async with AsyncSessionLocal() as session:
                new_admin = User(
                    telegram_id=user_id,
                    username=username,
                    is_admin=True,
                    is_active=True,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(new_admin)
                await session.commit()

            await message.answer(
                f"🎉 Вы первый пользователь! Автоматически зарегистрированы как АДМИНИСТРАТОР!\n\n"
                f"Telegram ID: {user_id}\n"
                f"Username: @{username or '—'}\n\n"
                f"Теперь вы можете:\n"
                f"• Добавлять других пользователей командой /add_user\n"
                f"• Управлять списком фильмов\n"
                f"• Просматривать всех пользователей\n\n"
                f"Напишите /start ещё раз для продолжения",
                reply_markup=admin_kb
            )
        else:
            # Не первый пользователь и не зарегистрирован
            logger.warning(f"Неавторизованный доступ: {user_id}")
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
@router.message(Command("users"))
async def cmd_list_users(message: Message):
    """Список всех пользователей (только для админа)"""
    user = await get_user_by_id(message.from_user.id)

    if not user or not user.is_admin:
        logger.warning(f"Попытка просмотра списка пользователей без прав: {message.from_user.id}")
        await message.answer("⛔ Только администратор может просматривать пользователей")
        return

    # Получаем всех пользователей
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = result.scalars().all()

    if not users:
        await message.answer("📭 В системе нет пользователей")
        return

    # Формируем сообщение
    text_lines = ["📋 Список пользователей:\n"]
    for i, user in enumerate(users, 1):
        status = "👑 АДМИН" if user.is_admin else "👤 ПОЛЬЗОВАТЕЛЬ"
        active = "✅" if user.is_active else "❌"
        date_str = user.created_at.strftime('%d.%m.%Y') if user.created_at else "—"
        text_lines.append(
            f"{i}. {active} {status}\n"
            f"   ID: {user.telegram_id}\n"
            f"   Username: @{user.username or '—'}\n"
            f"   Добавлен: {date_str}\n"
        )

    await message.answer("\n".join(text_lines))


@router.message(Command("add_user"))
async def cmd_add_user(message: Message):
    """Добавить пользователя в систему (только для админа)"""
    admin_user = await get_user_by_id(message.from_user.id)

    if not admin_user or not admin_user.is_admin:
        logger.warning(f"Попытка добавления пользователя без прав: {message.from_user.id}")
        await message.answer("⛔ Только администратор может добавлять пользователей")
        return

    # Парсим команду: /add_user 123456789 @username
    try:
        parts = message.text.split()
        if len(parts) < 2:
            raise ValueError

        new_user_id = int(parts[1])
        username = parts[2] if len(parts) > 2 else None

        logger.info(f"Попытка добавления пользователя: ID={new_user_id}, username={username}")

        # Проверяем, нет ли уже такого пользователя
        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                select(User).where(User.telegram_id == new_user_id)
            )
            if existing.scalar_one_or_none():
                logger.warning(f"Пользователь {new_user_id} уже существует")
                await message.answer(f"⚠️ Пользователь {new_user_id} уже существует")
                return

            # Добавляем нового пользователя (обычный пользователь, не админ)
            new_user = User(
                telegram_id=new_user_id,
                username=username,
                is_admin=False,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_user)
            await session.commit()

        logger.info(f"Пользователь {new_user_id} успешно добавлен")
        await message.answer(
            f"✅ Пользователь успешно добавлен!\n\n"
            f"Telegram ID: {new_user_id}\n"
            f"Username: @{username or '—'}\n\n"
            f"Теперь этот пользователь может написать /start и пользоваться ботом."
        )

    except (IndexError, ValueError):
        logger.error(f"Ошибка формата команды: {message.text}")
        await message.answer(
            "❌ Неверный формат команды\n\n"
            "Использование:\n"
            "<code>/add_user 123456789</code>\n"
            "или\n"
            "<code>/add_user 123456789 username</code>\n\n"
            "Пример:\n"
            "<code>/add_user 987654321</code>\n"
            "<code>/add_user 987654321 username</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при добавлении пользователя: {e}")


# === ИНФОРМАЦИЯ О СЕБЕ (доступна всем авторизованным) ===
@router.message(F.text == "😊 Обо мне")
@router.message(Command("me"))
async def cmd_myinfo(message: Message):
    """Информация о текущем пользователе"""
    user = await get_user_by_id(message.from_user.id)

    if not user:
        await message.answer("❌ Вы не авторизованы в системе. Напишите /start")
        return

    status = "👑 АДМИН" if user.is_admin else "👤 ПОЛЬЗОВАТЕЛЬ"
    active = "✅ Активен" if user.is_active else "❌ Не активен"
    date_str = user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else "—"

    text = (
        f"📋 Ваши данные:\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username or '—'}\n"
        f"Роль: {status}\n"
        f"Статус: {active}\n"
        f"Дата добавления: {date_str}"
    )

    if user.is_admin:
        text += "\n\n👑 Администраторские функции:\n"
        text += "• /add_user - добавить пользователя\n"
        text += "• /users - список всех пользователей"

    await message.answer(text, parse_mode="HTML")


# ============== ОСНОВНЫЕ КОМАНДЫ БОТА ==============
@router.message(Command("genre"))
async def cmd_update_genres(message: Message):
    success = await movie_service.sync_genres(fetch_genres_from_kinopoisk)
    if success:
        await message.answer("✅ Жанры обновлены!")
    else:
        await message.answer("❌ Не удалось получить жанры.")


@router.message(Command("types"))
async def cmd_update_types(message: Message):
    success = await movie_service.sync_types(fetch_types_from_kinopoisk)
    if success:
        await message.answer("✅ Типы обновлены!")
    else:
        await message.answer("❌ Не удалось получить типы.")


# Обработчики кнопок
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
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie).order_by(Movie.watched, Movie.title))
        movies = result.scalars().all()

    if not movies:
        await message.answer("Ваш список пуст.")
        return

    lines = []
    for movie in movies:
        icon = "🎬" if movie.type == "movie" else "📺"
        status = "✅" if movie.watched else ""
        line = f"{icon} {movie.title} {status}"
        if movie.year:
            line += f" ({movie.year})"
        lines.append(line)

    await message.answer("\n".join(lines))


@router.message(F.text == "🎭 Жанры")
async def handle_genres_button(message: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Genre).order_by(Genre.name))
        genres = result.scalars().all()

    if not genres:
        success = await movie_service.sync_genres(fetch_genres_from_kinopoisk)
        if not success:
            logger.error(f"Ошибка загрузки жанров", exc_info=True)
            await message.answer("❌ Не удалось загрузить жанры.")
            return

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Genre).order_by(Genre.name))
            genres = result.scalars().all()

    buttons = []
    row = []
    for genre in genres:
        row.append(InlineKeyboardButton(text=genre.name, callback_data=f"filter_genre_{genre.name}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await message.answer("Выберите жанр:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.message(F.text == "🎲 Случайный")
async def handle_random_button(message: Message, state: FSMContext):  # ← ДОБАВЛЕН state
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Types).order_by(Types.name))
        types = result.scalars().all()

    if not types:
        success = await movie_service.sync_types(fetch_types_from_kinopoisk)
        if not success:
            logger.error(f"Ошибка загрузки типов", exc_info=True)
            await message.answer("❌ Не удалось загрузить типы.")
            return

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Types).order_by(Types.name))
            types = result.scalars().all()

    buttons = []
    row = []
    for t in types:
        row.append(InlineKeyboardButton(text=t.name, callback_data=f"random_type_{t.name}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await message.answer("Выберите тип:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    user = await get_user_by_id(message.from_user.id)

    if not user:
        logger.warning(f"Попытка нажатия на кнопку помощь, без авторизации")
        await message.answer("❌ Вы не авторизованы. Напишите /start")
        return

    if user.is_admin:
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


# FSM: Добавление фильма
@router.message(AddMovieState.waiting_for_title)
async def process_add_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return

    movie_data = await get_movie(title)
    if not movie_data:
        await message.answer("Фильм не найден. Попробуйте другое название.")
        await state.clear()
        return

    movie, is_new = await movie_service.save_movie_to_db(movie_data)

    if is_new:
        await message.answer(f"✅ «{movie.title}» добавлен!")
    else:
        await message.answer(f"✅ «{movie.title}» уже в списке!")

    await state.clear()


# FSM: Получение информации
@router.message(InfoMovieState.waiting_for_title)
async def process_info_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie).order_by(Movie.watched, Movie.title))
        all_movies = result.scalars().all()

        target_movie = None
        target_index = None
        for i, movie in enumerate(all_movies):
            if movie.title == title:
                target_movie = movie
                target_index = i
                break

    if not target_movie:
        await message.answer("Фильм не найден в вашем списке.")
        await state.clear()
        return

    movie_ids = [m.id for m in all_movies]
    await state.update_data(movie_ids=movie_ids, current_index=target_index)
    await send_movie_card_with_nav(message, target_movie, target_index, len(all_movies))
    await state.set_state(InfoMovieState.viewing)


# Обработчики инлайн-кнопок
@router.callback_query(F.data.startswith("mark_watched_"))
async def mark_watched(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as session:
        movie = await session.get(Movie, movie_id)
        if movie and not movie.watched:
            movie.watched = True
            await session.commit()
            await callback.answer("✅ Отмечено!")
            new_caption = callback.message.caption + "\n\n✅ Просмотрено!"
            await callback.message.edit_caption(caption=new_caption, reply_markup=None)
        elif movie:
            await callback.answer("Уже просмотрено.")
        else:
            await callback.answer("Фильм не найден.")


@router.callback_query(F.data.startswith("delete_movie_"))
async def delete_movie(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as session:
        movie = await session.get(Movie, movie_id)
        if movie:
            await session.delete(movie)
            await session.commit()
            await callback.answer("🗑️ Удалено")
            await callback.message.delete()
        else:
            await callback.answer("Фильм уже удалён.")


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
    genre_name = callback.data[len("filter_genre_"):]

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie).where(Movie.genres.ilike(f"%{genre_name}%")))
        movies = result.scalars().all()

    if not movies:
        await callback.answer()
        await callback.message.answer(f"Фильмов жанра «{genre_name}» нет в вашем списке.")
    else:
        lines = []
        for movie in movies:
            icon = "🎬" if movie.type == "movie" else "📺"
            status = "✅" if movie.watched else ""
            line = f"{icon} {movie.title} {status}"
            if movie.year:
                line += f" ({movie.year})"
            lines.append(line)

        await callback.answer()
        await callback.message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("random_type_"))
async def random_select_genre(callback: CallbackQuery, state: FSMContext):
    type_name = callback.data.split("_", 2)[2]

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Genre).order_by(Genre.name))
        genres = result.scalars().all()

    if not genres:
        success = await movie_service.sync_genres(fetch_genres_from_kinopoisk)
        if not success:
            logger.error(f"Ошибка загрузки жанров в функции random_select_genre", exc_info=True)
            await callback.answer("❌ Не удалось загрузить жанры.")
            return

        # После синхронизации заново получаем жанры из БД
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Genre).order_by(Genre.name))
            genres = result.scalars().all()

    await state.update_data(selected_type=type_name)

    buttons = []
    row = []
    for g in genres:
        row.append(InlineKeyboardButton(text=g.name, callback_data=f"random_genre_{g.name}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await callback.message.edit_text("Выберите жанр:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("random_genre_"))
async def show_random_movie(callback: CallbackQuery, state: FSMContext):
    genre_name = callback.data.split("_", 2)[2]
    data = await state.get_data()
    type_name = data.get("selected_type")

    if not type_name:
        await callback.answer("Ошибка: тип не выбран.")
        return

    movie_data = await get_random_title(type_name, genre_name)
    if not movie_data:
        await callback.message.edit_text("Не удалось найти случайный фильм. Попробуйте другой жанр.")
        await state.clear()
        return

    temp_movie_obj = dict_to_movie_obj(movie_data)
    caption = build_movie_caption(temp_movie_obj)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data=f"add_random_{movie_data['kp_id']}")]
    ])

    poster_to_use = movie_data.get("poster_url") or POSTER_PLACEHOLDER_URL

    try:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=poster_to_use,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except:
        await callback.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")

    await state.update_data(random_movie=movie_data)
    await state.set_state(RandomMovieState.viewing)
    await callback.answer()


@router.callback_query(F.data.startswith("add_random_"), RandomMovieState.viewing)
async def add_random_movie(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    movie_data = data.get("random_movie")

    if not movie_data:
        await callback.answer("Ошибка: данные фильма утеряны.")
        return

    movie, is_new = await movie_service.save_movie_to_db(movie_data)

    if is_new:
        await callback.answer(f"✅ «{movie.title}» добавлен!")
    else:
        await callback.answer(f"✅ «{movie.title}» уже в списке!")

    await state.clear()


# Защита от неизвестных сообщений
@router.message(F.text)
async def fallback_handler(message: Message):
    await message.answer("Неизвестная команда. Используйте кнопки.")