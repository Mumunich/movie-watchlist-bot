from sqlalchemy import delete, select
from api.core.database import AsyncSessionLocal
from api.core.models import Genre, Movie, Types
from bot.logger import logger


class MovieService:
    @staticmethod
    def parse_movie_data(data: dict) -> dict | None:
        """Парсинг данных фильма из API-ответа"""
        # Проверка на пустые данные
        if not data:
            logger.error("Данные для парсинга пусты")
            return None

        logger.info(
            f"📊 Парсинг данных, тип:{type(data).__name__}, "
            f"ключи:{list(data.keys())[:5] if isinstance(data, dict) else 'не словарь'}"
        )

        if isinstance(data, dict):
            if "docs" in data and isinstance(data["docs"], list):
                if not data["docs"]:
                    logger.debug("Список в docs пустой")
                    return None
                movie = data["docs"][0]
                logger.info("Формат /search, извлекаем первый фильм")
            else:
                # Формат /random — сам объект фильма
                movie = data
                logger.info("Формат /random, используем как есть")
        else:
            logger.error(f"Ожидается словарь, получено: {type(data)}")
            return None

        logger.info(
            f"Обрабатываем фильм: {movie.get('name', 'Без названия')} "
            f"(id={movie.get('id')})"
        )

        # Извлечение данных
        title = movie.get("name") or movie.get("alternativeName") or "Без названия"
        year = movie.get("year")
        kp_id = movie.get("id")
        type_ = movie.get("type", "movie")

        # Обработка описания
        description = movie.get("description")
        if description:
            description = description.replace("\xa0", " ")
            if len(description) > 900:
                description = description[:900] + "..."

        # Постер
        poster_url = None
        poster = movie.get("poster")
        if poster:
            poster_url = poster.get("url", "").strip()

        # Рейтинг
        rating = None
        rating_data = movie.get("rating")
        if rating_data:
            rating = rating_data.get("kp")

        # Жанры
        genres_list = []
        for g in movie.get("genres", []):
            genre_name = g.get("name", "")
            if genre_name:
                genres_list.append(genre_name)
        genres_str = ", ".join(genres_list)

        result = {
            "title": title,
            "year": year,
            "kp_id": kp_id,
            "type": type_,
            "description": description,
            "poster_url": poster_url,
            "rating": rating,
            "genres": genres_str,
        }

        logger.info(f"Парсинг завершен: {title}")
        return result

    @staticmethod
    async def save_movie_to_db(movie_data: dict) -> tuple[Movie, bool]:
        """Сохранение фильма в БД (возвращает фильм и флаг is_new)"""
        if not movie_data:
            logger.error("Нет данных фильма для сохранения")
            raise ValueError("Нет данных фильма для сохранения")

        async with AsyncSessionLocal() as session:
            # Проверяем что фильм уже есть в БД
            existing = await session.execute(
                select(Movie).where(Movie.kp_id == movie_data["kp_id"])
            )
            existing_movie = existing.scalar_one_or_none()

            if existing_movie:
                return existing_movie, False

            new_movie = Movie(
                title=movie_data["title"],
                year=movie_data["year"],
                kp_id=movie_data["kp_id"],
                type=movie_data["type"],
                description=movie_data["description"],
                poster_url=movie_data["poster_url"],
                rating=movie_data["rating"],
                genres=movie_data["genres"],
            )
            session.add(new_movie)
            await session.commit()
            await session.refresh(new_movie)

            return new_movie, True

    @staticmethod
    async def sync_genres(kinopoisk_fetch_func) -> bool:
        """Синхронизация жанров"""
        try:
            logger.info("Начинаю синхронизацию жанров...")
            genres_data = await kinopoisk_fetch_func()
            if not genres_data:
                logger.error("Не удалось получить данные жанров")
                return False

            logger.info(f"Получено {len(genres_data)} жанров")

            async with AsyncSessionLocal() as session:
                # Очищаем старые жанры
                await session.execute(delete(Genre))
                logger.info("Старые жанры удалены")

                # Добавляем новые
                for g in genres_data:
                    genre = Genre(name=g["name"], slug=g["slug"])
                    session.add(genre)
                await session.commit()

                logger.info("Жанры сохранены в БД")
            return True
        except Exception as e:
            logger.error(f"Ошибка при синхронизации жанров: {e}")
            return False

    @staticmethod
    async def sync_types(kinopoisk_fetch_func) -> bool:
        """Синхронизация типов"""
        try:
            logger.info("Начинаю синхронизацию типов...")
            types_data = await kinopoisk_fetch_func()
            if not types_data:
                logger.error("Не удалось получить данные типов")
                return False

            logger.info(f"Получено {len(types_data)} типов")

            async with AsyncSessionLocal() as session:
                # Очищаем старые типы
                await session.execute(delete(Types))
                logger.info("Старые типы удалены")

                # Добавляем новые
                for t in types_data:
                    type_obj = Types(name=t["name"], slug=t["slug"])
                    session.add(type_obj)
                await session.commit()

                logger.info("Типы сохранены в БД")
            return True
        except Exception as e:
            logger.error(f"Ошибка при синхронизации типов: {e}")
            return False


movie_service = MovieService()
