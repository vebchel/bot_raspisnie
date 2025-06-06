# schedule_fetcher.py
# /deleteprofile
import logging
import random
import requests
from bs4 import BeautifulSoup
import datetime  # Добавляем импорт для работы с датами

logger = logging.getLogger(__name__)

# --- КОНСТАНТЫ ---
# Ссылка на страницу со списком групп
SCHEDULE_WEBSITE_URL = "https://bincol.ru/rasp/grupp.php"
# Базовый URL для расписания (чтобы составить полную ссылку)
BASE_URL = "https://bincol.ru/rasp/"
# -----------------

def format_schedule(para: str, predmet: str, auditoriya: str, prepodavatel: str) -> str:
    """Форматирует строку расписания с использованием смайликов."""
    # Словарь смайликов для разных предметов (можешь расширить!)
    emoji_for_subject = {
        "Математика": "📐",
        "Физика": "🧪",
        "Информатика": "💻",
        "История": "📜",
        "Английский": "🇬🇧",
        "Физкультура": "🏃‍♂️",
        "Программирование": "👨‍💻",
        "Практика": "🛠️",  # Добавим смайлик для практики
        "МДК.02.01 Монтаж и обслуживание инфокоммуникационных систем с коммутацией пакетов и каналов": "📡" #Смайлик для этого конкретного предмета
    }
    # Выбираем смайлик для предмета (если есть, иначе используем "книгу")
    emoji = emoji_for_subject.get(predmet, "📚")

    return f"⏰ {para} - {predmet} {emoji} (ауд. {auditoriya}) 👨‍🏫 {prepodavatel}\n"

def get_schedule(group: str) -> str:
    """
    Получает расписание для указанной группы с сайта колледжа на сегодня.
    """
    logger.info(f"Попытка получения расписания для группы: {group} с сайта: {SCHEDULE_WEBSITE_URL} на сегодня")

    today = datetime.date.today().strftime("%d.%m.%Y")

    schedule_text = f"Не удалось получить расписание для группы **{group}** на сегодня. 😞"

    try:
        # --- 1. ЗАПРАШИВАЕМ СТРАНИЦУ СО СПИСКОМ ГРУПП ---
        response = requests.get(SCHEDULE_WEBSITE_URL)
        response.raise_for_status()  # Проверяем на ошибки HTTP

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- 2. ИЩЕМ ССЫЛКУ НА СТРАНИЦУ ГРУППЫ ---
        group_link = None
        # Ищем все ссылки с классом 'modernsmall'
        for link in soup.find_all('a', class_='modernsmall'):
            # Если текст ссылки содержит название группы (без учета регистра)
            if group.upper() in link.text.upper():
                # Это нужная ссылка!
                group_link = link
                logger.info(f"Найдена ссылка на расписание для группы {group}: {link['href']}")
                break  # Выходим из цикла, нашли первую подходящую ссылку

        if group_link:
            # Ссылка на группу найдена!
            # Получаем URL из атрибута href
            group_url = group_link['href']
            # Составляем полный URL (если href относительный)
            if not group_url.startswith("http"):
                 group_url = BASE_URL + group_url # Добавляем базовый URL

            logger.info(f"Переход по ссылке для получения расписания: {group_url}")

            # --- 3. ЗАПРАШИВАЕМ СТРАНИЦУ РАСПИСАНИЯ ДЛЯ ГРУППЫ ---
            schedule_response = requests.get(group_url)
            schedule_response.raise_for_status()
            schedule_soup = BeautifulSoup(schedule_response.text, 'html.parser')

             # --- 4. ПАРСИМ СТРАНИЦУ С РАСПИСАНИЕМ (view.php?id=...) ---
            # !!! Вот тут нужно изучить HTML-код страницы view.php?id=...
            # и написать код, который будет извлекать расписание.
            # 1. Получаем текущую дату в нужном формате (как на сайте)

            logger.info(f"Сегодняшняя дата: {today}")

            # 1. Находим таблицу (без класса или id)
            schedule_table = schedule_soup.find('table')
            if schedule_table:
                schedule_text = ""
                current_day = ""
                today_found = False #Флаг, показывающий, нашли ли мы сегодня

                # 2. Идем по строкам таблицы
                for row in schedule_table.find_all('tr'):
                    #Проверяем, нашли ли мы уже сегодня
                    if not today_found:
                        #Если еще не нашли - ищем строку с сегодняшней датой
                        date_cell = row.find('td', attrs={'colspan': '5', 'align': 'center', 'bgcolor': '#E0FFFF'})
                        if date_cell:
                            day = date_cell.text.strip()
                            if today in day:
                                #Сегодняшняя дата найдена!
                                today_found = True
                                schedule_text += f"\n📅 {day}\n"
                                current_day = day #Запоминаем текущий день
                                logger.info(f"Найдено расписание на сегодня ({day})")
                            else:
                                #Это не сегодня - пропускаем
                                continue

                    else:
                        #Если сегодня уже нашли - ищем расписание до следующей даты
                        date_cell = row.find('td', attrs={'colspan': '5', 'align': 'center', 'bgcolor': '#E0FFFF'})
                        if date_cell:
                            #Это строка с днем недели - значит, расписание на сегодня закончилось
                            logger.info(f"Расписание на сегодня закончено.")
                            break
                        elif row.has_attr('class') and 'shadow' in row['class'] and row.has_attr('bgcolor') and row['bgcolor'] == 'yellow':
                            #Это строка с данными о занятии
                            cells = row.find_all('td')
                            if len(cells) == 5:
                                #Извлекаем данные из ячеек
                                para = cells[0].text.strip()
                                predmet = cells[1].text.strip()
                                auditoriya = cells[2].text.strip()
                                prepodavatel = cells[3].text.strip()
                                #podgruppa = cells[4].text.strip() #Не используем
                                #Форматируем строку и добавляем к расписанию
                                schedule_text += format_schedule(para, predmet, auditoriya, prepodavatel)

                if not schedule_text:
                    schedule_text = f"Расписание на сегодня ({today}) не найдено. 😞" #Сообщение, если сегодня не нашли
                    logger.warning(f"Не найдено расписание на сегодня ({today}).")

            else:
                schedule_text = "Не найдена таблица с расписанием. 😞"

        else:
            # Ссылка на группу не найдена
            schedule_text = f"Не найдена ссылка на расписание для группы **{group}** на сайте. 😞"
            logger.warning(f"Не найдена ссылка для группы {group} на странице {SCHEDULE_WEBSITE_URL}.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе расписания: {e}")
        schedule_text = f"Проблема с доступом к сайту расписания. 🌐 Повтори попытку позже. 😞"
    except Exception as e:
        logger.error(f"Неизвестная ошибка при парсинге расписания для группы {group}: {e}", exc_info=True)
        schedule_text = f"Произошла внутренняя ошибка при обработке расписания для **{group}**. 🛠️"

    # Возвращаем результат
    return schedule_text


def get_week_schedule(group: str) -> str:
    """
    Получает расписание для указанной группы с сайта колледжа на ближайшую неделю.
    """
    logger.info(f"Попытка получения расписания для группы: {group} с сайта: {SCHEDULE_WEBSITE_URL} на неделю")

    today = datetime.date.today()
    schedule_text = f"Не удалось получить расписание для группы **{group}** на неделю. 😞"

    try:
        # --- 1. ЗАПРАШИВАЕМ СТРАНИЦУ СО СПИСКОМ ГРУПП ---
        response = requests.get(SCHEDULE_WEBSITE_URL)
        response.raise_for_status()  # Проверяем на ошибки HTTP

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- 2. ИЩЕМ ССЫЛКУ НА СТРАНИЦУ ГРУППЫ ---
        group_link = None
        # Ищем все ссылки с классом 'modernsmall'
        for link in soup.find_all('a', class_='modernsmall'):
            # Если текст ссылки содержит название группы (без учета регистра)
            if group.upper() in link.text.upper():
                # Это нужная ссылка!
                group_link = link
                logger.info(f"Найдена ссылка на расписание для группы {group}: {link['href']}")
                break  # Выходим из цикла, нашли первую подходящую ссылку

        if group_link:
            # Ссылка на группу найдена!
            # Получаем URL из атрибута href
            group_url = group_link['href']
            # Составляем полный URL (если href относительный)
            if not group_url.startswith("http"):
                 group_url = BASE_URL + group_url # Добавляем базовый URL

            logger.info(f"Переход по ссылке для получения расписания: {group_url}")

            # --- 3. ЗАПРАШИВАЕМ СТРАНИЦУ РАСПИСАНИЯ ДЛЯ ГРУППЫ ---
            schedule_response = requests.get(group_url)
            schedule_response.raise_for_status()
            schedule_soup = BeautifulSoup(schedule_response.text, 'html.parser')

             # --- 4. ПАРСИМ СТРАНИЦУ С РАСПИСАНИЕМ (view.php?id=...) ---
            # !!! Вот тут нужно изучить HTML-код страницы view.php?id=...
            # и написать код, который будет извлекать расписание.

            logger.info(f"Сегодняшняя дата: {today}")

            # 1. Находим таблицу (без класса или id)
            schedule_table = schedule_soup.find('table')
            if schedule_table:
                schedule_text = ""
                current_day = None  # Храним текущую дату

                # 2. Идем по строкам таблицы
                for row in schedule_table.find_all('tr'):
                    # Проверяем, является ли строка строкой с датой
                    date_cell = row.find('td', attrs={'colspan': '5', 'align': 'center', 'bgcolor': '#E0FFFF'})
                    if date_cell:
                        day_text = date_cell.text.strip()
                        try:
                            # Пытаемся извлечь дату из строки
                            date_str = day_text.split(' - ')[0]  # Извлекаем "06.06.2025" из "06.06.2025 - Пятница"
                            day = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
                        except ValueError:
                            # Если не получилось преобразовать в дату, пропускаем
                            continue

                        # Проверяем, входит ли дата в ближайшие 7 дней
                        if today <= day <= today + datetime.timedelta(days=6):
                            schedule_text += f"\n📅 {day_text}\n"  # Добавляем дату в расписание
                            current_day = day  # Запоминаем текущую дату
                            logger.info(f"Найдено расписание на ({day_text})")
                        else:
                            current_day = None  # Сбрасываем текущую дату, если она не входит в неделю

                    elif row.has_attr('class') and 'shadow' in row['class'] and row.has_attr('bgcolor') and row['bgcolor'] == 'yellow' and current_day:
                        # Это строка с данными о занятии и у нас есть текущая дата
                        cells = row.find_all('td')
                        if len(cells) == 5:
                            # Извлекаем данные из ячеек
                            para = cells[0].text.strip()
                            predmet = cells[1].text.strip()
                            auditoriya = cells[2].text.strip()
                            prepodavatel = cells[3].text.strip()
                            # podgruppa = cells[4].text.strip() #Не используем
                            # Форматируем строку и добавляем к расписанию
                            schedule_text += format_schedule(para, predmet, auditoriya, prepodavatel)

                if not schedule_text:
                     schedule_text = "Расписание на неделю не найдено. 😞"

            else:
                schedule_text = "Не найдена таблица с расписанием. 😞"

        else:
            # Ссылка на группу не найдена
            schedule_text = f"Не найдена ссылка на расписание для группы **{group}** на сайте. 😞"
            logger.warning(f"Не найдена ссылка для группы {group} на странице {SCHEDULE_WEBSITE_URL}.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе расписания: {e}")
        schedule_text = f"Проблема с доступом к сайту расписания. 🌐 Повтори попытку позже. 😞"
    except Exception as e:
        logger.error(f"Неизвестная ошибка при парсинге расписания для группы {group}: {e}", exc_info=True)
        schedule_text = f"Произошла внутренняя ошибка при обработке расписания для **{group}**. 🛠️"

    return schedule_text
