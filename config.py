# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Загружаем токен бота из .env файла
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Название файла базы данных SQLite
DB_NAME = "students_schedule.db"

# Время в расписании будет храниться в формате HH:MM
TIME_FORMAT = "%H:%M"

WEBHOOK_URL = os.getenv("WEBHOOK_URL")