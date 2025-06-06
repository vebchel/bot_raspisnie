    # db.py
import sqlite3
import logging
from config import DB_NAME  # <--- ДОБАВИЛИ ИМПОРТ

    # Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
        """Инициализирует базу данных, создает таблицу users если ее нет."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE,
                name TEXT,
                surname TEXT,
                user_group TEXT,
                schedule_time TEXT -- Время в формате HH:MM
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"База данных '{DB_NAME}' инициализирована.")

def add_user(chat_id: int, username: str, name: str, surname: str, user_group: str, schedule_time: str):
        """Добавляет нового пользователя в базу данных."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (chat_id, name, surname, user_group, schedule_time) VALUES (?, ?, ?, ?, ?)",
                (chat_id, name, surname, user_group, schedule_time)
            )
            conn.commit()
            logger.info(f"Добавлен пользователь: {chat_id}, Группа: {user_group}, Время: {schedule_time}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Пользователь с chat_id {chat_id} уже существует.")
            return False # Пользователь уже существует
        finally:
            conn.close()

def get_user(chat_id: int):
        """Получает информацию о пользователе по chat_id."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        user = cursor.fetchone()
        conn.close()
        return user # Вернет None, если пользователь не найден

def update_user_time(chat_id: int, schedule_time: str):
        """Обновляет время расписания для пользователя."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET schedule_time = ? WHERE chat_id = ?",
            (schedule_time, chat_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Обновлено время для пользователя {chat_id} на {schedule_time}")

def get_users_for_time(time_hh_mm: str):
        """Получает список пользователей, которые хотят расписание в указанное время (HH:MM)."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, user_group FROM users WHERE schedule_time = ?", (time_hh_mm,))
        users = cursor.fetchall()
        conn.close()
        return users


def delete_user(chat_id: int):
        """Удаляет пользователя из базы данных."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
            conn.commit()
            logger.info(f"Пользователь с chat_id {chat_id} удален из базы данных.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении пользователя с chat_id {chat_id}: {e}")
        finally:
            conn.close()


    # Инициализируем базу данных при первом импорте модуля
init_db()
    
