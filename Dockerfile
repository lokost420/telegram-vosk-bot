FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN echo "Загружаю модель Vosk..." \
    && wget -q https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip \
    && unzip -q vosk-model-ru-0.42.zip \
    && rm vosk-model-ru-0.42.zip \
    && echo "Модель загружена успешно"

COPY app.py .

RUN mkdir -p logs temp

EXPOSE 8080

CMD ["python", "app.py"]
