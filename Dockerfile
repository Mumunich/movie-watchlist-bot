# Инструкция по сборке образа
# Базовый образ — уже готовая ОС с Python
FROM python:3.11-slim
# Рабочая папка внутри контейнера
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем библиотеки
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВЕСЬ проект
COPY . .

# Создаём папку для логов
RUN mkdir -p /app/logs

# Команда запуска FastApi по умолчанию
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]