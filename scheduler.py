# scheduler.py
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

import db
import schedule_fetcher
from config import TIME_FORMAT

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
bot_instance: Bot = None # Здесь будем хранить экземпляр бота

def init_scheduler(bot: Bot):
    """Инициализирует планировщик и сохраняет экземпляр бота."""
    global bot_instance
    bot_instance = bot
    scheduler.start()
    logger.info("Планировщик запущен.")
    # Добавляем задачу, которая будет проверять, кому пора отправить расписание каждую минуту
    # Или можно было бы добавлять individual jobs for each user - но это сложнее управлять
    # Этот способ проще для старта:
    scheduler.add_job(check_and_send_schedules, CronTrigger(second="0")) # Проверять каждую минуту на 00 секунде
    logger.info("Задача проверки расписаний добавлена.")


async def check_and_send_schedules():
    """Проверяет, каким пользователям нужно отправить расписание сейчас, и отправляет."""
    if not bot_instance:
        logger.error("Экземпляр бота не инициализирован в планировщике!")
        return

    current_time_str = datetime.now().strftime(TIME_FORMAT)
    logger.info(f"Проверка расписаний для времени: {current_time_str}")

    users_to_notify = db.get_users_for_time(current_time_str)

    if not users_to_notify:
        logger.info(f"Нет пользователей для отправки расписания в {current_time_str}")
        return

    logger.info(f"Найдено {len(users_to_notify)} пользователей для отправки в {current_time_str}")

    for chat_id, group in users_to_notify:
        try:
            # Получаем расписание для группы
            schedule_text = schedule_fetcher.get_schedule(group)
            # Отправляем сообщение
            await bot_instance.send_message(chat_id, schedule_text)
            logger.info(f"Отправлено расписание пользователю {chat_id} (Группа: {group})")
        except Exception as e:
            logger.error(f"Ошибка при отправке расписания пользователю {chat_id}: {e}")

# В этом подходе мы не добавляем отдельную задачу для каждого пользователя.
# Вместо этого, есть одна задача (check_and_send_schedules),
# которая запускается каждую минуту и проверяет всех пользователей в БД,
# кому пора отправить расписание в текущую минуту.
# Это проще управлять, но менее гибко, если нужны более сложные расписания.
# Для старта с лимитом в 100 руб/мес - это хороший вариант.
