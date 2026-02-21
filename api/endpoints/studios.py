import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from api.core.models import User
from api.dependencies import get_current_user
from api.schemas import StudioItem, StudiosResponse

router = APIRouter(prefix="/studios", tags=["Студии"])
# Все пути этого роутера будут начинаться с /studios
# tags=["Студии"] в Swagger эти эндпоинты будут сгруппированы под этим тегом


@router.get(
    "/studios",
    response_model=StudiosResponse,
    summary="Получить студии по ID фильма из Кинопоиска",
    description="Запрашивает API Кинопоиска и возвращает список студий,"
    " участвовавших в создании фильма с указанным ID.",
    responses={
        200: {"description": "Успешный ответ", "model": StudiosResponse},
        400: {
            "description": "Не указан ID фильма",
            "content": {
                "application/json": {"example": {"detail": "movie_id is required"}}
            },
        },
        404: {
            "description": "Фильм не найден или студии отсутствуют",
            "content": {
                "application/json": {"example": {"detail": "Studios not found"}}
            },
        },
        500: {
            "description": "Ошибка при обращении к API Кинопоиска",
            "content": {
                "application/json": {"example": {"detail": "Kinopoisk API error"}}
            },
        },
    },
)
async def get_studios_by_movie(
    movie_id: int = Query(
        ...,
        description="ID фильма в базе Кинопоиска (например, 798277)",
        examples=[798277],
    ),
    page: int = Query(1, ge=1, description="Номер страницы", examples=[1]),
    limit: int = Query(
        10, ge=1, le=100, description="Количество записей на странице", examples=[10]
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список студий, работавших над фильмом.

    Параметры:
    - **movie_id**: ID фильма (обязательный)
    - **page**: страница (по умолчанию 1)
    - **limit**: лимит на страницу (по умолчанию 10, максимум 100)

    Возвращает список студий с их названиями и типами.
    """
    # 1. Проверяем авторизацию (если нужно)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # 2. Получаем ключи из переменных окружения
    api_key = os.getenv("KINOPOISK_API_KEY")
    base_url = os.getenv("KINOPOISK_API_URL")
    if not api_key or not base_url:
        raise HTTPException(status_code=500, detail="Kinopoisk API not configured")

    # 3. Формируем запрос к API Кинопоиска
    url = f"{base_url}studio"
    params = {
        "page": page,
        "limit": limit,
        "selectFields": ["title", "type"],
        "notNullFields": ["title", "type"],
        "movies.id": movie_id,
    }
    headers = {"X-API-KEY": api_key, "accept": "application/json"}

    # 4. Выполняем асинхронный HTTP-запрос
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Studios not found") from e
            raise HTTPException(
                status_code=500, detail=f"Kinopoisk API error: {e}"
            ) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e

    # 5. Если студий нет, бросаем 404
    if not data.get("docs"):
        raise HTTPException(status_code=404, detail="No studios found for this movie")

    # 6. Преобразуем ответ в нашу Pydantic модель
    return StudiosResponse(
        docs=[
            StudioItem(
                title=item.get("title", "Unknown"), type=item.get("type", "Unknown")
            )
            for item in data["docs"]
        ],
        total=data["total"],
        limit=data["limit"],
        page=data["page"],
        pages=data["pages"],
    )


"""
СРАВНЕНИЕ СПОСОБОВ ПЕРЕДАЧИ ДАННЫХ В FASTAPI:

| Тип параметра | Синтаксис в коде      | Место в запросе     | Пример ссылки / Тела         |
|---------------|-----------------------|---------------------|------------------------------|
| Path (Путь)   | @router.get("/{id}")  | Прямо в адресе      | /movies/10                   |
| Query (Запрос)| query_param: str      | После знака ?       | /movies?genre=action&limit=5 |
| Body (Тело)   | data: MyPydanticModel | Скрыто в теле (JSON)| {"title": "Inception", ...}  |

@router.get("/movies/{movie_id}")  # {movie_id} - это Path
async def get_movie(
    movie_id: int,                              # Из пути
    rating: float = Query(8.0, ge=0, le=10),    # Из Query (?rating=8.5)
    token: str = Header(None)                   # Из заголовков (Headers)
):
    pass
"""
