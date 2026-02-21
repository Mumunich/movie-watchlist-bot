import os
import httpx
from bot.logger import logger


class APIClient:
    def __init__(self):
        # Берём URL из окружения, дефолт для Docker
        self.base_url = os.getenv("API_URL", "http://api:8000")
        self.timeout = 30.0
        logger.info(f"API Client инициализирован с base_url: {self.base_url}")

    async def _request(
        self, method: str, endpoint: str, user_id: int, json: dict | None = None
    ) -> dict | None:
        """Базовый метод для запросов к API"""
        url = f"{self.base_url}{endpoint}"
        headers = {"X-API-Key": str(user_id)}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method, url=url, headers=headers, json=json
                )
                response.raise_for_status()
                return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Ошибка запроса: {e}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка: {e}")
            raise

    # ===== Фильмы =====
    async def get_movies(self, user_id: int) -> list[dict]:
        """Получить все фильмы"""
        result = await self._request("GET", "/movies/", user_id)
        return result or []

    async def get_movie(self, user_id: int, movie_id: int) -> dict | None:
        """Получить фильм по ID"""
        return await self._request("GET", f"/movies/{movie_id}", user_id)

    async def create_movie(self, user_id: int, movie_data: dict) -> dict:
        """Создать фильм"""
        return await self._request("POST", "/movies/", user_id, json=movie_data)

    async def update_movie(
        self, user_id: int, movie_id: int, update_data: dict
    ) -> dict:
        """Обновить фильм"""
        return await self._request(
            "PATCH", f"/movies/{movie_id}", user_id, json=update_data
        )

    async def delete_movie(self, user_id: int, movie_id: int) -> None:
        """Удалить фильм"""
        await self._request("DELETE", f"/movies/{movie_id}", user_id)

    async def filter_by_genre(self, user_id: int, genre: str) -> list[dict]:
        """Фильтрация фильмов по жанру"""
        result = await self._request("GET", f"/movies/filter/?genre={genre}", user_id)
        return result or []

    async def search_movies(self, user_id: int, query: str) -> list[dict]:
        """Поиск фильмов по названию"""
        result = await self._request("GET", f"/movies/search/?q={query}", user_id)
        return result or []

    async def get_genres(self, user_id: int) -> list[str]:
        """Получить список всех жанров"""
        result = await self._request("GET", "/movies/genres/", user_id)
        return result or []

    async def get_types(self, user_id: int) -> list[str]:
        """Получить список всех типов"""
        result = await self._request("GET", "/movies/types/", user_id)
        return result or []

    # ===== Пользователи =====
    async def get_users(self, user_id: int) -> list[dict]:
        """Получить всех пользователей (только админ)"""
        result = await self._request("GET", "/users/", user_id)
        return result or []

    async def get_current_user(self, user_id: int) -> dict | None:
        """Получить информацию о текущем пользователе"""
        try:
            return await self._request("GET", "/users/me", user_id)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return None
            raise

    async def create_user(self, user_id: int, user_data: dict) -> dict:
        """Создать пользователя (только админ)"""
        return await self._request("POST", "/users/", user_id, json=user_data)

    async def activate_user(self, admin_id: int, target_user_id: int) -> dict:
        """Активировать пользователя (только админ)"""
        return await self._request(
            "POST", f"/users/{target_user_id}/activate", admin_id
        )

        # ===== Аутентификация и setup =====

    async def setup_first_user(self, user_data: dict) -> dict:
        """
        Зарегистрировать первого пользователя (админа).
        Доступно БЕЗ авторизации, работает только один раз.
        """
        url = f"{self.base_url}/auth/setup"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url=url, json=user_data)
            response.raise_for_status()
            return response.json()

    async def check_setup_status(self) -> dict:
        """Проверить, был ли уже выполнен setup"""
        url = f"{self.base_url}/auth/setup/status"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def sync_genres(self, user_id: int) -> dict:
        """Синхронизировать жанры с Кинопоиском (только админ)"""
        return await self._request("POST", "/movies/sync/genres", user_id)

    async def sync_types(self, user_id: int) -> dict:
        """Синхронизировать типы с Кинопоиском (только админ)"""
        return await self._request("POST", "/movies/sync/types", user_id)

    async def ensure_genres(self, user_id: int) -> list[str]:
        """
        Получить жанры. Если их нет - автоматически загрузить с Кинопоиска.
        """
        try:
            # Пробуем получить жанры
            genres = await self.get_genres(user_id)
            if genres:
                return genres

            # Жанров нет - синхронизируем
            logger.info("Жанры не найдены, автоматическая синхронизация...")
            await self.sync_genres(user_id)

            # Возвращаем загруженные жанры
            return await self.get_genres(user_id)
        except Exception as e:
            logger.error(f"Ошибка при загрузке жанров: {e}")
            return []

    async def ensure_types(self, user_id: int) -> list[str]:
        """
        Получить типы. Если их нет - автоматически загрузить с Кинопоиска.
        """
        try:
            # Пробуем получить типы
            types = await self.get_types(user_id)
            if types:
                return types

            # Типов нет - синхронизируем
            logger.info("Типы не найдены, автоматическая синхронизация...")
            await self.sync_types(user_id)

            # Возвращаем загруженные типы
            return await self.get_types(user_id)
        except Exception as e:
            logger.error(f"Ошибка при загрузке типов: {e}")
            return []


# Создаём глобальный экземпляр клиента
api_client = APIClient()
