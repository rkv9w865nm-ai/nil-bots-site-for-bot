import asyncio
import datetime
import random
import os
import json
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

PRICE_BOT_ONLY = float(os.environ.get("PRICE_BOT_ONLY", "3000"))
PRICE_SERVER_BASIC = float(os.environ.get("PRICE_SERVER_BASIC", "99"))
PRICE_SERVER_PRO = float(os.environ.get("PRICE_SERVER_PRO", "250"))

SITE_URL = "https://nil-bots-site-with-bot.vercel.app/"
SUPPORT_URL = "https://t.me/nilbots_support_bot"

# ============================================
# ИНИЦИАЛИЗАЦИЯ FIREBASE
# ============================================
firebase_key_json = os.environ.get("FIREBASE_KEY_JSON")
if firebase_key_json:
    cred = credentials.Certificate(json.loads(firebase_key_json))
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cred = credentials.Certificate(os.path.join(current_dir, "firebase-key.json"))

firebase_admin.initialize_app(cred)
firebase_db = firestore.client()

if not BOT_TOKEN:
    raise SystemExit("❌ ОШИБКА: Переменная BOT_TOKEN не задана!")

# ============================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ============================================
# СОСТОЯНИЯ (FSM)
# ============================================
class OrderState(StatesGroup):
    choosing_package = State()
    choosing_server_tier = State()
    waiting_for_details = State()
    waiting_for_promo = State()
    confirming_order = State()

class SetBdayState(StatesGroup):
    waiting_for_bday = State()

class AdminReplyState(StatesGroup):
    waiting_for_reply = State()

class AddPromoState(StatesGroup):
    waiting_for_code = State()
    waiting_for_discount = State()
    waiting_for_uses = State()

# ============================================
# БАЗА ДАННЫХ (SQLite)
# ============================================
async def init_db():
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT, birthday TEXT, first_order INTEGER DEFAULT 1)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            order_number TEXT UNIQUE,
            user_id INTEGER, 
            service TEXT, 
            details TEXT, 
            price REAL, 
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY, discount INTEGER, uses_left INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT, is_user INTEGER)""")
        await db.commit()

async def generate_order_number():
    async with aiosqlite.connect("nil_bots.db") as db:
        while True:
            number = f"NB-{random.randint(1000, 9999)}"
            cursor = await db.execute("SELECT id FROM orders WHERE order_number=?", (number,))
            if not await cursor.fetchone():
                return number

# ============================================
# РАСЧЁТ ЦЕНЫ С ПРОМОКОДАМИ И СКИДКАМИ
# ============================================
async def calculate_price(base_price: float, user_id: int, promo_code: str = None):
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT birthday, first_order FROM users WHERE id=?", (user_id,))
        user = await cursor.fetchone()
    
    discount = 0
    reasons = []
    
    if user and user[1] == 1:
        discount += 10
        reasons.append("первый заказ")
    
    if user and user[0]:
        today = datetime.datetime.now().strftime("%d.%m")
        if user[0] == today:
            discount += 10
            reasons.append("день рождения")
    
    if promo_code:
        async with aiosqlite.connect("nil_bots.db") as db:
            cursor = await db.execute("SELECT discount, uses_left FROM promos WHERE code=?", (promo_code.upper(),))
            promo = await cursor.fetchone()
            if promo and promo[1] > 0:
                discount += promo[0]
                reasons.append(f"промокод {promo_code.upper()}")
                await db.execute("UPDATE promos SET uses_left = uses_left - 1 WHERE code=?", (promo_code.upper(),))
                await db.commit()

    discount = min(discount, 20)
    final_price = round(base_price * (1 - discount / 100), 2)
    reason_str = f"\n🎁 Скидка {discount}% ({', '.join(reasons)})" if discount > 0 else ""
    
    return final_price, reason_str

def get_status_emoji(status: str) -> str:
    statuses = {
        "new": "🟡 Создан",
        "working": "🔵 В работе",
        "done": "🟢 Готов",
        "cancelled": "🔴 Отменен",
        "closed": "⚫ Закрыт",
    }
    return statuses.get(status, "❓ Неизвестно")

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🛠 Заказать разработку", callback_data="order_start")],
        [InlineKeyboardButton(text="👤 Мой профиль и заказы", callback_data="profile")],
        [InlineKeyboardButton(text="🌐 Наш сайт", url=SITE_URL)],
        [InlineKeyboardButton(text="💬 Техподдержка", url=SUPPORT_URL)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton(text="💬 Чаты с клиентами", callback_data="admin_chats")],
        [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_kb(callback_data: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
    ])

# ============================================
# ЭКРАНЫ (с кнопками Назад)
# ============================================
async def show_package_screen(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Только бот", callback_data="pkg_bot_only")],
        [InlineKeyboardButton(text="🤖+ Бот + Сервер", callback_data="pkg_bot_server")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="start_back_to_main")]
    ])
    text = "🛠 <b>Что именно вы хотите заказать?</b>"
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.choosing_package)

async def show_tiers_screen(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Базовый (99₽/мес)", callback_data="srv_basic")],
        [InlineKeyboardButton(text="🚀 Продвинутый (250₽/мес)", callback_data="srv_pro")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_package")]
    ])
    text = (
        "🖥 <b>Выберите тариф хостинга для вашего бота:</b>\n\n"
        f"⚡ <b>Базовый:</b> {PRICE_SERVER_BASIC:.0f}₽/мес (для простых ботов)\n"
        f"🚀 <b>Продвинутый:</b> {PRICE_SERVER_PRO:.0f}₽/мес (для ботов с БД и нагрузкой)"
    )
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.choosing_server_tier)

async def show_details_prompt(message, state, edit=False):
    kb = back_kb("nav_back_from_details")
    text = "📝 Отлично! Опиши подробно, какого бота ты хочешь (функционал, идеи, примеры):"
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    await state.set_state(OrderState.waiting_for_details)

async def show_promo_question(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Есть промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_details")]
    ])
    text = "💬 <b>Есть ли у вас промокод?</b>"
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.waiting_for_promo)

# ============================================
# СТАРТ И ГЛАВНОЕ МЕНЮ
# ============================================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await init_db()
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", 
                         (message.from_user.id, message.from_user.username))
        await db.commit()
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 <b>Админ-панель:</b>", reply_markup=admin_menu(), parse_mode="HTML")
    else:
        await message.answer("👋 <b>Привет!</b>\nЯ помогу тебе заказать идеального Telegram-бота.", reply_markup=main_menu(), parse_mode="HTML")

# ============================================
# НАВИГАЦИЯ (кнопки Назад)
# ============================================
@router.callback_query(F.data == "nav_package")
async def nav_package(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_package_screen(call.message, state, edit=True)

@router.callback_query(F.data == "nav_tiers")
async def nav_tiers(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_tiers_screen(call.message, state, edit=True)

@router.callback_query(F.data == "nav_details")
async def nav_details(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_details_prompt(call.message, state, edit=True)

@router.callback_query(F.data == "nav_promo")
async def nav_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_promo_question(call.message, state, edit=True)

@router.callback_query(F.data == "nav_back_from_details")
async def nav_back_from_details(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    if data.get('package') == 'bot_server':
        await show_tiers_screen(call.message, state, edit=True)
    else:
        await show_package_screen(call.message, state, edit=True)

@router.callback_query(F.data == "start_back_to_main")
async def start_back_to_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    kb = admin_menu() if call.from_user.id == ADMIN_ID else main_menu()
    await call.message.edit_text("🏠 <b>Главное меню:</b>", reply_markup=kb, parse_mode="HTML")

# ============================================
# ПРОЦЕСС ЗАКАЗА
# ============================================
@router.callback_query(F.data == "order_start")
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await show_package_screen(call.message, state, edit=True)

@router.callback_query(F.data == "pkg_bot_only", OrderState.choosing_package)
async def pkg_bot_only(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(
        package="bot_only",
        package_label="🤖 Только бот",
        server_tier=None,
        server_tier_label=None,
        base_price=PRICE_BOT_ONLY,
        service_name="Разработка бота"
    )
    await show_details_prompt(call.message, state, edit=True)

@router.callback_query(F.data == "pkg_bot_server", OrderState.choosing_package)
async def pkg_bot_server(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(
        package="bot_server",
        package_label="🤖+🖥 Бот + Сервер",
        base_price=PRICE_BOT_ONLY,
        service_name="Разработка бота"
    )
    await show_tiers_screen(call.message, state, edit=True)

@router.callback_query(F.data.in_(["srv_basic", "srv_pro"]), OrderState.choosing_server_tier)
async def process_server_tier(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    base_price = data.get('base_price', PRICE_BOT_ONLY)
    
    if call.data == "srv_basic":
        server_price = PRICE_SERVER_BASIC
        server_name = "Хостинг (Базовый)"
        tier_key = "basic"
        tier_label = "⚡ Базовый (99₽/мес)"
    else:
        server_price = PRICE_SERVER_PRO
        server_name = "Хостинг (Продвинутый)"
        tier_key = "pro"
        tier_label = "🚀 Продвинутый (250₽/мес)"
    
    await state.update_data(
        package="bot_server",
        package_label="🤖+ Бот + Сервер",
        server_tier=tier_key,
        server_tier_label=tier_label,
        base_price=base_price + server_price,
        service_name=f"Разработка бота + {server_name}"
    )
    await show_details_prompt(call.message, state, edit=True)

@router.message(OrderState.waiting_for_details)
async def process_details(message: Message, state: FSMContext):
    await state.update_data(details=message.text)
    await show_promo_question(message, state, edit=False)

@router.callback_query(F.data == "enter_promo", OrderState.waiting_for_promo)
async def enter_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("✏️ Введите ваш промокод:", reply_markup=back_kb("nav_promo"))

@router.callback_query(F.data == "skip_promo", OrderState.waiting_for_promo)
async def skip_promo(call: CallbackQuery, state: FSMContext):
    await process_promo_logic(call.message, state, promo_code=None)

@router.message(OrderState.waiting_for_promo)
async def process_promo_msg(message: Message, state: FSMContext):
    await process_promo_logic(message, state, promo_code=message.text.strip())

async def process_promo_logic(target, state: FSMContext, promo_code: str = None):
    data = await state.get_data()
    final_price, reason_str = await calculate_price(data['base_price'], target.from_user.id, promo_code)
    await state.update_data(final_price=final_price, promo_reason=reason_str)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_promo")]
    ])
    
    await target.answer(
        f"📋 <b>Предварительный итог:</b>\n"
        f"📦 План: {data.get('package_label', '🤖 Только бот')}\n"
        f"{('🖥 Тариф: ' + data['server_tier_label'] + chr(10)) if data.get('server_tier_label') else ''}"
        f"🛠 Услуга: {data['service_name']}\n"
        f"📝 ТЗ: {data['details']}\n\n"
        f"💰 <b>Итоговая цена: {final_price}₽</b>{reason_str}",
        reply_markup=kb, 
        parse_mode="HTML"
    )
    await state.set_state(OrderState.confirming_order)

@router.callback_query(F.data == "confirm_order", OrderState.confirming_order)
async def confirm_and_create_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data['final_price']
    user_id = call.from_user.id
    
    order_number = await generate_order_number()
    service_name = data.get('service_name', 'Заказ')
    details = data.get('details', '')
    package_label = data.get('package_label', '🤖 Только бот')
    server_tier_label = data.get('server_tier_label')
    user_contact = f"@{call.from_user.username}" if call.from_user.username else f"ID: {user_id}"
    
    # 1. Сохраняем в SQLite
    async with aiosqlite.connect("nil_bots.db") as db_sqlite:
        await db_sqlite.execute("""
            INSERT INTO orders (order_number, user_id, service, details, price, status) 
            VALUES (?, ?, ?, ?, ?, 'new')
        """, (order_number, user_id, service_name, details, amount))
        await db_sqlite.execute("UPDATE users SET first_order=0 WHERE id=?", (user_id,))
        await db_sqlite.commit()
    
    # 2. Сохраняем в Firebase (с инфо о плане!)
    try:
        order_ref = firebase_db.collection("orders").document(order_number)
        order_ref.set({
            "number": order_number,
            "user_id": user_id,
            "client": user_contact,
            "contact": user_contact,
            "service": service_name,
            "package": data.get('package', 'bot_only'),
            "package_label": package_label,
            "server_tier": data.get('server_tier'),
            "server_tier_label": server_tier_label,
            "desc": details,
            "price": amount,
            "status": "new",
            "payment_status": "waiting_manual_payment",
            "date": datetime.datetime.now().isoformat(),
            "created_at": datetime.datetime.now().isoformat()
        })
        print(f"✅ Заказ {order_number} сохранён в Firebase")
    except Exception as e:
        print(f"❌ Ошибка Firebase: {e}")
    
    await state.clear()
    
    # Уведомление пользователю
    await call.message.answer(
        f"🎉 <b>Заказ #{order_number} успешно создан!</b>\n\n"
        f"Я передал ваше ТЗ разработчику. В ближайшее время с вами свяжутся для уточнения деталей и оплаты.\n\n"
        f"📊 <b>Отслеживать статус заказа:</b>\n{SITE_URL}\n(номер: <b>{order_number}</b>)",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    
    # Уведомление админу (С ПЛАНОМ!)
    plan_line = f"📦 План: {package_label}"
    if server_tier_label:
        plan_line += f"\n🖥 Тариф сервера: {server_tier_label}"
    
    await bot.send_message(
        ADMIN_ID,
        f"🔥 <b>НОВЫЙ ЗАКАЗ #{order_number}</b>\n\n"
        f"👤 Клиент: {user_contact} (ID: {user_id})\n"
        f"{plan_line}\n"
        f"🛠 Услуга: {service_name}\n"
        f"💬 ТЗ: {details}\n"
        f"💵 Сумма: {amount}₽\n\n"
        f"⚠️ Требуется связаться с клиентом!",
        parse_mode="HTML"
    )

# ============================================
# ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
# ============================================
@router.callback_query(F.data == "profile")
async def show_profile(call: CallbackQuery, state: FSMContext):
    await call.answer()
    user_id = call.from_user.id
    
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT username, birthday, first_order FROM users WHERE id=?", (user_id,))
        user = await cursor.fetchone()
        cursor_orders = await db.execute(
            "SELECT order_number, service, price, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC", 
            (user_id,)
        )
        orders = await cursor_orders.fetchall()
    
    username = user[0] if user and user[0] else "Не указан"
    bday = user[1] if user and user[1] else "Не указан"
    
    text = f"👤 <b>Ваш профиль:</b>\n"
    text += f"🆔 ID: <code>{user_id}</code>\n"
    text += f"📱 Username: @{username}\n"
    text += f"🎂 День рождения: {bday}\n\n"
    
    if orders:
        text += f"📦 <b>Ваши заказы ({len(orders)}):</b>\n"
        for o in orders:
            order_num, service, price, status, date = o
            status_emoji = get_status_emoji(status)
            short_date = date.split(' ')[0] if date else "Неизвестно"
            text += f"\n🔹 <b>#{order_num}</b> ({short_date})\n"
            text += f"   {service} | {price}₽\n"
            text += f"   Статус: {status_emoji}"
    else:
        text += "📭 У вас пока нет заказов."
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎂 Изменить ДР", callback_data="set_bday")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="start_back_to_main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "set_bday")
async def set_bday(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("🎂 Напиши дату рождения в формате ДД.ММ (например, 15.09):", reply_markup=back_kb("profile"))
    await state.set_state(SetBdayState.waiting_for_bday)

@router.message(SetBdayState.waiting_for_bday)
async def save_bday(message: Message, state: FSMContext):
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("UPDATE users SET birthday=? WHERE id=?", (message.text.strip(), message.from_user.id))
        await db.commit()
    await state.clear()
    await message.answer("✅ День рождения сохранён!", reply_markup=main_menu())

# ============================================
# АДМИН-ПАНЕЛЬ
# ============================================
@router.callback_query(F.data == "admin_chats")
async def admin_chats(call: CallbackQuery):
    await call.answer()
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT DISTINCT user_id FROM messages")
        users = await cursor.fetchall()
    if not users:
        return await call.message.edit_text("💬 Диалогов пока нет.", reply_markup=back_kb("start_back_to_main"))
    
    kb = [[InlineKeyboardButton(text=f"👤 {u[0]}", callback_data=f"chat_{u[0]}")] for u in users]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="start_back_to_main")])
    await call.message.edit_text("💬 <b>Выберите пользователя:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data.startswith("chat_"))
async def read_chat(call: CallbackQuery):
    await call.answer()
    user_id = int(call.data.split("_")[1])
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT text, is_user FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 15", (user_id,))
        msgs = await cursor.fetchall()
    
    history = "\n".join([f"{'👤 Клиент' if m[1] else '👑 Вы'}: {m[0]}" for m in reversed(msgs)])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Написать ответ", callback_data=f"reply_{user_id}")],
        [InlineKeyboardButton(text="🔙 К чатам", callback_data="admin_chats")]
    ])
    await call.message.edit_text(f"💬 <b>Чат с {user_id}:</b>\n\n{history}", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("reply_"))
async def start_admin_reply(call: CallbackQuery, state: FSMContext):
    await call.answer()
    user_id = int(call.data.split("_")[1])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminReplyState.waiting_for_reply)
    await call.message.edit_text(f"✏️ Введи ответ для пользователя {user_id}:\n(или /cancel)", reply_markup=back_kb("admin_chats"))

@router.message(AdminReplyState.waiting_for_reply)
async def admin_send_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    if not target_user_id:
        await state.clear()
        return
    try:
        await bot.send_message(target_user_id, f"👑 <b>Ответ от Nil Bots:</b>\n\n{message.text}", parse_mode="HTML")
        async with aiosqlite.connect("nil_bots.db") as db:
            await db.execute("INSERT INTO messages (user_id, text, is_user) VALUES (?, ?, 0)", (target_user_id, message.text))
            await db.commit()
        await message.answer(f"✅ Отправлено пользователю {target_user_id}.", reply_markup=admin_menu())
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    await state.clear()

@router.message(Command("cancel"))
async def cancel_state(message: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu() if message.from_user.id == ADMIN_ID else main_menu()
    await message.answer("❌ Действие отменено.", reply_markup=kb)

@router.callback_query(F.data == "admin_promos")
async def admin_promos(call: CallbackQuery):
    await call.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="create_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="start_back_to_main")]
    ])
    await call.message.edit_text("🎟 <b>Управление промокодами:</b>", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "create_promo")
async def create_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("✏️ Введи название промокода (например, NIL10):", reply_markup=back_kb("admin_promos"))
    await state.set_state(AddPromoState.waiting_for_code)

@router.message(AddPromoState.waiting_for_code)
async def promo_code_input(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await message.answer("💰 Введи размер скидки в % (например, 10):")
    await state.set_state(AddPromoState.waiting_for_discount)

@router.message(AddPromoState.waiting_for_discount)
async def promo_discount_input(message: Message, state: FSMContext):
    try:
        discount = int(message.text)
        await state.update_data(discount=discount)
        await message.answer("🔢 Введи количество активаций (например, 50):")
        await state.set_state(AddPromoState.waiting_for_uses)
    except ValueError:
        await message.answer("❌ Введи число.")

@router.message(AddPromoState.waiting_for_uses)
async def promo_uses_input(message: Message, state: FSMContext):
    try:
        uses = int(message.text)
        data = await state.get_data()
        async with aiosqlite.connect("nil_bots.db") as db:
            await db.execute("INSERT OR REPLACE INTO promos (code, discount, uses_left) VALUES (?, ?, ?)",
                           (data['code'], data['discount'], uses))
            await db.commit()
        await state.clear()
        await message.answer(f"✅ Промокод <b>{data['code']}</b> создан!\nСкидка: {data['discount']}%\nАктиваций: {uses}", reply_markup=admin_menu(), parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Введи число.")

# ============================================
# ПОДДЕРЖКА (пользовательские сообщения) — САМЫЙ ПОСЛЕДНИЙ ХЕНДЛЕР!
# ============================================
@router.message(F.text)
async def support_msg(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        return
    
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("INSERT INTO messages (user_id, text, is_user) VALUES (?, ?, 1)", 
                         (message.from_user.id, message.text))
        await db.commit()
    
    # Пересылаем админу
    try:
        await bot.send_message(ADMIN_ID, f"💬 <b>Сообщение от {message.from_user.full_name}</b> (ID: {message.from_user.id}):\n\n{message.text}", parse_mode="HTML")
    except Exception:
        pass
    
    await message.answer("✅ Отправлено! Администратор ответит вам в ближайшее время.")

# ============================================
# ЗАПУСК
# ============================================
async def main():
    await init_db()
    print("🚀 Бот nil.bots запущен!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"💰 Цены: Бот={PRICE_BOT_ONLY}₽, Basic={PRICE_SERVER_BASIC}₽, Pro={PRICE_SERVER_PRO}₽")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
