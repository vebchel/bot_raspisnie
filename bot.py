# bot.py
# bot.py
import asyncio
import logging
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import config
import db
import scheduler
import schedule_fetcher

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
#bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# Определение состояний для FSM (Finite State Machine)
class RegStates(StatesGroup):
    """Состояния для процесса регистрации."""
    name = State()
    surname = State()
    group = State()
    schedule_time = State()


# --- ФУНКЦИЯ ДЛЯ СОЗДАНИЯ КЛАВИАТУРЫ ---
def create_keyboard():
    """Создает клавиатуру с кнопками."""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [
            KeyboardButton(text="Регистрация 📝"),
            KeyboardButton(text="Все расписание 📅"),
        ],
        [
            KeyboardButton(text="Расписание на сегодня 🗓️"),
        ],
        [
            KeyboardButton(text="Изменить время ⏰"),
        ],
        [
            KeyboardButton(text="Удалить профиль 🗑️")
        ]
    ])
    return keyboard


# --- ХЕНДЛЕРЫ ---

@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext) -> None:
    """Обрабатывает команду /start."""
    user = db.get_user(message.chat.id)
    keyboard = create_keyboard()  # Создаем клавиатуру

    if user:
        # Пользователь уже зарегистрирован
        await message.answer(
            f"Привет снова, {user[2]}! 👋\n"
            f"Твоя группа: {user[4]} 😎\n"
            f"Расписание приходит в: {user[5]} ⏰\n\n"
            "Что хочешь узнать? 🤔",  # Убираем лишний текст
            reply_markup=keyboard  # Отправляем клавиатуру
        )
        await state.clear()  # Убедимся, что состояние сброшено
    else:
        # Новый пользователь, начинаем регистрацию
        await message.answer(
            f"Йоу, {message.from_user.full_name}! 👋 Я твой личный бот-помощник по расписанию в колледже! 🚀\n"
            "Но сначала давай познакомимся! Как тебя зовут? 🤔\n"
            "(Просто напиши свое имя)",
            reply_markup=keyboard  # Отправляем клавиатуру
        )
        await state.set_state(RegStates.name)
        logger.info(f"Пользователь {message.chat.id} начал регистрацию.")


@dp.message(RegStates.name)
async def reg_name(message: types.Message, state: FSMContext):
    """Ловит имя и спрашивает фамилию."""
    if not message.text or len(message.text) < 2:
        await message.answer("Кажется, это не совсем похоже на имя 🤔. Попробуй еще раз?", reply_markup=create_keyboard())
        return

    await state.update_data(name=message.text.strip())
    await message.answer(f"Окей, {message.text.strip()}! Принято ✅\nТеперь напиши свою фамилию.", reply_markup=create_keyboard())
    await state.set_state(RegStates.surname)


@dp.message(RegStates.surname)
async def reg_surname(message: types.Message, state: FSMContext):
    """Ловит фамилию и спрашивает группу."""
    if not message.text or len(message.text) < 2:
        await message.answer("А теперь введи свою фамилию, пожалуйста 🤔. Еще разок?", reply_markup=create_keyboard())
        return

    await state.update_data(surname=message.text.strip())
    await message.answer("Супер! 💪 Теперь напиши название своей группы (например, ИВТ-1, ПД-2 и т.д.).", reply_markup=create_keyboard())
    await state.set_state(RegStates.group)


@dp.message(RegStates.group)
async def reg_group(message: types.Message, state: FSMContext):
    """Ловит группу и спрашивает время для расписания."""
    if not message.text or len(message.text) < 2:
        await message.answer("Нужна группа, чувак! Без нее никак 😅. Введи еще раз?", reply_markup=create_keyboard())
        return

    await state.update_data(group=message.text.strip().upper())  # Группу можно сохранить в верхнем регистре
    await message.answer(
        "Красавчик! 😎 Последний шаг!\n"
        "Напиши время, когда тебе удобнее всего получать расписание каждый день.\n"
        "⏰ Введи в формате ЧЧ:ММ (например, 08:30, 12:00).", reply_markup=create_keyboard()
    )
    await state.set_state(RegStates.schedule_time)


@dp.message(RegStates.schedule_time)
async def reg_schedule_time(message: types.Message, state: FSMContext):
    """Ловит время, сохраняет пользователя и завершает регистрацию/изменение времени."""
    time_str = message.text.strip()

    # Проверяем формат времени ЧЧ:ММ
    if not re.match(r"^(0[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", time_str):
        await message.answer("Неправильный формат времени 🤔. Пожалуйста, введи время в формате ЧЧ:ММ (например, 08:30).", reply_markup=create_keyboard())
        return

    chat_id = message.chat.id

    # Проверяем, есть ли данные в state (значит, это регистрация)
    user_data = await state.get_data()
    if 'name' in user_data and 'surname' in user_data and 'group' in user_data:
        # Это регистрация
        name = user_data['name']
        surname = user_data['surname']
        group = user_data['group']

        # Сохраняем пользователя в БД (только при регистрации)
        success = db.add_user(chat_id, message.from_user.username, name, surname, group, time_str)

        if success:
            # Регистрация успешна
            await message.answer(
                f"Ура! 🥳 Регистрация завершена!\n"
                f"Привет, {name} {surname} из группы {group}! ✨\n"
                f"Теперь я буду присылать тебе расписание каждый день в {time_str} ⏰\n"
                f"Будь на связи! 😉", reply_markup=create_keyboard()
            )
            logger.info(f"Регистрация пользователя {chat_id} успешно завершена.")
        else:
            # Этого не должно произойти, если /start корректно обрабатывает уже зарегистрированных
            await message.answer("Что-то пошло не так при сохранении твоих данных 🤔. Попробуй начать сначала командой /start.", reply_markup=create_keyboard())

    else:
        # Это изменение времени
        user = db.get_user(chat_id)
        if not user:
            await message.answer("Ты не зарегистрирован! Пожалуйста, используй /start для регистрации.", reply_markup=create_keyboard())
            await state.clear()
            return

        name = user[2]
        surname = user[3]
        group = user[4]

        # Обновляем время в базе данных (только при изменении времени)
        db.update_user_time(chat_id, time_str)
        logger.info(f"Пользователь {chat_id} изменил время рассылки на {time_str}")
        await message.answer(f"Отлично! ✅ Теперь расписание будет приходить в {time_str} ⏰", reply_markup=create_keyboard())

    await state.clear()  # Очищаем состояние FSM после завершения


@dp.message(F.text == "/myinfo")
async def show_my_info(message: types.Message):
    """Показывает информацию о зарегистрированном пользователе."""
    user = db.get_user(message.chat.id)
    keyboard = create_keyboard()

    if user:
        await message.answer(
            f"Твоя инфа, бро 👇\n\n"
            f"Имя: {user[2]}\n"
            f"Фамилия: {user[3]}\n"
            f"Группа: {user[4]}\n"
            f"Время для расписания: {user[5]} ⏰",
            reply_markup=keyboard
        )
    else:
        await message.answer("Ты еще не зарегистрирован! 😟 Используй команду /start чтобы начать.", reply_markup=keyboard)


@dp.message(F.text == "/getschedule")
async def get_schedule_now(message: types.Message):
    """Отправляет расписание для пользователя прямо сейчас."""
    user = db.get_user(message.chat.id)
    keyboard = create_keyboard()

    if user:
        group = user[4]
        schedule_text = schedule_fetcher.get_schedule(group)
        await message.answer(f"Держи расписание на сейчас, {user[2]}! 👇\n{schedule_text}", reply_markup=keyboard)
    else:
        await message.answer("Чтобы получить расписание, нужно сначала зарегистрироваться! ☝️ Используй /start.", reply_markup=keyboard)


# --- ХЕНДЛЕР ДЛЯ УДАЛЕНИЯ ПРОФИЛЯ ---

@dp.message(F.text == "Удалить профиль 🗑️")
async def delete_profile(message: types.Message):
    """Удаляет профиль пользователя из базы данных."""
    user_id = message.chat.id
    keyboard = create_keyboard()

    # Подтверждаем удаление
    inline_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="Да, удалить 🗑️", callback_data="confirm_delete"),
            types.InlineKeyboardButton(text="Нет, отменить 🙅‍♂️", callback_data="cancel_delete"),
        ]
    ])
    await message.answer("Ты уверен, что хочешь удалить свой профиль? 🥺 Все твои данные будут стерты, и тебе придется регистрироваться заново.", reply_markup=inline_keyboard)


# Обработчик нажатий на кнопки подтверждения/отмены
@dp.callback_query(F.data.in_({"confirm_delete", "cancel_delete"}))
async def delete_confirmation(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.message.chat.id
    keyboard = create_keyboard()

    if callback.data == "confirm_delete":
        # Удаляем пользователя из базы данных
        db.delete_user(user_id)
        logger.info(f"Пользователь {user_id} удалил свой профиль.")

        await callback.message.edit_text("Твой профиль успешно удален! 👋 Больше я тебя не знаю 🤖. Чтобы начать заново, используй /start")
        await state.clear()  # Сбрасываем состояние FSM (если оно было)
    else:
        # Отмена удаления
        await callback.message.edit_text("Удаление отменено. 😎 Твой профиль в безопасности!")

    await callback.answer()  # Обязательно отвечаем на callback query, чтобы убрать "часики"


# --- ХЕНДЛЕРЫ ДЛЯ КНОПОК ---
@dp.message(F.text == "Регистрация 📝")
async def registration_handler(message: types.Message, state: FSMContext):
    """Обрабатывает нажатие на кнопку "Регистрация"."""
    await message.answer("Чтобы зарегистрироваться, напиши свое имя:", reply_markup=create_keyboard())
    await state.set_state(RegStates.name)


@dp.message(F.text == "Все расписание 📅")
async def all_schedule_handler(message: types.Message):
    """Обрабатывает нажатие на кнопку "Все расписание"."""
    user = db.get_user(message.chat.id)
    keyboard = create_keyboard()

    if user:
        group = user[4]
        # Вызываем функцию get_week_schedule (расписание на неделю)
        schedule_text = schedule_fetcher.get_week_schedule(group)  # <--- ЗАМЕНИЛИ!
        await message.answer(f"Расписание на неделю для группы {group}: 👇\n{schedule_text}", reply_markup=keyboard)
    else:
        await message.answer("Чтобы получить расписание, нужно сначала зарегистрироваться! ☝️ Используй /start.", reply_markup=keyboard)


@dp.message(F.text == "Расписание на сегодня 🗓️")
async def today_schedule_handler(message: types.Message):
    """Обрабатывает нажатие на кнопку "Расписание на сегодня"."""
    user = db.get_user(message.chat.id)
    keyboard = create_keyboard()

    if user:
        group = user[4]
        # Вызываем функцию get_schedule (расписание только на сегодня)
        schedule_text = schedule_fetcher.get_schedule(group)
        await message.answer(f"Расписание на сегодня для группы {group}: 👇\n{schedule_text}", reply_markup=keyboard)
    else:
        await message.answer("Чтобы получить расписание, нужно сначала зарегистрироваться! ☝️ Используй /start.", reply_markup=keyboard)


@dp.message(F.text == "Изменить время ⏰")
async def change_time_handler(message: types.Message, state: FSMContext):
    """Обрабатывает нажатие на кнопку "Изменить время"."""
    await message.answer("Напиши время, в которое ты хочешь получать расписание (в формате ЧЧ:ММ):", reply_markup=create_keyboard())
    await state.set_state(RegStates.schedule_time)


@dp.message(RegStates.schedule_time)
async def reg_schedule_time(message: types.Message, state: FSMContext):
    """Ловит время, сохраняет пользователя и завершает регистрацию/изменение времени."""
    time_str = message.text.strip()

    # Проверяем формат времени ЧЧ:ММ
    if not re.match(r"^(0[0-9]|1[0-9]|2[0-3]):([0-5][0-9])$", time_str):
        await message.answer("Неправильный формат времени 🤔. Пожалуйста, введи время в формате ЧЧ:ММ (например, 08:30).", reply_markup=create_keyboard())
        return

    chat_id = message.chat.id

    # Проверяем, есть ли данные в state (значит, это регистрация)
    user_data = await state.get_data()
    if 'name' in user_data and 'surname' in user_data and 'group' in user_data:
        # Это регистрация
        name = user_data['name']
        surname = user_data['surname']
        group = user_data['group']

        # Сохраняем пользователя в БД (только при регистрации)
        success = db.add_user(chat_id, message.from_user.username, name, surname, group, time_str)

        if success:
            # Регистрация успешна
            await message.answer(
                f"Ура! 🥳 Регистрация завершена!\n"
                f"Привет, {name} {surname} из группы {group}! ✨\n"
                f"Теперь я буду присылать тебе расписание каждый день в {time_str} ⏰\n"
                f"Будь на связи! 😉", reply_markup=create_keyboard()
            )
            logger.info(f"Регистрация пользователя {chat_id} успешно завершена.")
        else:
            # Этого не должно произойти, если /start корректно обрабатывает уже зарегистрированных
            await message.answer("Что-то пошло не так при сохранении твоих данных 🤔. Попробуй начать сначала командой /start.", reply_markup=create_keyboard())

    else:
        # Это изменение времени
        user = db.get_user(chat_id)
        if not user:
            await message.answer("Ты не зарегистрирован! Пожалуйста, используй /start для регистрации.", reply_markup=create_keyboard())
            await state.clear()
            return

        name = user[2]
        surname = user[3]
        group = user[4]

        # Обновляем время в базе данных (только при изменении времени)
        db.update_user_time(chat_id, time_str)
        logger.info(f"Пользователь {chat_id} изменил время рассылки на {time_str}")
        await message.answer(f"Отлично! ✅ Теперь расписание будет приходить в {time_str} ⏰", reply_markup=create_keyboard())

    await state.clear()  # Очищаем состояние FSM после завершения

@dp.message()
async def echo_handler(message: types.Message) -> None:
    """Эхо-хендлер для любых других сообщений."""
    try:
        await message.send_copy(chat_id=message.chat.id, reply_markup=create_keyboard())
    except TypeError:
        await message.answer("Не могу это скопировать! 😅", reply_markup=create_keyboard())


# --- ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ---

async def main() -> None:
    # Инициализируем базу данных (если еще не инициализирована)
    db.init_db()
    # Инициализируем планировщик, передавая ему экземпляр бота
    scheduler.init_scheduler(bot)

    # Запускаем поллинг бота
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен! 🚀")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
