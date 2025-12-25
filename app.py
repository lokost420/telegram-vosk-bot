import os
import logging
import tempfile
import json
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import vosk

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка модели Vosk
MODEL_PATH = "vosk-model-ru-0.42"
model = None

def init_model():
    global model
    try:
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Модель не найдена: {MODEL_PATH}")
            return False
        
        logger.info("Загружаю модель Vosk...")
        model = vosk.Model(MODEL_PATH)
        logger.info("Модель успешно загружена")
        return True
    except Exception as e:
        logger.error(f"Ошибка загрузки модели: {e}")
        return False

def convert_audio_to_wav(input_path, output_path):
    """Конвертация аудио в WAV формат"""
    try:
        command = [
            'ffmpeg', '-i', input_path,
            '-ar', '16000',
            '-ac', '1',
            '-acodec', 'pcm_s16le',
            output_path,
            '-y',
            '-loglevel', 'error'
        ]
        subprocess.run(command, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка конвертации: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

def recognize_speech(audio_path):
    """Распознавание речи"""
    if model is None:
        return "Модель не загружена"
    
    # Создаем временный WAV файл
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = tmp.name
    
    try:
        # Конвертируем в WAV
        if not convert_audio_to_wav(audio_path, wav_path):
            return "Ошибка конвертации аудио"
        
        # Настраиваем распознаватель
        recognizer = vosk.KaldiRecognizer(model, 16000)
        
        # Читаем аудиофайл
        with open(wav_path, 'rb') as f:
            audio_data = f.read()
        
        # Распознаем
        if recognizer.AcceptWaveform(audio_data):
            result = json.loads(recognizer.Result())
            text = result.get('text', '')
        else:
            result = json.loads(recognizer.FinalResult())
            text = result.get('text', '')
        
        return text if text else "Речь не распознана"
        
    except Exception as e:
        logger.error(f"Ошибка распознавания: {e}")
        return f"Ошибка: {str(e)}"
    finally:
        # Удаляем временный файл
        try:
            os.unlink(wav_path)
        except:
            pass

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для распознавания речи.\n"
        "Отправьте мне голосовое сообщение или аудиофайл."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Доступные команды:\n"
        "/start - начать работу\n"
        "/help - помощь\n"
        "/status - статус бота\n\n"
        "Просто отправьте голосовое сообщение!"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if model:
        await update.message.reply_text("✅ Бот работает, модель загружена")
    else:
        await update.message.reply_text("❌ Модель не загружена")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых сообщений"""
    user = update.effective_user
    logger.info(f"Голосовое сообщение от {user.id}")
    
    await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Скачиваем файл
        voice_file = await update.message.voice.get_file()
        
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
            temp_path = tmp.name
        
        await voice_file.download_to_drive(temp_path)
        
        # Распознаем речь
        text = recognize_speech(temp_path)
        
        # Отправляем результат
        response = f"📝 Распознанный текст:\n\n{text}"
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке")
    finally:
        # Очистка
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка аудиофайлов"""
    await update.message.reply_text("🎵 Получен аудиофайл. К сожалению, эта функция в разработке.")

# Основная функция
def main():
    # Инициализация модели
    if not init_model():
        logger.error("Не удалось загрузить модель Vosk")
        return
    
    # Получение токена
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        logger.info("Установите переменную в настройках Amvera")
        return
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    
    # Запуск
    logger.info("Запускаю бота...")
    
    # Проверяем, на Amvera ли мы
    port = int(os.environ.get('PORT', 8080))
    app_name = os.environ.get('APP_NAME', '')
    
    if app_name:
        # Режим Amvera (webhook)
        webhook_url = f"https://{app_name}.amvera.io/{TOKEN}"
        logger.info(f"Использую webhook: {webhook_url}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        # Локальный режим (polling)
        logger.info("Использую polling (локальный режим)")
        application.run_polling()

if __name__ == '__main__':
    # Создаем папки если их нет
    os.makedirs("logs", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    
    main()
