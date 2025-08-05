import telebot
from telebot import types
import datetime
import os
from pytz import timezone

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Настройки ---

TOKEN = '7610927179:AAGMN_yfjCMS0AF7500KtJPGTZ1BjASbA3I'  # Ваш токен
SPREADSHEET_ID = '1bQUel2u51J7P2StDiq1o7PjAWCovB8SaShOvmNBYmLk'  # ID таблицы
CREDS_FILE = 'telegrambotproject-467921-e103d3d39eea.json'  # JSON сервисного аккаунта
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

if not os.path.isfile(CREDS_FILE):
    print(f"Файл учетных данных '{CREDS_FILE}' не найден.")
    exit(1)

creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

bot = telebot.TeleBot(TOKEN)

# --- Приватный доступ ---

ALLOWED_USERS = ['freyott', 'Dre1em4']  # без '@'

def check_user_access(func):
    def wrapper(message, *args, **kwargs):
        username = message.from_user.username
        if username not in ALLOWED_USERS:
            bot.reply_to(message, "Извините, бот доступен только ограниченному кругу пользователей.")
            return
        return func(message, *args, **kwargs)
    return wrapper

# --- Вспомогательные функции ---

def parse_time_value(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return val * 24 if val <= 1 else float(val)
    val = str(val).strip()
    if '.' in val:
        parts = val.split('.')
        if len(parts) == 2:
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
                if minutes >= 60:
                    return float(val)
                return hours + minutes / 60
            except:
                pass
    if ':' in val:
        parts = val.split(':')
        if len(parts) == 2:
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
                return hours + minutes / 60
            except:
                pass
    try:
        return float(val.replace(',', '.'))
    except:
        pass
    return 0.0

def format_hours_to_text(hours_float):
    total_seconds = int(round(hours_float * 3600))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    parts = []
    if hours > 0:
        parts.append(f"{hours} час{'ов' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} минут{'ы' if minutes != 1 else ''}")
    if not parts:
        return "0 минут"
    return " ".join(parts)

def parse_date_with_two_formats(date_str):
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def get_last_date_row():
    msk_tz = timezone('Europe/Moscow')
    today = datetime.datetime.now(msk_tz).date()
    dates_res = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='A7:A47').execute()
    dates = dates_res.get('values', [])
    last_row = 6
    for i, row in enumerate(dates, start=7):
        if not row:
            continue
        dt = parse_date_with_two_formats(row[0])
        if dt is None:
            continue
        if dt.date() <= today:
            last_row = i
        else:
            break
    return last_row

# --- Клавиатуры ---

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('Добавить онлайн', 'Общая статистика', 'Личная статистика')
    keyboard.row('Ответы', 'Помощь команд')
    return keyboard

def back_to_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("Главное меню")
    return keyboard

def nick_choice_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("Ilya_Lanskih", "Tom_Bananov")
    keyboard.row("Главное меню")
    return keyboard

def confirm_cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("Подтвердить", "Отменить")
    keyboard.row("Главное меню")
    return keyboard

def choose_action_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("+z", "-z")
    keyboard.row("+pm", "-pm")
    keyboard.row("+z(польз)", "-z(польз)")
    keyboard.row("+pm(польз)", "-pm(польз)")
    keyboard.row("Главное меню")
    return keyboard

# --- Состояния пользователей ---

user_online_data = {}
user_get_state = {}
user_states = {}
user_help_state = {}

# --- Добавить онлайн (многошаговый ввод) ---

@bot.message_handler(func=lambda m: m.text == 'Добавить онлайн')
@check_user_access
def add_online_start(message):
    user_online_data[message.from_user.id] = {'step': 'choose_nick'}
    bot.send_message(message.chat.id, "Выберите никнейм:", reply_markup=nick_choice_keyboard())

@bot.message_handler(func=lambda m: user_online_data.get(m.from_user.id, {}).get('step') == 'choose_nick')
@check_user_access
def add_online_nick_chosen(message):
    text = message.text
    if text == "Главное меню":
        user_online_data.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Возвращаемся в главное меню.", reply_markup=main_keyboard())
        return
    if text not in ("Ilya_Lanskih", "Tom_Bananov"):
        bot.send_message(message.chat.id, "Выберите ник из списка!", reply_markup=nick_choice_keyboard())
        return
    user_online_data[message.from_user.id]['nickname'] = text
    user_online_data[message.from_user.id]['step'] = 'input_date'
    bot.send_message(message.chat.id, "Введите дату (ДД.MM.ГГГГ или ДД.MM.ГГ):", reply_markup=back_to_main_keyboard())

@bot.message_handler(func=lambda m: user_online_data.get(m.from_user.id, {}).get('step') == 'input_date')
@check_user_access
def add_online_date_input(message):
    text = message.text
    if text == "Главное меню":
        user_online_data.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Возвращаемся в меню.", reply_markup=main_keyboard())
        return
    date_obj = parse_date_with_two_formats(text)
    if date_obj is None:
        bot.send_message(message.chat.id, "Неверный формат даты! Попробуйте ещё раз:", reply_markup=back_to_main_keyboard())
        return
    user_online_data[message.from_user.id]['date'] = text
    user_online_data[message.from_user.id]['step'] = 'input_time'
    bot.send_message(message.chat.id, "Введите количество отыгранных часов (например, 3.20 или 3:20):", reply_markup=back_to_main_keyboard())

@bot.message_handler(func=lambda m: user_online_data.get(m.from_user.id, {}).get('step') == 'input_time')
@check_user_access
def add_online_time_input(message):
    text = message.text
    if text == "Главное меню":
        user_online_data.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Возвращаемся в меню.", reply_markup=main_keyboard())
        return
    time_val = parse_time_value(text)
    if time_val == 0.0:
        bot.send_message(message.chat.id, "Время не распознано или = 0. Введите корректное время:", reply_markup=back_to_main_keyboard())
        return
    user_online_data[message.from_user.id]['time'] = time_val
    d = user_online_data[message.from_user.id]
    time_text = format_hours_to_text(d['time'])
    summary = (f"Проверьте введённые данные:\n"
               f"Ник: {d['nickname']}\n"
               f"Дата: {d['date']}\n"
               f"Время онлайн: {time_text}")
    user_online_data[message.from_user.id]['step'] = 'confirm'
    bot.send_message(message.chat.id, summary, reply_markup=confirm_cancel_keyboard())

@bot.message_handler(func=lambda m: user_online_data.get(m.from_user.id, {}).get('step') == 'confirm')
@check_user_access
def add_online_confirm_or_cancel(message):
    text = message.text
    if text in ("Главное меню", "Отменить"):
        user_online_data.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Данные отменены. Возвращаемся в меню.", reply_markup=main_keyboard())
        return
    if text == "Подтвердить":
        d = user_online_data.get(message.from_user.id)
        if not d:
            bot.send_message(message.chat.id, "Произошла ошибка, начните заново.", reply_markup=main_keyboard())
            return
        nickname = d['nickname']
        date_str = d['date']
        time_val = d['time']
        col_letter = 'B' if nickname == 'Ilya_Lanskih' else 'E'
        date_obj = parse_date_with_two_formats(date_str)
        if not date_obj:
            bot.send_message(message.chat.id, "Ошибка с датой. Начните заново.", reply_markup=main_keyboard())
            user_online_data.pop(message.from_user.id, None)
            return
        date_range = 'A7:A47'
        result_dates = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=date_range).execute()
        dates_in_sheet = result_dates.get('values', [])
        row_index = None
        for i, row in enumerate(dates_in_sheet, start=7):
            if not row:
                continue
            try:
                current_date_obj = parse_date_with_two_formats(row[0])
                if current_date_obj == date_obj:
                    row_index = i
                    break
            except:
                pass
        if row_index is None:
            bot.send_message(message.chat.id, f"Дата '{date_str}' не найдена. Начните заново.", reply_markup=main_keyboard())
            user_online_data.pop(message.from_user.id, None)
            return
        cell_address = f"{col_letter}{row_index}"
        time_as_days = time_val / 24
        body = {'values': [[time_as_days]]}
        try:
            sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=cell_address, valueInputOption='USER_ENTERED', body=body).execute()
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при сохранении: {e}", reply_markup=main_keyboard())
            user_online_data.pop(message.from_user.id, None)
            return
        bot.send_message(message.chat.id,
                         f"Данные сохранены:\nНик: {nickname}\nДата: {date_str}\nВремя онлайн: {format_hours_to_text(time_val)}",
                         reply_markup=main_keyboard())
        user_online_data.pop(message.from_user.id, None)
        return
    bot.send_message(message.chat.id, "Нажмите кнопку «Подтвердить» или «Отменить».", reply_markup=confirm_cancel_keyboard())

# --- Общая статистика ---

@bot.message_handler(func=lambda m: m.text == 'Общая статистика')
@check_user_access
def overall_stats(message):
    try:
        last_row = get_last_date_row()
        if last_row < 7:
            bot.send_message(message.chat.id, "Нет данных по датам до сегодня.")
            return

        ranges = {
            'ilya_time': f'B7:D{last_row}',
            'tom_time': f'E7:G{last_row}',
            'ilya_z': f'H7:H{last_row}',
            'ilya_pm': f'I7:I{last_row}',
            'tom_z': f'J7:J{last_row}',
            'tom_pm': f'K7:K{last_row}'
        }
        data = {}
        for key, rng in ranges.items():
            res = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=rng, valueRenderOption='UNFORMATTED_VALUE').execute()
            data[key] = res.get('values', [])

        def sum_time(matrix):
            total = 0.0
            for row in matrix:
                for val in row:
                    total += parse_time_value(val)
            return total

        def sum_col(values):
            total = 0
            for row in values:
                try:
                    if row and row[0] != '':
                        total += int(float(row[0]))
                except:
                    continue
            return total

        ilya_time_total = sum_time(data['ilya_time'])
        tom_time_total = sum_time(data['tom_time'])
        ilya_z_total = sum_col(data['ilya_z'])
        ilya_pm_total = sum_col(data['ilya_pm'])
        tom_z_total = sum_col(data['tom_z'])
        tom_pm_total = sum_col(data['tom_pm'])

        response = (f"Общая статистика:\n"
                    f"Ilya_Lanskih: {format_hours_to_text(ilya_time_total)} | {ilya_z_total} z | {ilya_pm_total} pm\n"
                    f"Tom_Bananov: {format_hours_to_text(tom_time_total)} | {tom_z_total} z | {tom_pm_total} pm")

        bot.send_message(message.chat.id, response)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при получении статистики: {e}")

# --- Личная статистика ---

@bot.message_handler(func=lambda m: m.text == 'Личная статистика')
@check_user_access
def personal_stats_start(message):
    user_get_state[message.from_user.id] = {'stage': 'awaiting_nick'}
    keyboard = nick_choice_keyboard()
    bot.send_message(message.chat.id, "Выберите ник для просмотра личной статистики:", reply_markup=keyboard)

@bot.message_handler(func=lambda m: user_get_state.get(m.from_user.id, {}).get('stage') == 'awaiting_nick')
@check_user_access
def personal_stats_choose_nick(message):
    text = message.text
    if text == "Главное меню":
        user_get_state.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Возвращаемся в главное меню.", reply_markup=main_keyboard())
        return
    if text not in ["Ilya_Lanskih", "Tom_Bananov"]:
        bot.send_message(message.chat.id, "Выберите ник из меню.", reply_markup=nick_choice_keyboard())
        return
    nickname = text
    user_get_state[message.from_user.id]['stage'] = None

    last_row = get_last_date_row()
    if last_row < 7:
        bot.send_message(message.chat.id, "Нет данных для выбранного ника.")
        return

    if nickname == 'Ilya_Lanskih':
        col_start, col_end = 'B', 'D'
        col_z = 'H'
        col_pm = 'I'
    else:
        col_start, col_end = 'E', 'G'
        col_z = 'J'
        col_pm = 'K'

    value_range = f"{col_start}7:{col_end}{last_row}"
    values_result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=value_range, valueRenderOption='UNFORMATTED_VALUE').execute()
    values_matrix = values_result.get('values', [])

    z_range = f"{col_z}7:{col_z}{last_row}"
    z_result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=z_range, valueRenderOption='UNFORMATTED_VALUE').execute()
    z_values = z_result.get('values', [])

    pm_range = f"{col_pm}7:{col_pm}{last_row}"
    pm_result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=pm_range, valueRenderOption='UNFORMATTED_VALUE').execute()
    pm_values = pm_result.get('values', [])

    dates_result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=f'A7:A{last_row}').execute()
    dates = dates_result.get('values', [])

    response = f"Личная статистика для {nickname}:\n\nДата | Время онлайн | z | pm\n"
    for i, date_row in enumerate(dates):
        if i >= len(values_matrix):
            break
        date_str = date_row[0] if date_row else '-'
        val = 0.0
        if i < len(values_matrix):
            row = values_matrix[i]
            if row:
                val = parse_time_value(row[0])
                time_text = format_hours_to_text(val) if val > 0 else "-"
            else:
                time_text = "-"
        else:
            time_text = "-"
        z_val = "-"
        if i < len(z_values):
            try:
                z_tmp = int(float(z_values[i][0]))
                z_val = str(z_tmp)
            except:
                pass
        pm_val = "-"
        if i < len(pm_values):
            try:
                pm_tmp = int(float(pm_values[i][0]))
                pm_val = str(pm_tmp)
            except:
                pass
        response += f"{date_str} | {time_text} | {z_val} | {pm_val}\n"

    bot.send_message(message.chat.id, response, reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row("Главное меню"))

# --- Меню "Ответы" ---

def get_msk_date_row():
    msk_tz = timezone('Europe/Moscow')
    now_msk = datetime.datetime.now(msk_tz).date()
    dates_res = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='A7:A46').execute()
    dates = dates_res.get('values', [])
    for i, row in enumerate(dates, start=7):
        if not row:
            continue
        dt = parse_date_with_two_formats(row[0])
        if dt and dt.date() == now_msk:
            return i
    return None

def update_answer_value(nickname, column_letter, delta):
    row_num = get_msk_date_row()
    if row_num is None:
        return None
    cell = f"{column_letter}{row_num}"
    try:
        current_val_result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=cell).execute()
        current_values = current_val_result.get('values', [])
        current_val = 0
        if current_values and current_values[0]:
            current_val = int(float(current_values[0][0]))
    except Exception as e:
        print(f"Ошибка чтения {cell}: {e}")
        return None
    new_val = current_val + delta
    if new_val < 0:
        new_val = 0
    body = {'values': [[new_val]]}
    try:
        sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=cell, valueInputOption='USER_ENTERED', body=body).execute()
        return new_val
    except Exception as e:
        print(f"Ошибка обновления {cell}: {e}")
        return None

@bot.message_handler(func=lambda m: m.text == 'Ответы')
@check_user_access
def answers_start(message):
    user_states[message.from_user.id] = {'stage': 'awaiting_nick', 'nickname': None}
    bot.send_message(message.chat.id, "Выберите ник:", reply_markup=nick_choice_keyboard())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('stage') == 'awaiting_nick')
@check_user_access
def answers_choose_nick(message):
    text = message.text
    if text == 'Главное меню':
        user_states.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "В главное меню.", reply_markup=main_keyboard())
        return
    if text not in ['Ilya_Lanskih', 'Tom_Bananov']:
        bot.send_message(message.chat.id, "Выберите ник из меню.", reply_markup=nick_choice_keyboard())
        return
    user_states[message.from_user.id]['nickname'] = text
    user_states[message.from_user.id]['stage'] = 'awaiting_action'
    bot.send_message(message.chat.id, f"Ник {text} выбран. Выберите действие:", reply_markup=choose_action_keyboard())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('stage') == 'awaiting_action')
@check_user_access
def answers_choose_action(message):
    text = message.text
    if text == 'Главное меню':
        user_states.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "В главное меню.", reply_markup=main_keyboard())
        return

    nickname = user_states[message.from_user.id]['nickname']
    col_map = {
        "Ilya_Lanskih": {"z": "H", "pm": "I"},
        "Tom_Bananov": {"z": "J", "pm": "K"},
    }

    if text in ["+z", "-z", "+pm", "-pm"]:
        sign = 1 if text.startswith("+") else -1
        answer_type = "z" if "z" in text else "pm"
        column = col_map[nickname][answer_type]

        new_val = update_answer_value(nickname, column, sign)
        if new_val is None:
            bot.send_message(message.chat.id, "Ошибка при обновлении данных. Попробуйте позже.")
            return

        bot.send_message(message.chat.id,
                         f"Для {nickname} в столбце '{answer_type}' значение изменено на {new_val}.\nВыберите следующее действие или главное меню.",
                         reply_markup=choose_action_keyboard())

    elif text in ["+z(польз)", "-z(польз)", "+pm(польз)", "-pm(польз)"]:
        sign = 1 if text.startswith("+") else -1
        answer_type = "z" if "z" in text else "pm"

        user_states[message.from_user.id]['stage'] = 'awaiting_custom_amount'
        user_states[message.from_user.id]['answer_type'] = answer_type
        user_states[message.from_user.id]['sign'] = sign

        bot.send_message(message.chat.id, f"Введите количество для {'увеличения' if sign>0 else 'уменьшения'} {answer_type} для {nickname} (целое число):", reply_markup=back_to_main_keyboard())

    else:
        bot.send_message(message.chat.id, "Выберите действие из меню.", reply_markup=choose_action_keyboard())

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('stage') == 'awaiting_custom_amount')
@check_user_access
def answers_custom_amount_enter(message):
    text = message.text
    if text == "Главное меню":
        user_states.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Возвращаемся в главное меню.", reply_markup=main_keyboard())
        return
    try:
        amount = int(text)
        if amount <= 0:
            raise ValueError()
    except:
        bot.send_message(message.chat.id, "Введите корректное положительное целое число:", reply_markup=back_to_main_keyboard())
        return

    state = user_states[message.from_user.id]
    nickname = state['nickname']
    answer_type = state['answer_type']
    sign = state['sign']

    delta = sign * amount
    col_map = {
        "Ilya_Lanskih": {"z": "H", "pm": "I"},
        "Tom_Bananov": {"z": "J", "pm": "K"},
    }
    column = col_map[nickname][answer_type]

    new_val = update_answer_value(nickname, column, delta)
    if new_val is None:
        bot.send_message(message.chat.id, "Ошибка при обновлении данных. Попробуйте позже.")
    else:
        bot.send_message(message.chat.id,
                         f"Для {nickname} в столбце '{answer_type}' значение изменено на {new_val}.\nВыберите следующее действие или главное меню.",
                         reply_markup=choose_action_keyboard())

    user_states[message.from_user.id]['stage'] = 'awaiting_action'
    user_states[message.from_user.id].pop('answer_type', None)
    user_states[message.from_user.id].pop('sign', None)

# --- Помощь команд ---

help_commands_keys = list(help_commands_dict := {
"открыть машину": "/lock 1",
"как открыть машину": "/lock 1",
"открыть дверь машины": "/lock 1",
"закрыть машину": "/lock 1",
"запереть машину": "/lock 1",
"запереть транспорт": "/lock 1",
"открыть тачку": "/lock 1",
"открыть транспорт": "/lock 1",
"рация RP": "/r",
"включить RP рацию": "/r",
"открыть RP рацию": "/r",
"использовать RP рацию": "/r",
"переключиться на рацию RP": "/r",
"рация NonRP": "/rr",
"включить NonRP рацию": "/rr",
"открыть NonRP рацию": "/rr",
"использовать NonRP рацию": "/rr",
"рация департамента RP": "/d",
"включить рацию департамента": "/d",
"открыть рацию департамента": "/d",
"рация департамента NonRP": "/dd",
"включить NonRP рацию департамента": "/dd",
"открыть NonRP рацию департамента": "/dd",
"статистика по работе": "/sc",
"показать статистику": "/sc",
"моя статистика": "/sc",
"переключить рацию": "/rc",
"сменить канал рации": "/rc",
"переключить канал в рации": "/rc",
"найти сотрудника": "/find",
"показать онлайн сотрудников": "/find",
"кто онлайн из сотрудников": "/find",
"история фракции": "/team_history",
"показать историю фракции": "/team_history",
"что произошло в фракции": "/team_history",
"выйти из фракции": "/leave",
"покинуть фракцию": "/leave",
"уйти из фракции": "/leave",
"подключиться к каналу рации": "/radio_set",
"сменить канал рации": "/radio_set",
"установить канал рации": "/radio_set",
"создать собеседование": "/add_event",
"добавить событие": "/add_event",
"создать мероприятие": "/add_event",
"форма сотрудников": "/uniforms",
"настроить форму": "/uniforms",
"изменить форму сотрудника": "/uniforms",
"пригласить во фракцию": "/invite [ID]",
"добавить в фракцию": "/invite [ID]",
"взять в фракцию": "/invite [ID]",
"уволить из фракции": "/uninvite [ID]",
"исключить из фракции": "/uninvite [ID]",
"уволить оффлайн": "/uninviteoff [nick]",
"исключить оффлайн": "/uninviteoff [nick]",
"изменить форму": "/changeskin [ID]",
"сменить скин": "/changeskin [ID]",
"изменить ранг": "/rang [ID]",
"повысить ранг": "/rang [ID]",
"понизить ранг": "/rang [ID]",
"черный список": "/blist",
"список заблокированных": "/blist",
"выдать выговор": "/fwarn [ID] [причина]",
"дать предупреждение": "/fwarn [ID] [причина]",
"снять выговор": "/unfwarn [ID]",
"выдать мут": "/r_mute [ID] время причина",
"снять мут": "/r_mute [ID] 0 причина",
"поданные заявки на вступление": "/r_list",
"сделать объявление во фракции": "/t_notify",
"список всех сотрудников": "/showall",
"меню фракционного транспорта": "/teamcar",
"продать фракционный транспорт": "/sellteamcar",
"ограничить увольнения замам": "/tmenu",
"менеджер каналов рации": "/radio_manage",
"список лицензёров": "/liclist",
"список адвокатов": "/adlist",
"список сотрудников для медкарты": "/medlist",
"меню советника": "/smenu",
"выдать лицензию": "/givelic [id] [тип] [сумма]",
"выпустить из тюрьмы или КПЗ": "/free [id] [сумма]",
"запустить изъятие собственности": "/debtorsell",
"список должников": "/debtorlist",
"казна фракции": "/tbank",
"сделать оружие / добавить патроны": "/makegun [id оружия] [кол-во патронов]",
"управление складами": "/warehouse",
"выдать военный билет": "/vb [ID] +",
"забрать военный билет": "/vb [ID] -",
"занять койку в больнице": "/med",
"выписать пациента": "/out [id]",
"выдать медкарту": "/medcard [id]",
"вылечить игрока в машине": "/heal [id] [цена]",
"вылечить игрока в больнице": "/medhelp [id] [цена]",
"понизить наркозависимость": "/medhelpdrug [id] [цена]",
"сменить пол игроку": "/changesex [id] [стоимость операции]",
"выбор волны вещания": "/radio",
"рейтинг сотрудников": "/topedit",
"начать редактирование объявления": "/edit",
"показать очереди объявлений": "/all",
"личное подключение к эфиру": "/efir",
"подключить игрока к эфиру": "/bring [ID]",
"отправить сообщение в эфир": "/t [текст]",
"полицейский планшет": "/police_tablet",
"список подозреваемых": "/wanted",
"отметить подозреваемого на карте": "/setmark [id]",
"говорить через мегафон": "/m [текст]",
"настройка постов": "/post",
"список сотрудников на постах": "/post_find",
"начать/окончить погоню": "/pg [id]",
"выписать штраф": "/ticket [id] [сумма] [причина]",
"забрать лицензию на вождение": "/takelic [id] [причина]",
"надеть наручники": "/cuff [id]",
"снять наручники": "/uncuff [id]",
"вести преступника": "/escort [id]",
"объявить в розыск": "/su [id]",
"снять розыск": "/clear [id]",
"выкинуть из закрытого авто": "/ejectout [id]",
"посадить в патрульную машину": "/putpl [id]",
"посадить в КПЗ": "/arrest [id]",
"обыскать игрока": "/search [id]",
"поставить ограждение": "/break [id ограждения 1-7]",
"убрать ограждение": "/dbreak [номер над ограждением]",
"отбуксировать автомобиль": "/at",
"взаимодействие со взводами": "/department",
"взломать дверь дома/бизнеса": "/break_door",
"вызвать подмогу": "/bk",
"достать документы": "/checkdocs",
"выдать разрешение адвокату": "/setfree",
"настройка причин розыска": "/su_reasons",
"заправить водой транспорт": "/pour_water",
"перелить воду между транспортами": "/trans_water [ID] [количество]",
"информация о пожарах": "/fires",
"вести заключенного за собой": "/escort [id]",
"открыть/закрыть дверь тюремной клетки": "/cell",
"начать перевозку из КПЗ в тюрьму": "/to_prison [id]",
"просмотреть досье заключенного": "/jail_info [id]",
"изменить тюремный срок": "/jail_time [id] [-или+] [время в минутах]",
"изъять наркотики или патроны": "/remove [id] [(наркотики) или (патроны)]",
"обыскать заключенного": "/search [id]",
"RP рация": "/fm",
"NonRP рация": "/nfm",
"продать наркотики": "/selldrugs [id] [кол-во] [цена]",
"убрать информационный таймер капта": "/capture_timer",
"сделать отмычку": "/makekey",
"взломать двери или двигатель автомобиля": "/hacking",
"список авто для угона": "/steal_cars",
"покинуть банду": "/family_leave",
"связать/развязать игрока": "/tie [id]",
"надеть мешок на голову": "/bag [id]",
"совершить ограбление инкассаторской машины": "/robbery",
"меню управления транспортом банды": "/gang_cars",
"открыть/закрыть склад": "/close",
"пригласить в банду": "/invite",
"уволить из банды": "/uninvite",
"изменить ранг участника банды": "/frank",
"начать захват бизнеса": "/capture_biz",
"добавить автомобиль в банду": "/gang_car",
"переделать дом под базу банды": "/gang_spawn",
"полностью расформировать банду": "/family_delete",
"RP рация между дальнобойщиками": "/r",
"NonRP рация между дальнобойщиками": "/rr",
"меню дальнобойщика": "/jmenu",
"начать работу внештатным дальнобойщиком": "/trucker",
"заказы продуктов для бизнеса": "/bizlist",
"заказы топлива для АЗС": "/fuellist",
"личная информация сотрудника ТК": "/tpass",
"управление автопарком ТК": "/jcars",
"занять игровой стол в казино в качестве крупье": "/take_table",
"управление музыкой в клубе": "/music",
"совершить обмен имуществом": "/exchange [id] [id]",
"поднять мёртвую утку": "/take_duck",
"меню управления транспортом": "/car",
"отметить личный транспорт на карте": "/getmycar",
"показать документы транспорта (технический паспорт)": "/carpass [id]",
"включить/заглушить двигатель": "/e",
"управление ключом зажигания": "/key",
"открыть капот/багажник": "/b",
"управление багажником": "/trunk",
"управление фарами": "/L",
"пристегнуть/отстегнуть ремень безопасности": "/rem (/belt)",
"дать/забрать ключи от транспорта": "/allow",
"припарковать личный транспорт": "/park",
"заправить транспорт на АЗС": "/i",
"заправить электромобиль на зарядной станции": "/ic",
"помыть автомобиль на автомойке": "/washing",
"управление сигнализацией": "/alarm",
"разорвать договор аренды": "/unrent",
"управление музыкой в транспорте (сабвуфер)": "/carmusic",
"управление лимитом скорости (круиз-контроль)": "/limit",
"выкинуть игрока из транспорта": "/eject [id]",
"меню управления пневмоподвеской": "/spanel",
"изменить отображаемую цену продажи": "/cm_price",
"предложить тест-драйв": "/cm_test_drive",
"продать автомобиль игроку": "/sellmycar [id] [сумма]",
"выбрать место появления (дом/квартира/гостиница)": "/setspawn",
"возврат части денег при изъятии имущества за неуплату": "/returnmoney",
"выйти из интерьера имущества": "/exit",
"меню аукциона": "/auction",
"информация и управление домом/квартирой": "/home",
"продажа дома/квартиры государству": "/sellhome",
"продажа дома/квартиры игроку": "/sellmyhome [id] [сумма]",
"подселить игрока": "/live [id] [дни] [цена за день]",
"покинуть совместное проживание": "/liveout",
"управление шкафом": "/use",
"удалить одежду из шкафа": "/dellskin",
"перенести шкаф в другое место": "/makestore",
"выбрать дом/квартиру в качестве базы банды": "/gang_spawn",
"управление подземным паркингом": "/parking",
"панель управления домом на колесах": "/mhouse",
"информация о гостинице": "/hotel",
"закрыть/открыть личный номер в гостинице": "/homelock",
"информация и управление гаражом": "/garage",
"покупка гаража у государства": "/buygarage",
"продажа гаража государству": "/sellgarage",
"продажа гаража игроку": "/sellmygarage [id] [сумма]",
"управление огородом": "/garden",
"покупка огорода по государственной цене": "/buygarden",
"продажа огорода игроку": "/sellgarden [id] [сумма]",
"изменить название киоска": "/changestallname",
"продажа киоска государству": "/sellstall",
"продажа киоска игроку": "/sellmystall [id] [сумма]",
"вернуть снятый с продажи предмет": "/return_items",
"управление бизнесом": "/business",
"покупка бизнеса по государственной цене": "/buybiz",
"продажа бизнеса игроку": "/sellmybiz [id] [сумма]",
"продажа бизнеса государству": "/sellbiz",
"редактирование объекта": "/pa_edit",
"управление музыкой при входе в бизнес": "/bizmusic",
"принять игрока в бизнес": "/invite [id]",
"уволить сотрудника из бизнеса": "/uninvite [id]",
"повысить сотрудника": "/b_rank [id]",
"основное меню игрока": "/menu",
"навигатор": "/gps",
"связь с администрацией": "/report",
"вопросы и ответы": "/faq",
"помощь и подсказки по игре": "/help",
"OOC (NonRP чат)": "/n [текст]",
"описание RP действий от первого лица": "/me [действие]",
"описание RP действия в настоящем времени": "/do [действие]",
"отыгровка RP действий в спорных ситуациях (удачно/неудачно)": "/try [действие]",
"отыгровка RP действий во время разговора": "/todo [действие]*[текст]",
"кричать": "/s [текст]",
"шептать": "/w [текст]",
"список наград из колеса фортуны": "/fwstore",
"список сотрудников для выдачи медкарты": "/medlist",
"список наказаний за 2 месяца от администрации": "/alist",
"список ваших активных предупреждений": "/warns",
"список анимаций": "/anim",
"список запланированных собеседований и мероприятий": "/events",
"список лицензеров в сети": "/liclist",
"список адвокатов в сети": "/adlist",
"список нотариусов в сети": "/notaries",
"список актуальных штрафов за нарушение ПДД": "/mytickets",
"список игроков с самыми большими благотворительными взносами": "/charity",
"список лидеров организаций": "/leaders",
"список администрации в сети": "/admins",
"список лидеров / адвокатов / мед. персонала в дежурстве": "/onduty",
"пожать руку/помахать": "/hi [id]",
"передать предмет из инвентаря": "/give_item [id]",
"показать трудовую книжку": "/wbook [id]",
"передать деньги": "/pay [id] [сумма]",
"показать медицинскую карту": "/showmc [id]",
"посмотреть навыки работы/стрельбы из оружия": "/skill [id]",
"поцеловать игрока": "/kiss [id]",
"подарить цветы": "/present [id]",
"узнать ник игрока по ID": "/id (/name)",
"показать лицензии": "/lic",
"показать удостоверение сотрудника": "/doc [id]",
"показать паспорт": "/pass [id]",
"история ников игрока": "/history [nick]",
"краткая информация об игроке": "/info [id]",
"оценить RP уровень игрока": "/rp [id] [+или-]",
"открыть меню крафтинга": "/craft",
"снять бронежилет": "/armoff",
"показать ассортимент в супермаркете": "/buy",
"купить канистру на АЗС": "/buyfuel",
"отменить текущее предложение": "/cancel",
"использовать наркотики": "/drugs [количество]",
"открыть меню ставок в казино": "/dice",
"вернуть скин после временного": "/end",
"вернуть камеру в исходное положение на пароме": "/fixcam",
"использовать аптечку": "/healme",
"использовать петарду": "/blow",
"выйти из лобби пейнтбола": "/pb_exit",
"вернуть старые аксессуары": "/return_acces",
"надеть аксессуары": "/put_on",
"занять койку в больнице для бесплатного лечения": "/med (/hospital)",
"взаимодействовать с огнетушителем": "/fire_ext",
"временно снять аксессуары": "/reset",
"редактировать объект": "/pa_edit",
"подобрать предмет": "/take",
"надеть маску": "/mask",
"снять маску": "/maskoff",
"согласиться на предложение игрока": "/yes",
"отказаться от предложения игрока": "/no",
"управлять музыкой": "/play",
"сменить место появления при входе в игру": "/setspawn",
"разместить информационное сообщение": "/tdo",
"удалить информационное сообщение": "/tdo_delete",
"проверить время до конца наказания": "/time",
"телепортироваться на мероприятие/событие": "/tp",
"открыть меню банка": "/bank",
"открыть встроенный биндер": "/bind",
"активировать пополнение донат счёта": "/donate",
"забрать денежный набор": "/package",
"открыть меню доната": "/mn пункт Дополнительно",
"ввести промокод": "/pcode",
"посмотреть оставшееся время до получения промокода": "/plist",
"получить деньги за промокод": "/bonus",
"заключить брачный союз": "/wedding [id]",
"как поженится": "/wedding [id]",
"поженится": "/wedding [id]",
"развестись": "/divorce [id]",
"съесть еду с подноса": "/eat",
"положить еду": "/put",
"поднять еду": "/pick",
"выбрать изученный стиль боя": "/set_style",
"вызвать игрока на ринг": "/fight [id] [сумма]",
"найти соперника для тренировки": "/find_fight",
"начать тренировку": "/training_start",
"открыть меню телефона": "/phone",
"позвонить по номеру": "/call [номер]",
"отправить SMS": "/sms [номер] [текст]",
"принять вызов": "/p",
"отклонить/сбросить вызов": "/h",
"включить/выключить телефон": "/togphone",
"сделать фотографию": "/selfie",
"занести номер в чёрный список": "/phone_black [номер]",
"посмотреть на часы": "/watch",
"продать сим-карту": "/sellsim [id] [цена]",
"футбольный чат вашей команды": "/fblc",
"общий футбольный чат": "/fb_msg",
"меню футбольного клуба": "/football",
"создать футбольный матч": "/create_match",
"меню футбольного лобби": "/fb_lobby (/fbl)",
"выйти из лобби": "/fbl_exit",
"настройка позиций тренером/руководством": "/fb_match",
"билеты на матч": "/fb_ticket",
"меню бумбокса": "/boombox",
"поставить бумбокс": "/boombox_put",
"поднять бумбокс": "/boombox_pick",
"зарегистрироваться на зимнюю гонку": "/snow_race",
"зарегистрироваться на зимнюю битву": "/snow_battle",
"посмотреть результаты последнего мероприятия": "/sr_result",
"изменить количество строк в чате": "/pagesize [10-20]",
"изменить размер шрифта": "/fontsize [от -3 до 5]",
"ограничить количество кадров в секунду (FPS)": "/fpslimit [20-90]",
"отображать время рядом с сообщением в чате": "/timestamp",
"управление поворотом головы персонажа": "/headmove",
"настройка худа под широкоформатный монитор": "/hudscalefix",
"управление отображением музыкальных ссылок в чате": "/audiomsg",
"отобразить тестовый Kill List": "/testdw",
"управление песочными часами паузы около игрового имени": "/nametagstatus",
"показать ID текущего интерьера": "/interior",
"показать объём занятой памяти": "/mem",
"сохранить позицию транспорта и игрока в документ \"savedpositions\"": "/save",
"сохранить текущие координаты в документ \"rawposition\"": "/rs",
"отобразить информацию о транспорте (состояние, координаты и др.)": "/dl",
"выход из игры": "/q"
})

@bot.message_handler(func=lambda m: m.text == "Помощь команд")
@check_user_access
def help_commands_enter(message):
    user_help_state[message.from_user.id] = True
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("Главное меню")
    bot.send_message(message.chat.id,
                     "Вы в режиме Помощи команд. Введите вопрос или фразу, например: 'как открыть машину'.",
                     reply_markup=keyboard)

@bot.message_handler(func=lambda m: user_help_state.get(m.from_user.id, False))
@check_user_access
def help_commands_response(message):
    if message.text == "Главное меню":
        user_help_state.pop(message.from_user.id)
        bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_keyboard())
        return

    user_text = message.text.lower().strip()
    query_words = [word for word in user_text.split() if len(word) > 2]

    if not query_words:
        bot.send_message(message.chat.id, "Пожалуйста, введите более конкретный запрос.", reply_markup=back_to_main_keyboard())
        return

    # Собираем ключи из help_commands_keys, которые содержат хотя бы одно слово запроса
    matched_keys = []
    for key in help_commands_keys:
        key_words = set(key.split())
        if any(word in key_words for word in query_words):
            matched_keys.append(key)

    if not matched_keys:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row("Главное меню")
        bot.send_message(message.chat.id,
                         "Команда не найдена. Попробуйте уточнить запрос или нажмите «Главное меню».",
                         reply_markup=keyboard)
        return

    if len(query_words) > 1:
        # Много слов в запросе — ищем лучшее совпадение (максимум совпадающих слов)
        scored_matches = []
        query_word_set = set(query_words)
        for key in matched_keys:
            key_word_set = set(key.split())
            common = query_word_set.intersection(key_word_set)
            scored_matches.append((key, len(common)))
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        best_key = scored_matches[0][0]
        matched_command = help_commands_dict[best_key]
        related_keys = [k for k, _ in scored_matches]

        related_text = "\n\nВозможные варианты по вашему запросу:\n" + "\n".join(related_keys)
        bot.send_message(message.chat.id, f"{matched_command}{related_text}")

    else:
        # Одно слово в запросе - выводим только сокращенный список вариантов (до 7)
        guess_limit = 7
        related_keys = matched_keys[:guess_limit]
        related_text = "\nВозможные варианты по вашему запросу:\n" + "\n".join(related_keys)
        bot.send_message(message.chat.id, related_text)
# --- Главное меню ---

@bot.message_handler(func=lambda m: m.text == 'Главное меню')
def back_main_menu(message):
    user_states.pop(message.from_user.id, None)
    user_online_data.pop(message.from_user.id, None)
    user_get_state.pop(message.from_user.id, None)
    user_help_state.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Вы в главном меню.", reply_markup=main_keyboard())

# --- Обработка прочих сообщений ---

@bot.message_handler(func=lambda m: True)
def unknown_message(message):
    if message.from_user.username not in ALLOWED_USERS:
        bot.reply_to(message, "Извините, бот доступен только ограниченному кругу пользователей.")
        return
    known_cmds = ['Добавить онлайн', 'Общая статистика', 'Личная статистика', 'Ответы', 'Помощь команд']
    if message.text in known_cmds:
        if message.text == 'Добавить онлайн':
            add_online_start(message)
        elif message.text == 'Общая статистика':
            overall_stats(message)
        elif message.text == 'Личная статистика':
            personal_stats_start(message)
        elif message.text == 'Ответы':
            answers_start(message)
        elif message.text == 'Помощь команд':
            help_commands_enter(message)
    else:
        bot.send_message(message.chat.id, "Команда не распознана. Пожалуйста, выберите действие в меню.", reply_markup=main_keyboard())

# --- Запуск бота ---

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
