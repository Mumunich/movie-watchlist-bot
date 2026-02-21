import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.models import Genre, Movie, Types, User
from api.dependencies import get_current_admin, get_current_user, get_db
from api.schemas import MovieCreate, MovieSchema, MovieUpdate

router = APIRouter()


@router.get("/", response_model=list[MovieSchema])
async def get_movies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    watched: bool | None = None,
    type_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Получить фильмы (только для авторизованных)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация"
        )

    query = select(Movie)

    if watched is not None:
        query = query.where(Movie.watched == watched)

    if type_filter:
        query = query.where(Movie.type == type_filter)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    movies = result.scalars().all()

    return movies


# movie_data — определяет, как распарсить и валидировать входящий JSON.
# FastAPI возьмёт тело запроса, проверит его по схеме MovieCreate
# и передаст в функцию объект этого типа.
# MovieCreate может не содержать поля id и created_at (они генерируются автоматически).
# response_model — определяет, как сериализовать ответ (то, что возвращает функция).
# FastAPI возьмёт возвращаемое значение, преобразует его по схеме MovieSchema в JSON
# и отправит клиенту.
# MovieSchema включает все поля, которые мы хотим показать клиенту.
@router.post("/", response_model=MovieSchema)
async def create_movie(
    movie_data: MovieCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать фильм (только для авторизованных)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    # Проверяем, нет ли уже такого фильма
    existing = await db.execute(select(Movie).where(Movie.kp_id == movie_data.kp_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Фильм уже существует")

    # сокращённый аналог кода: movie =
    # Movie(title=movie_data.title, kp_id=movie_data.kp_id, year=movie_data.year...)
    movie = Movie(**movie_data.model_dump())
    db.add(movie)
    await db.commit()
    await db.refresh(movie)

    return movie


# Получаем динамический параметр из URL
@router.delete("/{movie_id}")
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Удалить фильм (только для админа)"""
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")

    await db.delete(movie)
    await db.commit()

    return {"message": "Фильм удалён"}


@router.get("/{movie_id}", response_model=MovieSchema)
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить фильм по ID"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")

    return movie


@router.patch("/{movie_id}", response_model=MovieSchema)
async def update_movie(
    movie_id: int,
    movie_update: MovieUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить фильм (только для авторизованных)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")

    # Обновляем только переданные поля
    for field, value in movie_update.model_dump(exclude_unset=True).items():
        # устанавливаем атрибут field объекта movie в значение value
        setattr(movie, field, value)

    await db.commit()
    await db.refresh(movie)

    return movie


@router.get("/search/", response_model=list[MovieSchema])
async def search_movies(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Поиск фильмов по названию"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    query = select(Movie).where(Movie.title.ilike(f"%{q}%"))
    result = await db.execute(query)
    movies = result.scalars().all()
    return movies


@router.get("/filter/", response_model=list[MovieSchema])
async def filter_movies_by_genre(
    genre: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Фильтрация фильмов по жанру"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    query = select(Movie).where(Movie.genres.ilike(f"%{genre}%"))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/genres/", response_model=list[str])
async def get_genres(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Получить список всех жанров"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    result = await db.execute(select(Genre).order_by(Genre.name))
    genres = result.scalars().all()
    return [g.name for g in genres]


@router.get("/types/", response_model=list[str])
async def get_types(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Получить список всех типов"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    result = await db.execute(select(Types).order_by(Types.name))
    types = result.scalars().all()
    return [t.name for t in types]


@router.post("/sync/genres")
async def sync_genres(
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)
):
    """Синхронизировать жанры с Кинопоиском (только админ)"""
    KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")
    ALT_API_URL = os.getenv("KINOPOISK_ALT_API_URL")

    url = f"{ALT_API_URL}movie/possible-values-by-field?field=genres.name"
    headers = {"X-API-KEY": KINOPOISK_API_KEY}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        genres_data = response.json()

    # Очищаем старые жанры
    await db.execute(delete(Genre))

    # Добавляем новые
    for g in genres_data:
        genre = Genre(name=g["name"], slug=g["slug"])
        db.add(genre)

    await db.commit()

    return {"message": f"Добавлено {len(genres_data)} жанров"}


@router.post("/sync/types")
async def sync_types(
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)
):
    """Синхронизировать типы с Кинопоиском (только админ)"""
    KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")
    ALT_API_URL = os.getenv("KINOPOISK_ALT_API_URL")

    url = f"{ALT_API_URL}movie/possible-values-by-field?field=type"
    headers = {"X-API-KEY": KINOPOISK_API_KEY}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        types_data = response.json()

    # Очищаем старые типы
    await db.execute(delete(Types))

    # Добавляем новые
    for t in types_data:
        type_obj = Types(name=t["name"], slug=t["slug"])
        db.add(type_obj)

    await db.commit()

    return {"message": f"Добавлено {len(types_data)} типов"}
