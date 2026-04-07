FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем директорию для данных (для локальной разработки)
RUN mkdir -p /app/data

# Запускаем бота
CMD ["python", "news_bot.py"]
