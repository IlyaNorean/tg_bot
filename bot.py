import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = '6587249578:AAHZCZ3_yaQn-7UwuvHw-KGdsi0dAmFM1TI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging_middleware = LoggingMiddleware()
dp.middleware.setup(logging_middleware)

# Устанавливаем соединение с базой данных SQLite
conn = sqlite3.connect('registration.db')
cursor = conn.cursor()

# Создаем таблицу для хранения данных о зарегистрированных пользователях
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (id INTEGER PRIMARY KEY, full_name TEXT, class_num TEXT, phone_number TEXT, user_id INTEGER)''')

# Создаем таблицу для хранения данных о мероприятиях
cursor.execute('''CREATE TABLE IF NOT EXISTS events 
                  (id INTEGER PRIMARY KEY, title TEXT, description TEXT, date TEXT, class_range TEXT)''')
conn.commit()

class RegistrationStates(StatesGroup):
    full_name = State()
    class_num = State()
    phone_number = State()
    menu = State()
    info_menu = State()  # Добавляем новое состояние для меню информации

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я бот для регистрации. Нажми /register чтобы зарегистрироваться.")

@dp.message_handler(commands=['register'])
async def register(message: types.Message):
    await message.answer("Введите ваше ФИО:")
    await RegistrationStates.full_name.set()

@dp.message_handler(state=RegistrationStates.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text
    async with state.proxy() as data:
        data['full_name'] = full_name
    await message.answer("Введите ваш класс:")
    await RegistrationStates.next()

@dp.message_handler(state=RegistrationStates.class_num)
async def process_class(message: types.Message, state: FSMContext):
    class_num = message.text
    async with state.proxy() as data:
        data['class_num'] = class_num
    await message.answer("Введите ваш номер телефона:")
    await RegistrationStates.next()

@dp.message_handler(state=RegistrationStates.phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    phone_number = message.text
    async with state.proxy() as data:
        data['phone_number'] = phone_number
        data['user_id'] = message.from_user.id
        # Сохраняем данные в базу данных
        cursor.execute("INSERT INTO users (full_name, class_num, phone_number, user_id) VALUES (?, ?, ?, ?)",
                       (data['full_name'], data['class_num'], data['phone_number'], data['user_id']))
        conn.commit()
    # После регистрации переходим к меню
    await message.answer("Вы успешно зарегистрированы!")
    await message.answer("Выберите пункт меню:", reply_markup=get_menu_markup())
    await RegistrationStates.menu.set()

def get_menu_markup():
    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Информация", "Анонсы", "Предложка"]
    keyboard_markup.add(*buttons)
    return keyboard_markup

@dp.message_handler(state=RegistrationStates.menu)
async def process_menu(message: types.Message, state: FSMContext):
    if message.text == "Информация":
        await message.answer("Информация о Первых 1507")
        await message.answer("Выберите нужный раздел:", reply_markup=get_info_menu_markup())
        await RegistrationStates.info_menu.set()  # Переходим к состоянию info_menu
    elif message.text == "Анонсы":
        await message.answer("Анонсы мероприятий:")
        await show_events_by_class(message)
        await message.answer("Выберите пункт меню:", reply_markup=get_menu_markup())

def get_info_menu_markup():
    inline_keyboard_markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("Волонтерский отряд «Хранители»", callback_data="volunteers"),
        types.InlineKeyboardButton("Юнармия", callback_data="yunarmia"),
        types.InlineKeyboardButton("ЮИД (Юные инспектора движения)", callback_data="yuid"),
        types.InlineKeyboardButton("Клуб «Я вожатый»", callback_data="club_vozhaty"),
        types.InlineKeyboardButton("Клуб «Вкусное чтение»", callback_data="club_reading"),
        types.InlineKeyboardButton("Школьный спортивный клуб", callback_data="school_sport"),
        types.InlineKeyboardButton("Театральная студия «Момент»", callback_data="theater_studio"),
        types.InlineKeyboardButton("Проекты Первых", callback_data="first_projects"),
        types.InlineKeyboardButton("Наши планы", callback_data="our_plans"),
        types.InlineKeyboardButton("Контакты", callback_data="contacts")
    ]
    inline_keyboard_markup.add(*buttons)
    return inline_keyboard_markup

async def show_events_by_class(message: types.Message):
    class_num = get_user_class(message.from_user.id)
    events = get_events_for_class(class_num)
    if events:
        for event in events:
            await message.answer(f"Название: {event[1]}\nОписание: {event[2]}\nДата: {event[3]}")
    else:
        await message.answer("На данный момент нет мероприятий для вашего класса.")

def get_user_class(user_id):
    cursor.execute("SELECT class_num FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

def get_events_for_class(class_num):
    cursor.execute("SELECT * FROM events WHERE class_range LIKE ?", ('%' + class_num + '%',))
    return cursor.fetchall()

@dp.callback_query_handler(lambda c: c.data.startswith('volunteers'), state=RegistrationStates.info_menu)
async def handle_volunteers(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Описание Волонтерского отряда «Хранители»")
    await RegistrationStates.menu.set()  # Вернуться к основному меню

# Добавьте обработчики для других inline кнопок

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
