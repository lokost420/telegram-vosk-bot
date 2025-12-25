FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Загружаем ЛЕГКУЮ модель Vosk (400 МБ вместо 1.8 ГБ)
RUN echo "Загружаю легкую модель Vosk (400 МБ)..." \
    && wget -q https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip \
    && unzip -q vosk-model-small-ru-0.22.zip \
    && rm vosk-model-small-ru-0.22.zip \
    && echo "Легкая модель загружена успешно"

# Копируем исходный код
COPY app.py .

# Создаем необходимые директории
RUN mkdir -p logs temp

# Открываем порт
EXPOSE 8080

# Запускаем приложение
CMD ["python", "app.py"]