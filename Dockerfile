# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект (кроме игнорируемого)
COPY . .

# Открываем порт Flask
EXPOSE 5000

# Запускаем приложение
CMD ["python", "run.py"]