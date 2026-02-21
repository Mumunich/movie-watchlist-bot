# Movie Bot FullStack Project

Проект системы управления личным списком фильмов с интеграцией Кинопоиск API.

## 🚀 Возможности
*   **Управление личным списком**: добавление, удаление и просмотр просмотренных фильмов/сериалов.
*   **Интеграция с Кинопоиск API**: автоматическое получение постеров, рейтингов, описаний и студий.
*   **Умная фильтрация**: поиск по жанрам, типам контента и студиям.
*   **Ролевая модель**: разграничение прав (Админ/Пользователь) для управления базой.
*   **Авто-синхронизация**: обновление справочников жанров и типов напрямую из внешнего API.

## 📁 Структура проекта
```
movie_bot/
├── Api/ # FastAPI приложение
│ ├── core/
│ │ ├── database.py # Настройка БД (SQLAlchemy async) (p. 3)
│ │ └── models.py # Модели БД (Movie, User, Genre, Types) (pp. 3-4)
│ ├── endpoints/ # Роутеры API (Auth, Movies, Users, Health, Studios) (0.1.4-0.1.16)
│ ├── init.py
│ ├── Dependencies.py # Зависимости FastAPI (get_db, auth) (p. 16)
│ ├── Main.py # Точка входа FastAPI приложения (p. 17)
│ └── Schemas.py # Pydantic схемы для валидации данных (pp. 17-18)
├── bot/ # Telegram-бот на aiogram 3
│ ├── services/
│ │ ├── api_client.py # Клиент для взаимодействия с локальным API (p. 19)
│ │ └── movie_service.py # Сервис для парсинга данных и логики (p. 22)
│ ├── Handlers.py # Обработчики команд и кнопок бота (0.1.25-0.1.39)
│ ├── Kinopoisk.py # Функции для работы с API Кинопоиска и UI (0.1.39-0.1.44)
│ └── Logger.py # Настройка логирования (p. 44)
├── Alembic/ # Миграции базы данных (pp. 1-2)
├── .env.example # Пример файла переменных окружения
├── alembic.ini # Конфиг Alembic
├── docker-compose.yml # Скрипт для запуска в Docker
└── requirements.txt # Зависимости проекта
```

## 🛠️ Технологии
- **Python** 3.11+
- **FastAPI** — асинхронный бэкенд API.
- **Aiogram** 3.x — современный фреймворк для Telegram-бота.
- **SQLAlchemy** (async) — работа с БД через асинхронный движок.
- **PostgreSQL** — основное хранилище данных.
- **Alembic** — управление миграциями базы данных.
- **Pytest & Allure** — тестирование и наглядная отчетность.
- **Ruff & Mypy** — контроль качества кода и типизации.

## 🔧 Быстрый старт
### Настройка окружения
Создайте `.env` файл:
```env
BOT_TOKEN=ваш_токен_бота
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/movie_bot
KINOPOISK_API_KEY=ваш_ключ_api
KINOPOISK_API_URL=https://api.kinopoisk.dev
KINOPOISK_ALT_API_URL=https://api.kinopoisk.dev
POSTER_PLACEHOLDER_URL=https://ссылка_на_заглушку_постера
```

### Запуск через Docker
```bash
docker-compose up --build -d
```

## 🏗 Миграции (Alembic)
Для управления схемой БД используются следующие команды:
*   Создание миграции: alembic revision --autogenerate -m "описание_изменений"
*   Применение: alembic upgrade head
*   Откат: alembic downgrade -1

## 🧪 Тестирование и Качество
```
# Запуск с подробным выводом
pytest tests/ -v

# Проверка покрытия кода тестами
pytest --cov=api --cov=bot tests/ --cov-report=html

# Генерация отчета Allure
pytest --alluredir=allure-results tests/
allure serve allure-results
```

### Линтинг и форматирование
```
# Проверка и исправление ошибок форматирования
ruff check --fix ; ruff format

# Строгая проверка типов
mypy .
```

## 💾 Бэкап и Восстановление
Для обеспечения сохранности данных используйте команды pg_dump (внутри Docker или локально):
### 1. Создание бэкапа
```bash
docker exec -t movie_bot_db pg_dumpall -c -U postgres > backup_$(date +%Y-%m-%d).sql
```
### 2. Восстановление
```bash
cat backup_file.sql | docker exec -i movie_bot_db psql -U postgres
```

## 📖 Документация API
После запуска бэкенда интерактивная документация доступна по адресам:
*   **Swagger UI**: http://localhost:8000/docs
*   **ReDoc**: http://localhost:8000/redoc

## 🤖 CI/CD Pipeline
В репозитории настроен GitHub Actions (.github/workflows/ci.yml), который при каждом пуше:
Поднимает окружение Python 3.11.
Проверяет код линтером Ruff.
Проверяет типизацию через Mypy.
Запускает весь набор тестов (Auth, Users, Movies, Handlers).