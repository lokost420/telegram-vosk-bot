import os
import logging
import tempfile
import json
import subprocess
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import vosk

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Используем ЛЕГКУЮ модель Vosk
MODEL_PATH = "vosk-model-small-ru-0.22"
model = None

def init_model():
    global model
    try:
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Модель не найдена: {MODEL_PATH}")
            return False
        
        logger.info("Загружаю ЛЕГКУЮ модель Vosk (400 МБ)...")
        model = vosk.Model(MODEL_PATH)
        logger.info("✅ Легкая модель успешно загружена")
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
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = tmp.name
    
    try:
        if not convert_audio_to_wav(audio_path, wav_path):
            return "Ошибка конвертации аудио"
        
        recognizer = vosk.KaldiRecognizer(model, 16000)
        
        with open(wav_path, 'rb') as f:
            audio_data = f.read()
        
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
        try:
            os.unlink(wav_path)
        except:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для распознавания речи.\n"
        "Использую легкую модель Vosk (400 МБ).\n"
        "Отправьте мне голосовое сообщение!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Просто отправьте голосовое сообщение!\n"
        "Я распознаю речь и пришлю текст.\n\n"
        "⚡ Использую легкую модель для быстрой работы."
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if model:
        await update.message.reply_text("✅ Бот работает, легкая модель загружена")
    else:
        await update.message.reply_text("❌ Модель не загружена")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых сообщений"""
    user = update.effective_user
    logger.info(f"Голосовое сообщение от {user.id}")
    
    await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        voice_file = await update.message.voice.get_file()
        
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
            temp_path = tmp.name
        
        await voice_file.download_to_drive(temp_path)
        
        text = recognize_speech(temp_path)
        
        response = f"📝 Распознанный текст:\n\n{text}"
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке")
    finally:
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass

def main():
    # Инициализация модели
    logger.info("=== ЗАПУСК БОТА С ЛЕГКОЙ МОДЕЛЬЮ ===")
    
    # Проверяем переменные окружения
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    APP_NAME = os.getenv("APP_NAME", "")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        logger.info("Установите в Amvera: TELEGRAM_BOT_TOKEN = ваш_токен")
        logger.info("Ожидаю 30 секунд перед завершением...")
        time.sleep(30)
        return
    
    logger.info(f"✅ Токен получен (первые 10 символов): {TOKEN[:10]}...")
    logger.info(f"📱 APP_NAME: {APP_NAME if APP_NAME else 'НЕ УСТАНОВЛЕН'}")
    
    if not init_model():
        logger.error("❌ Не удалось загрузить модель Vosk")
        return
    
    # Создание приложения
    try:
        application = Application.builder().token(TOKEN).build()
        logger.info("✅ Приложение Telegram создано успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка создания приложения Telegram: {e}")
        return
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # Запуск
    logger.info("🚀 Запускаю бота...")
    
    # Проверяем, на Amvera ли мы
    port = int(os.environ.get('PORT', 8080))
    
    if APP_NAME:
        # Режим Amvera (webhook)
        webhook_url = f"https://{APP_NAME}.amvera.io/{TOKEN}"
        logger.info(f"🌐 Использую webhook: {webhook_url}")
        
        try:
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=TOKEN,
                webhook_url=webhook_url,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"❌ Ошибка запуска webhook: {e}")
            logger.info("🔄 Пробую использовать polling...")
            try:
                application.run_polling()
            except Exception as e2:
                logger.error(f"❌ Ошибка запуска polling: {e2}")
    else:
        # Локальный режим (polling)
        logger.info("📡 Использую polling (локальный режим)")
        try:
            application.run_polling()
        except Exception as e:
            logger.error(f"❌ Ошибка запуска polling: {e}")

if __name__ == '__main__':
    # Создаем папки если их нет
    os.makedirs("logs", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        time.sleep(5)