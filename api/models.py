from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Movie(Base):
    """
        Представляет фильм в системе.

        Attributes:
            title (str): Название фильма
            description (str) описание фильма
            year (int): Год выпуска
            kp_id (int) идентификатор кинопоиска
            poster_url (str) ссылка на постер
            rating (float) рейтинг кинопоиска
            type (str): Тип ('movie' или 'tv-series')
            genres (str): Жанры через запятую
        """

    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    kp_id = Column(Integer, unique=True, index=True)
    poster_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    type = Column(String, nullable=False)
    genres = Column(String, nullable=False)
    watched = Column(Boolean, default=False)
    # Используем UTC для времени
    created_at = Column(DateTime(timezone = True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Movie(title='{self.title}', watched={self.watched})>"

class Genre(Base):
    __tablename__ = "genres"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # "боевик"
    slug = Column(String, unique=True, nullable=False)  # "boevik"

    def __repr__(self):
        return f"<Genre(name='{self.name}', slug={self.slug})>"

class Types(Base):
    __tablename__ = "types"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # "animated-series"
    slug = Column(String, unique=True, nullable=False)  # "animated-series"

    def __repr__(self):
        return f"<Types(name='{self.name}', slug={self.slug})>"

class User(Base):
    __tablename__ = "users"

    id  = Column(Integer, primary_key=True)
    telegram_id  = Column(Integer, unique=True, nullable=False)
    username  = Column(String(100))
    is_active  = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone = True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Users(telegram_id='{self.telegram_id}', username={self.username})>"