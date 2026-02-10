import asyncio
from sqlalchemy import select
from api.database import AsyncSessionLocal
from api.models import Movie


async def check_movies():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie))
        movies = result.scalars().all()

        if not movies:
            print("❌ В базе данных нет фильмов.")
        else:
            print(f"✅ Найдено {len(movies)} фильм(ов):")
            for m in movies:
                print(f"  - {m.title} (ID: {m.id}, просмотрено: {m.watched})")


if __name__ == "__main__":
    asyncio.run(check_movies())