from typing import Any
import allure
import pytest
from httpx import AsyncClient


@allure.feature("Movies")
@allure.story("List movies")
class TestMovieList:
    """Тестирование получения списка фильмов."""

    @allure.title("Получение списка фильмов, когда БД пуста")
    @allure.description(
        "Проверяем, что при отсутствии фильмов возвращается пустой массив."
    )
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.asyncio
    async def test_get_movies_empty(self, client: AsyncClient) -> None:
        """
        GET /movies/ ожидает пустой список.
        """
        with allure.step("Отправить GET-запрос к /movies/"):
            response = await client.get("/movies/")

        with allure.step("Проверить статус ответа"):
            assert response.status_code == 200

        with allure.step("Проверить тело ответа"):
            assert response.json() == []


@allure.feature("Movies")
@allure.story("Create movie")
class TestMovieCreate:
    """Тестирование создания фильмов."""

    @allure.title("Создание нового фильма")
    @allure.description("Проверяем успешное создание фильма с корректными данными.")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.asyncio
    async def test_create_movie(self, client: AsyncClient) -> None:
        """
        POST /movies/ должен создать фильм и вернуть его с id.
        """
        movie_data: dict[str, Any] = {
            "title": "Матрица",
            "year": 1999,
            "type": "movie",
            "genres": "фантастика, боевик",
            "kp_id": 301,
            "rating": 8.7,
            "watched": False,
            "poster_url": "https://example.com/poster.jpg",
        }

        with allure.step("Отправить POST-запрос на создание фильма"):
            response = await client.post("/movies/", json=movie_data)

        with allure.step("Проверить статус ответа (200 OK)"):
            assert response.status_code == 200

        with allure.step("Проверить, что фильм создан с правильными полями"):
            data = response.json()
            assert data["title"] == "Матрица"
            assert data["id"] is not None

        with allure.step("Проверить, что фильм действительно добавился в БД"):
            get_response = await client.get("/movies/")
            movies: list[dict] = get_response.json()
            assert len(movies) == 1

    @allure.title("Создание фильма с уже существующим kp_id")
    @allure.description("Должна вернуться ошибка 400.")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.asyncio
    async def test_create_movie_duplicate_kp_id(self, client: AsyncClient) -> None:
        """
        Попытка создать фильм с тем же kp_id должна завершиться ошибкой.
        """
        movie_data: dict[str, Any] = {
            "title": "Матрица",
            "year": 1999,
            "type": "movie",
            "genres": "фантастика, боевик",
            "kp_id": 301,
            "rating": 8.7,
            "watched": False,
            "poster_url": "https://example.com/poster.jpg",
        }

        with allure.step("Создать фильм первый раз"):
            await client.post("/movies/", json=movie_data)

        with allure.step("Попытаться создать ещё раз"):
            response = await client.post("/movies/", json=movie_data)

        with allure.step("Проверить статус 400 и сообщение об ошибке"):
            assert response.status_code == 400
            assert response.json()["detail"] == "Фильм уже существует"


@allure.feature("Movies")
@allure.story("Get movie by ID")
class TestMovieGet:
    """Тестирование получения фильма по ID."""

    @allure.title("Получение фильма по существующему ID")
    @allure.description("Должен вернуться корректный фильм.")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.asyncio
    async def test_get_movie_by_id(self, client: AsyncClient) -> None:
        """
        Сначала создаём фильм, потом получаем его по ID.
        """
        movie_data: dict[str, Any] = {
            "title": "Матрица",
            "year": 1999,
            "type": "movie",
            "genres": "фантастика, боевик",
            "kp_id": 301,
            "rating": 8.7,
            "watched": False,
            "poster_url": "https://example.com/poster.jpg",
        }

        with allure.step("Создать фильм"):
            create_resp = await client.post("/movies/", json=movie_data)
            movie_id = create_resp.json()["id"]

        with allure.step(f"Запросить фильм по ID {movie_id}"):
            response = await client.get(f"/movies/{movie_id}")

        with allure.step("Проверить статус и данные"):
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Матрица"
            assert data["id"] == movie_id


@allure.feature("Movies")
@allure.story("Update movie")
class TestMovieUpdate:
    """Тестирование обновления фильма."""

    @allure.title("Обновление фильма (отметка о просмотре)")
    @allure.description("PATCH /movies/{id} должен обновить поле watched.")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.asyncio
    async def test_update_movie_watched(self, client: AsyncClient) -> None:
        """
        Создаём фильм, затем отправляем PATCH с watched=true.
        """
        movie_data: dict[str, Any] = {
            "title": "Матрица",
            "year": 1999,
            "type": "movie",
            "genres": "фантастика, боевик",
            "kp_id": 301,
            "rating": 8.7,
            "watched": False,
            "poster_url": "https://example.com/poster.jpg",
        }

        with allure.step("Создать фильм"):
            create_resp = await client.post("/movies/", json=movie_data)
            movie_id = create_resp.json()["id"]

        with allure.step("Обновить поле watched = true"):
            update_data = {"watched": True}
            response = await client.patch(f"/movies/{movie_id}", json=update_data)

        with allure.step("Проверить статус и значение watched"):
            assert response.status_code == 200
            data = response.json()
            assert data["watched"] is True


@allure.feature("Movies")
@allure.story("Delete movie")
class TestMovieDelete:
    """Тестирование удаления фильма (только админ)."""

    @allure.title("Удаление фильма")
    @allure.description("DELETE /movies/{id} должен удалить фильм.")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.asyncio
    async def test_delete_movie(self, client: AsyncClient) -> None:
        """
        Создаём фильм, затем удаляем и проверяем, что он больше не доступен.
        """
        movie_data: dict[str, Any] = {
            "title": "Матрица",
            "year": 1999,
            "type": "movie",
            "genres": "фантастика, боевик",
            "kp_id": 301,
            "rating": 8.7,
            "watched": False,
            "poster_url": "https://example.com/poster.jpg",
        }

        with allure.step("Создать фильм"):
            create_resp = await client.post("/movies/", json=movie_data)
            movie_id = create_resp.json()["id"]

        with allure.step("Удалить фильм"):
            response = await client.delete(f"/movies/{movie_id}")

        with allure.step("Проверить статус и сообщение"):
            assert response.status_code == 200
            assert response.json()["message"] == "Фильм удалён"

        with allure.step("Убедиться, что фильм больше не существует"):
            get_response = await client.get(f"/movies/{movie_id}")
            assert get_response.status_code == 404
