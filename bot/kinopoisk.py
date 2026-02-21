import os

import httpx
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from dotenv import load_dotenv

from api.core.models import Movie
from bot.logger import logger
from bot.services.api_client import api_client

# Импортируем общий сервис
from bot.services.movie_service import movie_service

load_dotenv()
KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")
BASE_URL = os.getenv("KINOPOISK_API_URL")
ALT_API_URL = os.getenv("KINOPOISK_ALT_API_URL")
POSTER_PLACEHOLDER_URL = os.getenv("POSTER_PLACEHOLDER_URL")


async def get_movie(title: str) -> dict | None:
    """Получает список фильмов по названию из Кинопоиска"""
    params = {"query": title, "limit": 3}
    headers = {"X-API-KEY": KINOPOISK_API_KEY, "accept": "application/json"}

    logger.info(f"Поиск фильма:: {title}")
    logger.info(f"URL: {BASE_URL}movie/search")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}movie/search", headers=headers, params=params
            )
            logger.info(f"Ответ от Кинопоиска (фильм): статус {response.status_code}")
            response.raise_for_status()

            data = response.json()
            logger.info(f"Получен ответ, ключи: {list(data.keys())}")

            parsed = movie_service.parse_movie_data(data)
            logger.info(f"Парсинг завершен: {parsed is not None}")
            return parsed
        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка HTTP: {e.response.status_code} — {e.response.text}")
            return None
        except Exception as e:
            logger.error(
                f"Критическая ошибка при поиске фильма '{title}': {e}", exc_info=True
            )
            return None


async def fetch_genres_from_kinopoisk() -> list[dict] | None:
    """Получает список всех жанров из Кинопоиска"""
    headers = {"X-API-KEY": KINOPOISK_API_KEY, "accept": "application/json"}

    url = f"{ALT_API_URL}movie/possible-values-by-field?field=genres.name"
    logger.info(f"Запрос жанров из Кинопоиска по URL: {url}")

    timeout = httpx.Timeout(
        30.0, connect=10.0
    )  # ← 30 секунд на запрос, 10 на соединение

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, headers=headers)
            logger.info(f"Ответ от Кинопоиска (жанры): статус {response.status_code}")
            response.raise_for_status()

            data = response.json()
            logger.info(f"Получено жанров: {len(data) if data else 0}")
            return data
        except Exception as e:
            logger.error(f"Ошибка при получении жанров: {e}")
            return None


async def fetch_types_from_kinopoisk() -> list[dict] | None:
    """Получает список всех тип медиа-контента из Кинопоиска"""
    headers = {"X-API-KEY": KINOPOISK_API_KEY, "accept": "application/json"}

    url = f"{ALT_API_URL}movie/possible-values-by-field?field=type"
    logger.info(f"Запрос типов из Кинопоиска по URL: {url}")
    timeout = httpx.Timeout(
        30.0, connect=10.0
    )  # ← 30 секунд на запрос, 10 на соединение

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, headers=headers)
            logger.info(f"Ответ от Кинопоиска (типы): статус {response.status_code}")
            response.raise_for_status()

            data = response.json()
            logger.info(f"Получено типов: {len(data) if data else 0}")
            return data
        except Exception as e:
            logger.error(f"Ошибка при получении типов: {e}")
            return None


async def get_random_title(type_name: str, genre: str) -> dict | None:
    """Получает рандомный тайтл из Кинопоиска"""
    params = {
        "type": type_name,
        "genres.name": genre,
        "notNullFields": [
            "id",
            "name",
            "description",
            "type",
            "year",
            "rating.kp",
            "genres.name",
            "poster.url",
        ],
    }
    headers = {"X-API-KEY": KINOPOISK_API_KEY, "accept": "application/json"}

    logger.info(f"🎲 Поиск случайного фильма: тип={type_name}, жанр={genre}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{BASE_URL}movie/random", headers=headers, params=params
            )
            logger.info(f"Статус ответа random: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            logger.info(f"Получен случайный фильм: {data.get('name', 'Без названия')}")

            parsed = movie_service.parse_movie_data(data)
            return parsed

        except httpx.HTTPStatusError as e:
            logger.error(f"Ошибка HTTP: {e.response.status_code} — {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении рандомного тайтла: {e}")
            return None


async def send_movie_card_with_nav(
    message: Message, movie: Movie, index: int, total: int
) -> None:
    """Отправляет карточку фильма с постером и инлайн-кнопками"""
    caption = build_movie_caption(movie)

    # Кнопки навигации
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data="info_nav_prev"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data="info_nav_next"))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Просмотрено", callback_data=f"mark_watched_{movie.id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Удалить", callback_data=f"delete_movie_{movie.id}"
                ),
            ],
            nav_row,
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="info_close")],
        ]
    )

    poster_to_use = movie.poster_url or POSTER_PLACEHOLDER_URL
    try:
        await message.answer_photo(
            photo=poster_to_use,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке тайтла с навигацией: {e}")
        await message.answer(caption, reply_markup=keyboard, parse_mode="HTML")


async def navigate_info_movie(
    callback: CallbackQuery, state: FSMContext, direction: int
):
    """Навигация по карточкам фильмов через API"""
    data = await state.get_data()
    movie_ids = data["movie_ids"]
    current_index = data["current_index"]

    new_index = current_index + direction
    if new_index < 0 or new_index >= len(movie_ids):
        await callback.answer("Край списка.")
        return

    movie_id = movie_ids[new_index]

    # Получаем фильм через Api
    try:
        movie_data = await api_client.get_movie(callback.from_user.id, movie_id)
        if not movie_data:
            await callback.answer("Фильм удалён.")
            return

        # Создаём временный объект Movie для send_movie_card
        from api.core.models import Movie

        temp_movie = Movie(
            id=movie_data["id"],
            title=movie_data["title"],
            year=movie_data.get("year"),
            type=movie_data.get("type", "movie"),
            description=movie_data.get("description"),
            poster_url=movie_data.get("poster_url"),
            rating=movie_data.get("rating"),
            genres=movie_data.get("genres", ""),
            watched=movie_data.get("watched", False),
        )

        await state.update_data(current_index=new_index)
        await edit_movie_card(callback.message, temp_movie, new_index, len(movie_ids))
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка навигации: {e}")
        await callback.answer("❌ Ошибка загрузки фильма")


async def edit_movie_card(message: Message, movie: Movie, index: int, total: int):
    """Редактирует существующее сообщение с карточкой фильма"""
    caption = build_movie_caption(movie)

    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data="info_nav_prev"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data="info_nav_next"))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Просмотрено", callback_data=f"mark_watched_{movie.id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Удалить", callback_data=f"delete_movie_{movie.id}"
                ),
            ],
            nav_row,
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="info_close")],
        ]
    )

    poster_to_use = movie.poster_url or POSTER_PLACEHOLDER_URL
    try:
        media = InputMediaPhoto(media=poster_to_use, caption=caption, parse_mode="HTML")
        await message.edit_media(media=media, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при редактировании карточки тайтла с навигацией: {e}")
        await message.edit_caption(
            caption=caption, reply_markup=keyboard, parse_mode="HTML"
        )


def build_movie_caption(movie: Movie) -> str:
    """Формирует подпись к карточке фильма"""
    caption = f"🎬 <b>{movie.title}</b>\n"
    if movie.year:
        caption += f"Год: {movie.year}\n"
    if movie.genres:
        caption += f"Жанры: {movie.genres}\n"
    if movie.rating:
        caption += f"Рейтинг: {movie.rating}\n"
    if movie.description:
        if len(movie.description) > 500:
            caption += f"\n{movie.description[:500]}..."
        else:
            caption += f"\n{movie.description}"
    return caption
