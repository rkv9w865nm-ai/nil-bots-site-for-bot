import asyncio
import datetime
import json
import os
import random

import aiosqlite
import firebase_admin
from firebase_admin import credentials, firestore

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5244755473"))

if not BOT_TOKEN:
    raise RuntimeError(
        "Переменная BOT_TOKEN не установлена. "
        "Добавь BOT_TOKEN в Railway Variables."
    )


# ============================================================
# FIREBASE
# ============================================================

firebase_key_raw = os.getenv("FIREBASE_KEY")

if not firebase_key_raw:
    raise RuntimeError(
        "Переменная FIREBASE_KEY не установлена. "
        "Добавь содержимое firebase-key.json в Railway Variables."
    )

try:
    firebase_key = json.loads(firebase_key_raw)
except json.JSONDecodeError as e:
    raise RuntimeError(
        "FIREBASE_KEY содержит неправильный JSON. "
        "Проверь, что в Railway вставлено полное содержимое firebase-key.json."
    ) from e


if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key)
    firebase_admin.initialize_app(cred)

firebase_db = firestore.client()


# ============================================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

router = Router()

dp.include_router(router)


# ============================================================
# СОСТОЯНИЯ
# ============================================================

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


# ============================================================
# БАЗА ДАННЫХ SQLITE
# ============================================================

async def init_db():
    async with aiosqlite.connect("nil_bots.db") as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                birthday TEXT,
                first_order INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE,
                user_id INTEGER,
                service TEXT,
                details TEXT,
                price REAL,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promos (
                code TEXT PRIMARY KEY,
                discount INTEGER,
                uses_left INTEGER
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                is_user INTEGER
            )
        """)

        await db.commit()


# ============================================================
# НОМЕР ЗАКАЗА
# ============================================================

async def generate_order_number():
    """
    Генерирует уникальный номер заказа вида NB-XXXX.
    """

    async with aiosqlite.connect("nil_bots.db") as db:

        while True:

            number = f"NB-{random.randint(1000, 9999)}"

            cursor = await db.execute(
                "SELECT id FROM orders WHERE order_number=?",
                (number,)
            )

            if not await cursor.fetchone():
                return number


# ============================================================
# РАСЧЁТ ЦЕНЫ
# ============================================================

async def calculate_price(
    base_price: float,
    user_id: int,
    promo_code: str = None
):
    async with aiosqlite.connect("nil_bots.db") as db:

        cursor = await db.execute(
            "SELECT birthday, first_order FROM users WHERE id=?",
            (user_id,)
        )

        user = await cursor.fetchone()

    discount = 0
    reasons = []

    # Первый заказ
    if user and user[1] == 1:

        discount += 10

        reasons.append("первый заказ")

    # День рождения
    if user and user[0]:

        today = datetime.datetime.now().strftime("%d.%m")

        if user[0] == today:

            discount += 10

            reasons.append("день рождения")

    # Промокод
    if promo_code:

        promo_code = promo_code.strip().upper()

        async with aiosqlite.connect("nil_bots.db") as db:

            cursor = await db.execute(
                "SELECT discount, uses_left FROM promos WHERE code=?",
                (promo_code,)
            )

            promo = await cursor.fetchone()

            if promo and promo[1] > 0:

                discount += promo[0]

                reasons.append(f"промокод {promo_code}")

                await db.execute(
                    """
                    UPDATE promos
                    SET uses_left = uses_left - 1
                    WHERE code=?
                    """,
                    (promo_code,)
                )

                await db.commit()

    # Максимальная скидка — 20%
    discount = min(discount, 20)

    final_price = round(
        base_price * (1 - discount / 100),
        2
    )

    if discount > 0:
        reason_str = (
            f"\n🎁 Скидка {discount}% "
            f"({', '.join(reasons)})"
        )
    else:
        reason_str = ""

    return final_price, reason_str


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_menu():

    kb = [
        [
            InlineKeyboardButton(
                text="🛠 Заказать бота",
                callback_data="order_bot"
            )
        ],
        [
            InlineKeyboardButton(
                text="🖥 Тарифы серверов",
                callback_data="order_server"
            )
        ],
        [
            InlineKeyboardButton(
                text="👤 Профиль",
                callback_data="profile"
            )
        ],
        [
            InlineKeyboardButton(
                text="🆘 Поддержка",
                callback_data="support_info"
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_menu():

    kb = [
        [
            InlineKeyboardButton(
                text="📦 Заказы",
                callback_data="admin_orders"
            )
        ],
        [
            InlineKeyboardButton(
                text="💬 Чаты",
                callback_data="admin_chats"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎟 Промокоды",
                callback_data="admin_promos"
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=kb)


# ============================================================
# START
# ============================================================

@router.message(Command("start"))
async def cmd_start(
    message: Message,
    state: FSMContext
):

    await state.clear()

    await init_db()

    async with aiosqlite.connect("nil_bots.db") as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO users
            (id, username)
            VALUES (?, ?)
            """,
            (
                message.from_user.id,
                message.from_user.username
            )
        )

        await db.commit()

    if message.from_user.id == ADMIN_ID:

        await message.answer(
            "👑 Админ-панель:",
            reply_markup=admin_menu()
        )

    else:

        await message.answer(
            "👋 Привет! Выбери услугу:",
            reply_markup=main_menu()
        )


# ============================================================
# ЗАКАЗ БОТА
# ============================================================

@router.callback_query(F.data == "order_bot")
async def order_bot(
    call: CallbackQuery,
    state: FSMContext
):

    await state.update_data(
        base_price=90.0,
        service_name="Бот + админ панель + сайт"
    )

    await call.message.answer(
        "🛠 Опиши подробно, какой бот тебе нужен (ТЗ):"
    )

    await state.set_state(
        OrderState.waiting_for_details
    )

    await call.answer()


# ============================================================
# ЗАКАЗ СЕРВЕРА
# ============================================================

@router.callback_query(F.data == "order_server")
async def order_server(
    call: CallbackQuery,
    state: FSMContext
):

    await state.update_data(
        base_price=99.0,
        service_name="Базовый хост"
    )

    await call.message.answer(
        "📦 Какой тариф?\n\n"
        "Напиши «базовый» — 99₽/мес\n"
        "или «pro» — 250₽/мес."
    )

    await state.set_state(
        OrderState.waiting_for_details
    )

    await call.answer()


# ============================================================
# ДЕТАЛИ ЗАКАЗА
# ============================================================

@router.message(OrderState.waiting_for_details)
async def process_details(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    service_name = data.get("service_name")

    if (
        service_name == "Базовый хост"
        and message.text
        and "pro" in message.text.lower()
    ):

        await state.update_data(
            base_price=250.0,
            service_name="Pro хост"
        )

    await state.update_data(
        details=message.text
    )

    await message.answer(
        "💬 Есть промокод?\n"
        "Напиши его или нажми «Пропустить».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Пропустить",
                        callback_data="skip_promo"
                    )
                ]
            ]
        )
    )

    await state.set_state(
        OrderState.waiting_for_promo
    )


# ============================================================
# ПРОПУСК ПРОМОКОДА
# ============================================================

@router.callback_query(
    F.data == "skip_promo",
    OrderState.waiting_for_promo
)
async def skip_promo(
    call: CallbackQuery,
    state: FSMContext
):

    await process_promo(
        call.message,
        state,
        promo_code=None
    )

    await call.answer()


# ============================================================
# ПРОМОКОД
# ============================================================

@router.message(OrderState.waiting_for_promo)
async def process_promo_msg(
    message: Message,
    state: FSMContext
):

    await process_promo(
        message,
        state,
        promo_code=message.text.strip()
    )


async def process_promo(
    target,
    state: FSMContext,
    promo_code: str = None
):

    data = await state.get_data()

    final_price, reason_str = await calculate_price(
        data["base_price"],
        target.from_user.id,
        promo_code
    )

    await state.update_data(
        final_price=final_price
    )

    kb = [
        [
            InlineKeyboardButton(
                text="💳 Оформить заказ",
                callback_data="create_order"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_order"
            )
        ]
    ]

    await target.answer(
        f"📋 <b>Заказ:</b>\n"
        f"{data['details']}\n\n"
        f"💰 <b>Итог:</b> "
        f"{final_price}₽"
        f"{reason_str}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        ),
        parse_mode="HTML"
    )


# ============================================================
# СОЗДАНИЕ ЗАКАЗА
# ============================================================

@router.callback_query(
    F.data == "create_order",
    OrderState.waiting_for_promo
)
async def create_manual_order(
    call: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    amount = data["final_price"]

    user_id = call.from_user.id

    order_number = await generate_order_number()

    service_name = data.get(
        "service_name",
        "Заказ"
    )

    details = data.get(
        "details",
        ""
    )

    if call.from_user.username:

        user_contact = (
            f"@{call.from_user.username}"
        )

    else:

        user_contact = (
            f"ID: {user_id}"
        )

    # --------------------------------------------------------
    # SQLite
    # --------------------------------------------------------

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db_sqlite:

        await db_sqlite.execute(
            """
            INSERT INTO orders
            (
                order_number,
                user_id,
                service,
                details,
                price,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'new')
            """,
            (
                order_number,
                user_id,
                service_name,
                details,
                amount
            )
        )

        # После первого заказа убираем скидку первого заказа
        await db_sqlite.execute(
            """
            UPDATE users
            SET first_order = 0
            WHERE id=?
            """,
            (user_id,)
        )

        await db_sqlite.commit()

    # --------------------------------------------------------
    # Firebase Firestore
    # --------------------------------------------------------

    try:

        order_ref = (
            firebase_db
            .collection("orders")
            .document(order_number)
        )

        now = datetime.datetime.now().isoformat()

        order_ref.set(
            {
                "number": order_number,
                "user_id": user_id,
                "client": user_contact,
                "contact": user_contact,
                "service": service_name,
                "desc": details,
                "price": amount,
                "status": "new",
                "payment_status": "waiting_manual_payment",
                "date": now,
                "created_at": now
            }
        )

        print(
            f"✅ Заказ {order_number} "
            f"сохранён в Firebase"
        )

    except Exception as e:

        print(
            f"❌ Ошибка Firebase: {e}"
        )

    await state.clear()

    # --------------------------------------------------------
    # Пользователь
    # --------------------------------------------------------

    await call.message.answer(
        f"✅ <b>Заказ #{order_number} создан!</b>\n\n"
        f"📋 <b>Детали:</b>\n"
        f"{details}\n\n"
        f"💰 Сумма: <b>{amount}₽</b>\n\n"
        f"💳 <b>Оплата:</b>\n"
        f"Напиши в поддержку для получения реквизитов.\n\n"
        f"📊 <b>Отслеживай заказ на сайте:</b>\n"
        f"https://nil-bots-site.vercel.app\n\n"
        f"Введи номер: <b>{order_number}</b>",
        parse_mode="HTML"
    )

    # --------------------------------------------------------
    # Администратор
    # --------------------------------------------------------

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

    await call.answer()


# ============================================================
# ОТМЕНА ЗАКАЗА
# ============================================================

@router.callback_query(F.data == "cancel_order")
async def cancel_order(
    call: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await call.message.answer(
        "❌ Заказ отменён.",
        reply_markup=main_menu()
    )

    await call.answer()


# ============================================================
# ПРОФИЛЬ
# ============================================================

@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db:

        cursor = await db.execute(
            """
            SELECT birthday, first_order
            FROM users
            WHERE id=?
            """,
            (call.from_user.id,)
        )

        user = await cursor.fetchone()

    if user:

        bday = user[0]
        first_order_flag = user[1]

    else:

        bday = None
        first_order_flag = 1

    bday_text = (
        bday if bday else "Не указан"
    )

    first_text = (
        "Да" if first_order_flag else "Нет"
    )

    kb = [
        [
            InlineKeyboardButton(
                text="🎂 Указать ДР (ДД.ММ)",
                callback_data="set_bday"
            )
        ]
    ]

    await call.message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"🎁 Первый заказ: {first_text}\n"
        f"🎂 ДР: {bday_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        ),
        parse_mode="HTML"
    )

    await call.answer()


# ============================================================
# УСТАНОВКА ДНЯ РОЖДЕНИЯ
# ============================================================

@router.callback_query(F.data == "set_bday")
async def set_bday(
    call: CallbackQuery,
    state: FSMContext
):

    await call.message.answer(
        "🎂 Напиши дату рождения "
        "(например, 15.09):"
    )

    await state.set_state(
        SetBdayState.waiting_for_bday
    )

    await call.answer()


@router.message(SetBdayState.waiting_for_bday)
async def save_bday(
    message: Message,
    state: FSMContext
):

    birthday = message.text.strip()

    try:

        datetime.datetime.strptime(
            birthday,
            "%d.%m"
        )

    except ValueError:

        await message.answer(
            "❌ Неверный формат.\n"
            "Используй ДД.ММ, например: 15.09"
        )

        return

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db:

        await db.execute(
            """
            UPDATE users
            SET birthday=?
            WHERE id=?
            """,
            (
                birthday,
                message.from_user.id
            )
        )

        await db.commit()

    await state.clear()

    await message.answer(
        "✅ День рождения сохранён!",
        reply_markup=main_menu()
    )


# ============================================================
# ПОДДЕРЖКА
# ============================================================

@router.callback_query(F.data == "support_info")
async def support_info(call: CallbackQuery):

    await call.message.answer(
        "🆘 Напиши сообщение сюда — "
        "оно будет отправлено администратору."
    )

    await call.answer()


@router.message(F.text)
async def support_msg(
    message: Message,
    state: FSMContext
):

    current_state = await state.get_state()

    if (
        message.from_user.id == ADMIN_ID
        and current_state
        == AdminReplyState.waiting_for_reply
    ):

        return await admin_send_reply(
            message,
            state
        )

    if message.from_user.id == ADMIN_ID:
        return

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db:

        await db.execute(
            """
            INSERT INTO messages
            (user_id, text, is_user)
            VALUES (?, ?, 1)
            """,
            (
                message.from_user.id,
                message.text
            )
        )

        await db.commit()

    # Уведомляем администратора
    try:

        username = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else f"ID: {message.from_user.id}"
        )

        await bot.send_message(
            ADMIN_ID,
            f"💬 <b>Новое сообщение</b>\n\n"
            f"👤 {username}\n"
            f"🆔 {message.from_user.id}\n\n"
            f"{message.text}",
            parse_mode="HTML"
        )

    except Exception as e:

        print(
            f"Ошибка уведомления админа: {e}"
        )

    await message.answer(
        "✅ Сообщение отправлено админу!"
    )


# ============================================================
# АДМИН — ЧАТЫ
# ============================================================

@router.callback_query(F.data == "admin_chats")
async def admin_chats(call: CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db:

        cursor = await db.execute(
            """
            SELECT DISTINCT user_id
            FROM messages
            """
        )

        users = await cursor.fetchall()

    if not users:

        await call.message.answer(
            "💬 Диалогов пока нет."
        )

        await call.answer()

        return

    kb = [
        [
            InlineKeyboardButton(
                text=f"👤 {user[0]}",
                callback_data=f"chat_{user[0]}"
            )
        ]
        for user in users
    ]

    kb.append(
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="start_back"
            )
        ]
    )

    await call.message.answer(
        "💬 Выбери пользователя:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        )
    )

    await call.answer()


# ============================================================
# ПРОСМОТР ЧАТА
# ============================================================

@router.callback_query(F.data.startswith("chat_"))
async def read_chat(call: CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return

    try:

        user_id = int(
            call.data.split("_")[1]
        )

    except (ValueError, IndexError):

        await call.answer(
            "Ошибка пользователя",
            show_alert=True
        )

        return

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db:

        cursor = await db.execute(
            """
            SELECT text, is_user
            FROM messages
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 15
            """,
            (user_id,)
        )

        msgs = await cursor.fetchall()

    if msgs:

        history = "\n\n".join(
            [
                (
                    f"{'👤 Пользователь' if m[1] else '👑 Админ'}:\n"
                    f"{m[0]}"
                )
                for m in reversed(msgs)
            ]
        )

    else:

        history = "Сообщений нет."

    kb = [
        [
            InlineKeyboardButton(
                text="✏️ Написать",
                callback_data=f"reply_{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 К чатам",
                callback_data="admin_chats"
            )
        ]
    ]

    await call.message.answer(
        f"💬 <b>Чат с {user_id}</b>\n\n"
        f"{history}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        ),
        parse_mode="HTML"
    )

    await call.answer()


# ============================================================
# ОТВЕТ АДМИНА
# ============================================================

@router.callback_query(F.data.startswith("reply_"))
async def start_admin_reply(
    call: CallbackQuery,
    state: FSMContext
):

    if call.from_user.id != ADMIN_ID:
        return

    try:

        user_id = int(
            call.data.split("_")[1]
        )

    except (ValueError, IndexError):

        await call.answer(
            "Ошибка пользователя",
            show_alert=True
        )

        return

    await state.update_data(
        target_user_id=user_id
    )

    await state.set_state(
        AdminReplyState.waiting_for_reply
    )

    await call.message.answer(
        f"✏️ Введи ответ для {user_id}.\n"
        f"Для отмены используй /cancel."
    )

    await call.answer()


# ============================================================
# CANCEL
# ============================================================

@router.message(Command("cancel"))
async def cancel_state(
    message: Message,
    state: FSMContext
):

    await state.clear()

    if message.from_user.id == ADMIN_ID:

        await message.answer(
            "❌ Отмена.",
            reply_markup=admin_menu()
        )

    else:

        await message.answer(
            "❌ Отмена.",
            reply_markup=main_menu()
        )


# ============================================================
# ОТПРАВКА ОТВЕТА АДМИНА
# ============================================================

async def admin_send_reply(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    target_user_id = data.get(
        "target_user_id"
    )

    if not target_user_id:

        await state.clear()

        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=admin_menu()
        )

        return

    try:

        await bot.send_message(
            target_user_id,
            f"👑 <b>Ответ администратора:</b>\n\n"
            f"{message.text}",
            parse_mode="HTML"
        )

        async with aiosqlite.connect(
            "nil_bots.db"
        ) as db:

            await db.execute(
                """
                INSERT INTO messages
                (user_id, text, is_user)
                VALUES (?, ?, 0)
                """,
                (
                    target_user_id,
                    message.text
                )
            )

            await db.commit()

        await message.answer(
            f"✅ Ответ отправлен {target_user_id}.",
            reply_markup=admin_menu()
        )

    except Exception as e:

        await message.answer(
            f"❌ Ошибка отправки:\n{e}"
        )

    await state.clear()


# ============================================================
# АДМИН — ЗАКАЗЫ
# ============================================================

@router.callback_query(F.data == "admin_orders")
async def admin_orders(call: CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db:

        cursor = await db.execute(
            """
            SELECT
                order_number,
                user_id,
                service,
                price,
                status
            FROM orders
            ORDER BY id DESC
            LIMIT 10
            """
        )

        orders = await cursor.fetchall()

    if not orders:

        await call.message.answer(
            "📦 Заказов пока нет."
        )

        await call.answer()

        return

    text = "\n\n".join(
        [
            (
                f"#{o[0]}\n"
                f"👤 ID: {o[1]}\n"
                f"📦 {o[2]}\n"
                f"💰 {o[3]}₽\n"
                f"📊 {o[4]}"
            )
            for o in orders
        ]
    )

    kb = [
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="start_back"
            )
        ]
    ]

    await call.message.answer(
        f"📦 <b>Последние заказы:</b>\n\n{text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        ),
        parse_mode="HTML"
    )

    await call.answer()


# ============================================================
# АДМИН — ПРОМОКОДЫ
# ============================================================

@router.callback_query(F.data == "admin_promos")
async def admin_promos(call: CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return

    kb = [
        [
            InlineKeyboardButton(
                text="➕ Создать промокод",
                callback_data="create_promo"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="start_back"
            )
        ]
    ]

    await call.message.answer(
        "🎟 Управление промокодами:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=kb
        )
    )

    await call.answer()


# ============================================================
# СОЗДАНИЕ ПРОМОКОДА
# ============================================================

@router.callback_query(F.data == "create_promo")
async def create_promo(
    call: CallbackQuery,
    state: FSMContext
):

    if call.from_user.id != ADMIN_ID:
        return

    await call.message.answer(
        "🎟 Введи название промокода "
        "(например, NIL10):"
    )

    await state.set_state(
        AddPromoState.waiting_for_code
    )

    await call.answer()


@router.message(AddPromoState.waiting_for_code)
async def promo_code_input(
    message: Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:
        return

    code = message.text.strip().upper()

    if not code:

        await message.answer(
            "❌ Промокод не может быть пустым."
        )

        return

    await state.update_data(
        code=code
    )

    await message.answer(
        "💰 Введи размер скидки в % "
        "(например, 10):"
    )

    await state.set_state(
        AddPromoState.waiting_for_discount
    )


@router.message(AddPromoState.waiting_for_discount)
async def promo_discount_input(
    message: Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        discount = int(
            message.text.strip()
        )

        if discount < 0 or discount > 100:

            raise ValueError

    except ValueError:

        await message.answer(
            "❌ Введи число от 0 до 100."
        )

        return

    await state.update_data(
        discount=discount
    )

    await message.answer(
        "🔢 Введи количество использований "
        "(например, 50):"
    )

    await state.set_state(
        AddPromoState.waiting_for_uses
    )


@router.message(AddPromoState.waiting_for_uses)
async def promo_uses_input(
    message: Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        uses = int(
            message.text.strip()
        )

        if uses <= 0:

            raise ValueError

    except ValueError:

        await message.answer(
            "❌ Введи положительное число."
        )

        return

    data = await state.get_data()

    async with aiosqlite.connect(
        "nil_bots.db"
    ) as db:

        await db.execute(
            """
            INSERT OR REPLACE INTO promos
            (
                code,
                discount,
                uses_left
            )
            VALUES (?, ?, ?)
            """,
            (
                data["code"],
                data["discount"],
                uses
            )
        )

        await db.commit()

    await state.clear()

    await message.answer(
        f"✅ Промокод <b>{data['code']}</b> создан!\n\n"
        f"💰 Скидка: {data['discount']}%\n"
        f"🔢 Использований: {uses}",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


# ============================================================
# НАЗАД
# ============================================================

@router.callback_query(F.data == "start_back")
async def start_back(call: CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return

    await call.message.answer(
        "👑 Админ-панель:",
        reply_markup=admin_menu()
    )

    await call.answer()


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    await init_db()

    print("========================================")
    print("🚀 NIL.BOTS запущен!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("🔥 Firebase подключён")
    print("📦 SQLite подключён")
    print("========================================")

    try:

        await dp.start_polling(bot)

    finally:

        await bot.session.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
