from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# Pydantic модели
# Movie schemas
class MovieBase(BaseModel):
    title: str
    description: str | None = None
    year: int | None = None
    type: str
    genres: str
    rating: float | None = None
    watched: bool = False


class MovieCreate(MovieBase):
    kp_id: int
    poster_url: str | None = None


class MovieUpdate(BaseModel):
    watched: bool | None = None


class MovieSchema(MovieBase):
    id: int
    kp_id: int
    poster_url: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserBase(BaseModel):
    telegram_id: int
    username: str | None = None


class UserCreate(UserBase):
    is_admin: bool = False


class UserSchema(UserBase):
    id: int
    is_admin: bool
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StudioItem(BaseModel):
    """Одна студия из списка"""

    title: str = Field(..., description="Название студии")
    type: str = Field(..., description="Тип (Производство, Прокат и т.д.)")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"title": "Entertainment One", "type": "Производство"}
        }
    )


class StudiosResponse(BaseModel):
    """Ответ со списком студий"""

    docs: list[StudioItem] = Field(..., description="Список студий")
    total: int = Field(None, description="Всего записей")
    limit: int = Field(None, description="Лимит на странице")
    page: int = Field(None, description="Текущая страница")
    pages: int = Field(None, description="Всего страниц")
    title: str = Field(..., description="Название студии")
    type: str = Field(..., description="Тип (Производство, Прокат и т.д.)")
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "docs": [
                    {"title": "Entertainment One", "type": "Производство"},
                    {"title": "Focus Features", "type": "Прокат"},
                ],
                "total": 8,
                "limit": 10,
                "page": 1,
                "pages": 1,
            }
        }
    )
