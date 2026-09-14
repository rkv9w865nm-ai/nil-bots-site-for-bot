import asyncio
import datetime
import random
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# НАСТРОЙКИ — ЗАМЕНИ НА СВОИ!
# ============================================
BOT_TOKEN = "8960247259:AAEEnulu0TY6XNrXwp0Fnuw2QhKmtrLM7l4"
ADMIN_ID = 5244755473

# ============================================
# ИНИЦИАЛИЗАЦИЯ FIREBASE
# ============================================
# ИНИЦИАЛИЗАЦИЯ FIREBASE
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
cred = credentials.Certificate(os.path.join(current_dir, "firebase-key.json"))
firebase_admin.initialize_app(cred)
firebase_db = firestore.client()  # ← ЭТА СТРОКА ОБЯЗАТЕЛЬНА!
# ============================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ============================================
# СОСТОЯНИЯ
# ============================================
class OrderState(StatesGroup):
    waiting_for_details = State()
    waiting_for_promo = State()

class AdminReplyState(StatesGroup):
    waiting_for_reply = State()

class SetBdayState(StatesGroup):
    waiting_for_bday = State()

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
    """Генерирует уникальный номер заказа вида NB-XXXX"""
    async with aiosqlite.connect("nil_bots.db") as db:
        while True:
            number = f"NB-{random.randint(1000, 9999)}"
            cursor = await db.execute("SELECT id FROM orders WHERE order_number=?", (number,))
            if not await cursor.fetchone():
                return number

# ============================================
# РАСЧЁТ ЦЕНЫ
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

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🛠 Заказать бота", callback_data="order_bot")],
        [InlineKeyboardButton(text="🖥 Тарифы серверов", callback_data="order_server")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text=" Поддержка", callback_data="support_info")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="💬 Чаты", callback_data="admin_chats")],
        [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ============================================
# ХЕНДЛЕРЫ ПОЛЬЗОВАТЕЛЯ
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
        await message.answer("👑 Админ-панель:", reply_markup=admin_menu())
    else:
        await message.answer("👋 Привет! Выбери услугу:", reply_markup=main_menu())

@router.callback_query(F.data == "order_bot")
async def order_bot(call: CallbackQuery, state: FSMContext):
    await state.update_data(base_price=90.0, service_name="Бот + админ панель + сайт")
    await call.message.answer("🛠 Опиши подробно, какой бот тебе нужен (ТЗ):")
    await state.set_state(OrderState.waiting_for_details)

@router.callback_query(F.data == "order_server")
async def order_server(call: CallbackQuery, state: FSMContext):
    await state.update_data(base_price=99.0, service_name="Базовый хост")
    await call.message.answer("📦 Какой тариф? Напиши 'базовый' (99₽/мес) или 'pro' (250₽/мес):")
    await state.set_state(OrderState.waiting_for_details)

@router.message(OrderState.waiting_for_details)
async def process_details(message: Message, state: FSMContext):
    data = await state.get_data()
    if data['service_name'] == "Базовый хост" and "pro" in message.text.lower():
        await state.update_data(base_price=250.0, service_name="Pro хост")
    
    await state.update_data(details=message.text)
    await message.answer("💬 Есть промокод? Напиши его или нажми 'Пропустить'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_promo")]]))
    await state.set_state(OrderState.waiting_for_promo)

@router.callback_query(F.data == "skip_promo", OrderState.waiting_for_promo)
async def skip_promo(call: CallbackQuery, state: FSMContext):
    await process_promo(call.message, state, promo_code=None)

@router.message(OrderState.waiting_for_promo)
async def process_promo_msg(message: Message, state: FSMContext):
    await process_promo(message, state, promo_code=message.text.strip())

async def process_promo(target, state: FSMContext, promo_code: str = None):
    data = await state.get_data()
    final_price, reason_str = await calculate_price(data['base_price'], target.from_user.id, promo_code)
    await state.update_data(final_price=final_price)
    
    kb = [
        [InlineKeyboardButton(text="💳 Оформить заказ", callback_data="create_order")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
    ]
    
    await target.answer(f"📋 *Заказ:*\n{data['details']}\n\n💰 *Итог:* {final_price}₽{reason_str}",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data == "create_order", OrderState.waiting_for_promo)
async def create_manual_order(call: CallbackQuery, state: FSMContext):
    """Создаёт заказ БЕЗ автоматической оплаты - для ручной обработки"""
    data = await state.get_data()
    amount = data['final_price']
    user_id = call.from_user.id
    
    order_number = await generate_order_number()
    service_name = data.get('service_name', 'Заказ')
    details = data.get('details', '')
    user_contact = f"@{call.from_user.username}" if call.from_user.username else f"ID: {user_id}"
    
    # 1. Сохраняем в SQLite
    async with aiosqlite.connect("nil_bots.db") as db_sqlite:
        await db_sqlite.execute("""
            INSERT INTO orders (order_number, user_id, service, details, price, status) 
            VALUES (?, ?, ?, ?, ?, 'new')
        """, (order_number, user_id, service_name, details, amount))
        await db_sqlite.commit()
    
    # 2. Сохраняем в Firebase Firestore (ИСПРАВЛЕНО!)
    try:
        order_ref = firebase_db.collection("orders").document(order_number)
        order_ref.set({
            "number": order_number,
            "user_id": user_id,
            "client": user_contact,
            "contact": user_contact,
            "service": service_name,
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
    
    # Уведомление пользователю (ИСПРАВЛЕНО - используем HTML вместо Markdown)
    await call.message.answer(
        f"✅ <b>Заказ #{order_number} создан!</b>\n\n"
        f"📋 Детали:\n"
        f"{details}\n\n"
        f" Сумма: <b>{amount}₽</b>\n\n"
        f"💳 <b>Оплата:</b>\n"
        f"Напиши в поддержку для получения реквизитов.\n\n"
        f"📊 <b>Отслеживай заказ на сайте:</b>\n"
        f"https://nil-bots-site.vercel.app\n"
        f"Введи номер: <b>{order_number}</b>",
        parse_mode="HTML"
    )
    
    # Уведомление админу (ИСПРАВЛЕНО - используем HTML)
    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>НОВЫЙ ЗАКАЗ #{order_number}</b>\n\n"
        f"👤 Клиент: {user_contact}\n"
        f"📦 Услуга: {service_name}\n"
        f"💬 Описание: {details}\n"
        f"💵 Сумма: {amount}₽\n\n"
        f"⚠️ Требуется ручная оплата!",
        parse_mode="HTML"
    )
@router.callback_query(F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("❌ Отменено.", reply_markup=main_menu())

@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT birthday, first_order FROM users WHERE id=?", (call.from_user.id,))
        user = await cursor.fetchone()
    
    if user:
        bday, first_order_flag = user
    else:
        bday, first_order_flag = None, 1
    
    bday_text = bday if bday else "Не указан"
    first_text = "Да" if first_order_flag else "Нет"
    
    kb = [[InlineKeyboardButton(text=" Указать ДР (ДД.ММ)", callback_data="set_bday")]]
    await call.message.answer(f"👤 *Профиль:*\n Первый заказ: {first_text}\n ДР: {bday_text}",
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data == "set_bday")
async def set_bday(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Напиши дату рождения (например, 15.09):")
    await state.set_state(SetBdayState.waiting_for_bday)

@router.message(SetBdayState.waiting_for_bday)
async def save_bday(message: Message, state: FSMContext):
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("UPDATE users SET birthday=? WHERE id=?", (message.text.strip(), message.from_user.id))
        await db.commit()
    await state.clear()
    await message.answer("✅ ДР сохранён!", reply_markup=main_menu())

@router.callback_query(F.data == "support_info")
async def support_info(call: CallbackQuery):
    await call.message.answer(" Напиши сюда сообщение, оно улетит админу.")

@router.message(F.text)
async def support_msg(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID and await state.get_state() == AdminReplyState.waiting_for_reply:
        return await admin_send_reply(message, state)
    if message.from_user.id == ADMIN_ID:
        return
    
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("INSERT INTO messages (user_id, text, is_user) VALUES (?, ?, 1)", 
                         (message.from_user.id, message.text))
        await db.commit()
    await message.answer("✅ Отправлено админу!")

# ============================================
# АДМИН ПАНЕЛЬ
# ============================================
@router.callback_query(F.data == "admin_chats")
async def admin_chats(call: CallbackQuery):
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT DISTINCT user_id FROM messages")
        users = await cursor.fetchall()
    if not users:
        return await call.message.answer("💬 Диалогов нет.")
    kb = [[InlineKeyboardButton(text=f"👤 {u[0]}", callback_data=f"chat_{u[0]}")] for u in users]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="start_back")])
    await call.message.answer("💬 Выбери пользователя:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("chat_"))
async def read_chat(call: CallbackQuery):
    user_id = int(call.data.split("_")[1])
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT text, is_user FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 15", (user_id,))
        msgs = await cursor.fetchall()
    history = "\n".join([f"{'👤' if m[1] else '👑'}: {m[0]}" for m in reversed(msgs)])
    kb = [[InlineKeyboardButton(text="✏️ Написать", callback_data=f"reply_{user_id}")],
          [InlineKeyboardButton(text="🔙 К чатам", callback_data="admin_chats")]]
    await call.message.answer(f"💬 Чат с {user_id}:\n\n{history}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("reply_"))
async def start_admin_reply(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split("_")[1])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminReplyState.waiting_for_reply)
    await call.message.answer(f"✏️ Введи ответ для {user_id} (или /cancel):")

@router.message(Command("cancel"))
async def cancel_state(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(" Отмена.", reply_markup=admin_menu() if message.from_user.id == ADMIN_ID else main_menu())

async def admin_send_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data['target_user_id']
    try:
        await bot.send_message(target_user_id, f"👑 *Ответ админа:*\n\n{message.text}", parse_mode="Markdown")
        async with aiosqlite.connect("nil_bots.db") as db:
            await db.execute("INSERT INTO messages (user_id, text, is_user) VALUES (?, ?, 0)", (target_user_id, message.text))
            await db.commit()
        await message.answer(f"✅ Отправлено {target_user_id}.", reply_markup=admin_menu())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

@router.callback_query(F.data == "admin_orders")
async def admin_orders(call: CallbackQuery):
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT order_number, user_id, service, price, status FROM orders ORDER BY id DESC LIMIT 10")
        orders = await cursor.fetchall()
    if not orders:
        return await call.message.answer(" Закаов нет.")
    text = "\n".join([f"#{o[0]} | ID {o[1]} | {o[2]} | {o[3]}₽ | {o[4]}" for o in orders])
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="start_back")]]
    await call.message.answer(f"📦 *Последние заказы:*\n\n{text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data == "admin_promos")
async def admin_promos(call: CallbackQuery):
    kb = [[InlineKeyboardButton(text="➕ Создать промокод", callback_data="create_promo")],
          [InlineKeyboardButton(text="🔙 Назад", callback_data="start_back")]]
    await call.message.answer(" Управление промокодами:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "create_promo")
async def create_promo(call: CallbackQuery, state: FSMContext):
    await call.message.answer(" Введи название промокода (например, NIL10):")
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
        await message.answer("🔢 Введи количество использований (например, 50):")
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
        await message.answer(f"✅ Промокод {data['code']} создан! Скидка {data['discount']}%, Использований: {uses}", reply_markup=admin_menu())
    except ValueError:
        await message.answer("❌ Введи число.")

@router.callback_query(F.data == "start_back")
async def start_back(call: CallbackQuery):
    await call.message.answer(" Админ-панель:", reply_markup=admin_menu())

# ============================================
# ЗАПУСК
# ============================================
async def main():
    await init_db()
    print(" Бот nil.bots запущен!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("📦 Заказы синхронизируются с Firebase")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())