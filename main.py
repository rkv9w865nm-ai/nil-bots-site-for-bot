import asyncio
import datetime
import random
import os
import json
import html
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ErrorEvent
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================
# НАСТРОЙКИ
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

PRICE_BOT_ONLY = float(os.environ.get("PRICE_BOT_ONLY", "115"))
PRICE_SERVER_BASIC = float(os.environ.get("PRICE_SERVER_BASIC", "300"))

ADDONS = {
    "support_bot": {
        "label": "🛟 Отдельный бот тех. поддержки",
        "price": float(os.environ.get("PRICE_ADDON_SUPPORT", "99")),
    },
    "priority": {
        "label": "⚡ Приоритет к заказу",
        "price": float(os.environ.get("PRICE_ADDON_PRIORITY", "50")),
    },
}

SITE_URL = "https://nil-bots-site-with-bot.vercel.app/"
SUPPORT_URL = "https://t.me/nilbots_support_bot"

# ============================================
# ПОЛНЫЕ ТЕКСТЫ ДОКУМЕНТОВ
# ============================================
PRIVACY_POLICY = """\
🔒 <b>ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ</b>

<b>1. Общие положения</b>
1.1. Настоящая Политика конфиденциальности определяет порядок сбора, обработки, хранения и защиты персональных данных Пользователей онлайн-сервиса (далее — «Сервис»).
1.2. Обработка персональных данных Пользователей осуществляется в соответствии с настоящей Политикой и применимым законодательством.
1.3. Используя Сервис, Пользователь подтверждает, что ознакомился с настоящей Политикой.

<b>2. Обрабатываемые данные</b>
2.1. В зависимости от используемого функционала Оператор может обрабатывать:
• имя и контактные данные;
• идентификаторы учётной записи;
• адрес электронной почты и номер телефона, если они предоставлены;
• сведения о заказах и подписках;
• сведения о платежах и их статусе;
• технические данные устройства и подключения;
• информацию, предоставленную Пользователем при обращении в поддержку.
2.2. Оператор не запрашивает пароли, платёжные коды и иные конфиденциальные данные, если их предоставление не требуется соответствующим официальным сервисом.

<b>3. Цели обработки</b>
3.1. Персональные данные обрабатываются для:
• предоставления товаров и услуг;
• регистрации и идентификации Пользователя;
• обработки платежей;
• управления заказами и подписками;
• предоставления технической поддержки;
• обеспечения безопасности Сервиса;
• предотвращения мошенничества и злоупотреблений;
• улучшения работы Сервиса;
• выполнения требований законодательства.

<b>4. Основания обработки</b>
4.1. Обработка персональных данных осуществляется на основании согласия Пользователя, необходимости исполнения договора, выполнения требований законодательства, а также иных законных оснований, предусмотренных применимым законодательством.

<b>5. Передача данных третьим лицам</b>
5.1. Оператор не продаёт персональные данные Пользователей третьим лицам.
5.2. Данные могут передаваться платёжным, техническим, информационным и иным поставщикам услуг в объёме, необходимом для функционирования Сервиса.
5.3. Передача данных государственным органам осуществляется исключительно в случаях и порядке, предусмотренных применимым законодательством.

<b>6. Платёжные данные</b>
6.1. Обработка банковских карт и иных платёжных реквизитов может осуществляться непосредственно сторонним платёжным провайдером.
6.2. Если иное не предусмотрено используемой платёжной инфраструктурой, Оператор не хранит полные реквизиты банковских карт Пользователей.

<b>7. Хранение и защита данных</b>
7.1. Персональные данные хранятся только в течение периода, необходимого для достижения целей обработки, либо в течение срока, установленного законодательством.
7.2. Оператор принимает разумные технические и организационные меры для защиты данных от утраты, изменения, раскрытия и несанкционированного доступа.
7.3. После достижения целей обработки данные могут быть удалены или обезличены, если их дальнейшее хранение не требуется законодательством.
<b>8. Права Пользователя</b>
8.1. В предусмотренных законом случаях Пользователь вправе запросить доступ к своим персональным данным, их изменение или удаление, а также воспользоваться иными предусмотренными законодательством правами.
8.2. Для реализации своих прав Пользователь может обратиться к Оператору по указанным в Сервисе контактным данным.
<b>9. Изменение Политики</b>
9.1. Оператор вправе изменять настоящую Политику в связи с изменением законодательства, функциональности Сервиса или порядка обработки данных.
9.2. Актуальная редакция Политики публикуется в Сервисе.

<b>10. Контактная информация</b>
10.1. По вопросам использования Сервиса Заказчик может обратиться в службу поддержки по указанным в Сервисе контактным данным."""


PUBLIC_OFFER = """\
📄 <b>ПУБЛИЧНАЯ ОФЕРТА</b>
<i>Пользовательское соглашение</i>

<b>1. Общие положения</b>
1.1. Настоящая оферта (далее — «Договор») регулирует отношения между Исполнителем и Заказчиком в связи с предоставлением Исполнителем цифровых товаров и/или услуг посредством онлайн-сервиса (далее — «Сервис»).
1.2. Использование Сервиса, регистрация, оформление заказа, оплата услуг или получение доступа к цифровым материалам означают полное и безоговорочное принятие Заказчиком условий настоящего Договора.
1.3. В случае несогласия с условиями Договора Заказчик обязан прекратить использование Сервиса.

<b>2. Предмет договора</b>
2.1. В соответствии с условиями настоящего Договора Исполнитель принимает на себя обязательство по предоставлению Заказчику цифровых товаров и/или услуг, а Заказчик обязуется принять указанные товары и услуги и произвести их оплату в порядке и на условиях, определённых настоящей офертой.
2.2. Доступ к услугам и цифровым товарам обеспечивается посредством программных, технических и информационных средств Сервиса.
2.3. Конкретный состав, стоимость, срок действия и условия предоставления соответствующего товара или услуги указываются в Сервисе до момента оплаты.

<b>3. Порядок предоставления услуг</b>
3.1. После успешной оплаты Заказчику предоставляется доступ к приобретённому товару или услуге в порядке, предусмотренном Сервисом.
3.2. Заказчик самостоятельно обеспечивает наличие необходимых технических средств и доступа к сети Интернет.
3.3. Срок предоставления доступа определяется условиями соответствующего тарифа или заказа.

<b>4. Оплата и возвраты</b>
4.1. Стоимость определяется тарифами на момент оформления заказа.
4.2. Оплата производится доступными в Сервисе платёжными инструментами.
4.3. Возврат осуществляется в соответствии с законодательством.
4.4. При технической проблеме Заказчик вправе обратиться в поддержку.

<b>5. Права и обязанности Заказчика</b>
5.1. Заказчик обязуется использовать Сервис исключительно законным способом и соблюдать условия настоящего Договора.
5.2. Запрещается использовать Сервис для мошенничества, нарушения законодательства, распространения вредоносного программного обеспечения, нарушения прав третьих лиц или иных противоправных действий.
5.3. Заказчик несёт ответственность за достоверность предоставляемой им информации и законность своих действий при использовании Сервиса.

<b>6. Интеллектуальная собственность</b>
6.1. Материалы, размещённые в Сервисе, охраняются законодательством об интеллектуальной собственности.
6.2. Приобретение товара или услуги не означает передачу Заказчику исключительных прав на соответствующие материалы.
6.3. Копирование, перепродажа, распространение, публикация и передача материалов третьим лицам запрещены, если иное прямо не предусмотрено условиями конкретного товара или законодательством.

<b>7. Права Исполнителя</b>
7.1. Исполнитель вправе временно ограничить работу Сервиса для проведения технических работ, обновлений или устранения неисправностей.
7.2. Исполнитель вправе ограничить или прекратить доступ Заказчика к Сервису при нарушении настоящего Договора или применимого законодательства.
7.3. Исполнитель вправе изменять функциональность Сервиса, условия тарифов и настоящий Договор с публикацией актуальной редакции в Сервисе.

<b>8. Ответственность</b>
8.1. Исполнитель не гарантирует бесперебойную работу Сервиса и достижение Заказчиком какого-либо конкретного результата, если такой результат прямо не предусмотрен условиями приобретённой услуги.
8.2. Исполнитель не несёт ответственности за сбои, вызванные действиями третьих лиц, операторов связи, платёжных систем, техническими неисправностями или иными обстоятельствами, находящимися вне разумного контроля Исполнителя.
8.3. Заказчик самостоятельно несёт ответственность за использование предоставленных товаров, материалов и услуг.

<b>9. Конфиденциальность</b>
9.1. Обработка персональных данных осуществляется в соответствии с отдельной Политикой конфиденциальности.
9.2. Исполнитель принимает разумные технические и организационные меры для защиты информации Пользователей.

<b>10. Заключительные положения</b>
10.1. Актуальная редакция настоящего Договора публикуется в Сервисе.
10.2. Продолжение использования Сервиса после публикации новой редакции означает принятие её условий в той мере, в какой это допускается применимым законодательством.
10.3. По вопросам использования Сервиса Заказчик может обратиться в службу поддержки по указанным в Сервисе контактным данным."""


LIABILITY_TEXT = (
    "⚠️ <b>Ограничение ответственности и особые условия</b>\n\n"
    "1. <b>Ограничение ответственности:</b> Исполнитель не несёт ответственности за "
    "блокировку бота Telegram, изменения в API сторонних сервисов, упущенную выгоду Заказчика.\n\n"
    "2. <b>Законность использования:</b> Заказчик несёт единоличную ответственность за "
    "соблюдение законодательства, включая 152-ФЗ «О персональных данных».\n\n"
    "3. <b>Интеллектуальная собственность:</b> Передаётся неисключительное право "
    "использования бота. Заказчик не вправе публиковать исходный код без согласия Исполнителя.\n\n"
    "4. <b>Возврат средств:</b> За качественно оказанную услугу возврат не производится, "
    "так как результат имеет индивидуально-определённые свойства.\n\n"
    "5. <b>Расторжение:</b> Исполнитель вправе расторгнуть договор в одностороннем порядке "
    "при использовании бота для спама, мошенничества или иной незаконной деятельности."
)

# ============================================
# FIREBASE
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
# БОТ
# ============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ============================================
# ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК
# ============================================
@router.errors()
async def on_handler_error(event: ErrorEvent):
    print(f"🔥 ХЕНДЛЕР УПАЛ: {type(event.exception).__name__}: {event.exception}")
    try:
        if event.update.message:
            await event.update.message.answer("⚠️ Произошла ошибка. Попробуй ещё раз или нажми /start.")
        elif event.update.callback_query:
            await event.update.callback_query.answer()  # снимаем "часики" на кнопке
            await event.update.callback_query.message.answer(
                "⚠️ Произошла ошибка. Попробуй ещё раз или нажми /start."
            )
    except Exception:
        pass
    return True

# ============================================
# РЕЖИМ ТЕХ. РАБОТ (общий с сайтом через Firebase)
# ============================================
MAINTENANCE = {"on": False}
MAIN_LOOP = None

def tw(text: str) -> str:
    if MAINTENANCE["on"]:
        return f"{text}\n\n🚧 Технические работы!"
    return text

async def broadcast_maintenance():
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT id FROM users")
        users = [r[0] for r in await cursor.fetchall()]
    sent = 0
    for uid in users:
        try:
            await bot.send_message(
                uid,
                "🚧 <b>Технические работы!</b>\n"
                "Сайт и некоторые функции могут временно работать нестабильно. "
                "Тех. работы временны — скоро всё вернётся!",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass
    print(f"📢 Оповещение о тех. работах: {sent}/{len(users)}")

def _settings_listener(doc_snapshot, from_cache):
    """Слушает документ settings/main в Firebase (2 параметра у DocumentSnapshot)"""
    try:
        data = doc_snapshot.to_dict() if doc_snapshot.exists else {}
        on = bool((data or {}).get("maintenance", False))
        prev = MAINTENANCE["on"]
        MAINTENANCE["on"] = on
        print(f"🚧 Режим тех. работ: {'ВКЛЮЧЕН' if on else 'выключен'}")
        if on and not prev and MAIN_LOOP:
            MAIN_LOOP.call_soon_threadsafe(MAIN_LOOP.create_task, broadcast_maintenance())
    except Exception as e:
        print(f"⚠️ Ошибка в settings_listener: {e}")

def start_settings_listener():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_event_loop()
    firebase_db.collection("settings").document("main").on_snapshot(_settings_listener)
    print("👂 Listener тех. работ запущен")

# ============================================
# СОСТОЯНИЯ
# ============================================
class OrderState(StatesGroup):
    choosing_package = State()
    choosing_server_tier = State()
    choosing_addons = State()
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
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_number TEXT UNIQUE,
            user_id INTEGER, service TEXT, details TEXT, price REAL,
            status TEXT DEFAULT 'new', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
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
# ПРОМОКОДЫ
# ============================================
async def get_promo(code: str):
    """Возвращает (discount, uses_left) или None. НЕ списывает активацию."""
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute(
            "SELECT discount, uses_left FROM promos WHERE code=?", (code.strip().upper(),)
        )
        return await cursor.fetchone()

async def consume_promo(code: str) -> bool:
    """Атомарно списывает одну активацию. True — если списание прошло."""
    code = code.strip().upper()
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute(
            "UPDATE promos SET uses_left = uses_left - 1 WHERE code=? AND uses_left > 0", (code,)
        )
        await db.commit()
        return cursor.rowcount > 0

# ============================================
# РАСЧЁТ ЦЕНЫ
# ============================================
async def calculate_price(base_price: float, user_id: int, promo_discount: int = 0, promo_code: str = None):
    """Чистый расчёт цены. Промокод только ВАЛИДИРУЕТСЯ, списание — отдельно при подтверждении заказа."""
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

    if promo_discount > 0:
        discount += promo_discount
        reasons.append(f"промокод {html.escape((promo_code or '').strip().upper())}")

    discount = min(discount, 20)
    final_price = round(base_price * (1 - discount / 100), 2)
    reason_str = f"\n🎁 Скидка {discount}% ({', '.join(reasons)})" if discount > 0 else ""

    return final_price, reason_str

def get_status_emoji(status: str) -> str:
    return {
        "new": "🟡 Создан", "working": "🔵 В работе", "done": "🟢 Готов",
        "cancelled": "🔴 Отменен", "closed": "⚫ Закрыт",
    }.get(status, "❓ Неизвестно")

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Заказать разработку", callback_data="order_start")],
        [InlineKeyboardButton(text="👤 Мой профиль и заказы", callback_data="profile")],
        [InlineKeyboardButton(text="📄 Документация", callback_data="docs")],
        [InlineKeyboardButton(text="🌐 Наш сайт", url=SITE_URL)],
        [InlineKeyboardButton(text="💬 Техподдержка", url=SUPPORT_URL)]
    ])

def docs_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="doc_privacy")],
        [InlineKeyboardButton(text="📄 Публичная оферта", callback_data="doc_offer")],
        [InlineKeyboardButton(text="⚠️ Ограничение ответственности", callback_data="docs_liability")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="start_back_to_main")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Чаты с клиентами", callback_data="admin_chats")],
        [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promos")],
        [InlineKeyboardButton(text="📄 Документация", callback_data="docs")]
    ])

def back_kb(callback_data: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
    ])

def addons_kb(selected: list):
    rows = []
    for key, addon in ADDONS.items():
        mark = "✅" if key in selected else "⬜"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {addon['label']} (+{addon['price']:.0f}₽)",
            callback_data=f"add_{key}"
        )])
    rows.append([InlineKeyboardButton(text="✅ Продолжить", callback_data="addons_done")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="nav_back_from_addons")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def promo_prompt_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_details")]
    ])

# ============================================
# РАЗБИВКА ДЛИННЫХ СООБЩЕНИЙ
# ============================================
def split_telegram_text(text: str, limit: int = 3900):
    if len(text) <= limit:
        return [text]
    chunks = []
    rest = text
    while rest:
        if len(rest) <= limit:
            chunks.append(rest)
            break
        cut = rest.rfind("\n", 0, limit)
        if cut < 200:
            cut = limit
        chunks.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    return chunks

async def send_document_text(message: Message, text: str):
    """Отправляет длинный документ, разбивая на части. В конце — кнопка назад."""
    chunks = split_telegram_text(text)
    if chunks:
        chunks[-1] = tw(chunks[-1])
    for i, chunk in enumerate(chunks):
        markup = docs_kb() if i == len(chunks) - 1 else None
        await message.answer(chunk, parse_mode="HTML", reply_markup=markup)

# ============================================
# ЭКРАНЫ
# ============================================
async def show_package_screen(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Только бот", callback_data="pkg_bot_only")],
        [InlineKeyboardButton(text="🤖+ Бот + Сервер", callback_data="pkg_bot_server")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="start_back_to_main")]
    ])
    text = "🛠 <b>Что именно вы хотите заказать?</b>"
    if edit:
        await message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.choosing_package)

async def show_tiers_screen(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⚡ Базовый ({PRICE_SERVER_BASIC:.0f}₽/мес)", callback_data="srv_basic")],
        [InlineKeyboardButton(text="🚫 Премиум — stop list", callback_data="srv_stop")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_package")]
    ])
    text = (
        "🖥 <b>Выберите тариф хостинга:</b>\n\n"
        f"⚡ <b>Базовый:</b> {PRICE_SERVER_BASIC:.0f}₽/мес\n"
        "🚀 <b>Премиум:</b> stop list — временно недоступен"
    )
    if edit:
        await message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.choosing_server_tier)

async def show_addons_screen(message, state, edit=False):
    data = await state.get_data()
    selected = data.get("addons", [])
    kb = addons_kb(selected)
    text = (
        "🧩 <b>Дополнительные услуги (по желанию):</b>\n\n"
        "Нажимай, чтобы добавить или убрать услугу.\n"
        "Когда всё выберешь — жми «✅ Продолжить»."
    )
    if edit:
        await message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.choosing_addons)

async def show_details_prompt(message, state, edit=False):
    kb = back_kb("nav_back_from_details")
    text = "📝 Отлично! Опиши подробно, какого бота ты хочешь:"
    if edit:
        await message.edit_text(tw(text), reply_markup=kb)
    else:
        await message.answer(tw(text), reply_markup=kb)
    await state.set_state(OrderState.waiting_for_details)

async def show_promo_question(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Есть промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_details")]
    ])
    text = "💬 <b>Есть ли у вас промокод?</b>"
    if edit:
        await message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.waiting_for_promo)

# ============================================
# СТАРТ
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
        await message.answer(tw("👑 <b>Админ-панель:</b>"), reply_markup=admin_menu(), parse_mode="HTML")
    else:
        notice = ""
        if MAINTENANCE["on"]:
            notice = ("🚧 <b>Сейчас идут технические работы!</b>\n"
                      "Некоторые функции могут работать нестабильно.\n\n")
        await message.answer(
            tw(notice + "👋 <b>Привет!</b>\nЯ помогу тебе заказать идеального Telegram-бота."),
            reply_markup=main_menu(), parse_mode="HTML"
        )

# ============================================
# ДОКУМЕНТАЦИЯ
# ============================================
@router.callback_query(F.data == "docs")
async def docs_handler(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        tw("📄 <b>Документация</b>\n\nВыбери документ:"),
        reply_markup=docs_kb(), parse_mode="HTML"
    )

@router.callback_query(F.data == "doc_privacy")
async def doc_privacy_handler(call: CallbackQuery):
    await call.answer()
    await send_document_text(call.message, PRIVACY_POLICY)

@router.callback_query(F.data == "doc_offer")
async def doc_offer_handler(call: CallbackQuery):
    await call.answer()
    await send_document_text(call.message, PUBLIC_OFFER)

@router.callback_query(F.data == "docs_liability")
async def docs_liability_handler(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(tw(LIABILITY_TEXT), reply_markup=back_kb("docs"), parse_mode="HTML")

# ============================================
# НАВИГАЦИЯ
# ============================================
@router.callback_query(F.data == "nav_package")
async def nav_package(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_package_screen(call.message, state, edit=True)

@router.callback_query(F.data == "nav_tiers")
async def nav_tiers(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_tiers_screen(call.message, state, edit=True)

@router.callback_query(F.data == "nav_addons")
async def nav_addons(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_addons_screen(call.message, state, edit=True)

@router.callback_query(F.data == "nav_details")
async def nav_details(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_details_prompt(call.message, state, edit=True)

@router.callback_query(F.data == "nav_promo")
async def nav_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_promo_question(call.message, state, edit=True)

@router.callback_query(F.data == "nav_back_from_addons")
async def nav_back_from_addons(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    if data.get('package') == 'bot_server':
        await show_tiers_screen(call.message, state, edit=True)
    else:
        await show_package_screen(call.message, state, edit=True)

@router.callback_query(F.data == "nav_back_from_details")
async def nav_back_from_details(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await show_addons_screen(call.message, state, edit=True)

@router.callback_query(F.data == "start_back_to_main")
async def start_back_to_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    kb = admin_menu() if call.from_user.id == ADMIN_ID else main_menu()
    await call.message.edit_text(tw("🏠 <b>Главное меню:</b>"), reply_markup=kb, parse_mode="HTML")

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
        package="bot_only", package_label="🤖 Только бот",
        server_tier=None, server_tier_label=None,
        base_price=PRICE_BOT_ONLY, service_name="Разработка бота",
        addons=[], addons_price=0.0, addons_label=None
    )
    await show_addons_screen(call.message, state, edit=True)

@router.callback_query(F.data == "pkg_bot_server", OrderState.choosing_package)
async def pkg_bot_server(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(
        package="bot_server", package_label="🤖+ Бот + Сервер",
        base_price=PRICE_BOT_ONLY, service_name="Разработка бота",
        addons=[], addons_price=0.0, addons_label=None
    )
    await show_tiers_screen(call.message, state, edit=True)

@router.callback_query(F.data.in_(["srv_basic", "srv_stop"]), OrderState.choosing_server_tier)
async def process_server_tier(call: CallbackQuery, state: FSMContext):
    if call.data == "srv_stop":
        await call.answer("🚫 Премиум сейчас в stop list!", show_alert=True)
        return
    await call.answer()
    data = await state.get_data()
    base_price = data.get('base_price', PRICE_BOT_ONLY)
    await state.update_data(
        package="bot_server", package_label="🤖+ Бот + Сервер",
        server_tier="basic",
        server_tier_label=f"⚡ Базовый ({PRICE_SERVER_BASIC:.0f}₽/мес)",
        base_price=base_price + PRICE_SERVER_BASIC,
        service_name="Разработка бота + Хостинг (Базовый)"
    )
    await show_addons_screen(call.message, state, edit=True)

@router.callback_query(F.data.startswith("add_"), OrderState.choosing_addons)
async def toggle_addon(call: CallbackQuery, state: FSMContext):
    key = call.data.replace("add_", "")
    if key not in ADDONS:
        await call.answer("❌ Неизвестная услуга")
        return
    data = await state.get_data()
    selected = data.get("addons", [])
    if key in selected:
        selected.remove(key)
        await call.answer("➖ Убрано")
    else:
        selected.append(key)
        await call.answer("➕ Добавлено")
    await state.update_data(addons=selected)
    await call.message.edit_reply_markup(reply_markup=addons_kb(selected))

@router.callback_query(F.data == "addons_done", OrderState.choosing_addons)
async def addons_done(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    selected = data.get("addons", [])
    addons_price = sum(ADDONS[k]["price"] for k in selected if k in ADDONS)
    addons_label = ", ".join(f"{ADDONS[k]['label']} (+{ADDONS[k]['price']:.0f}₽)" for k in selected if k in ADDONS) or None
    await state.update_data(addons_price=addons_price, addons_label=addons_label)
    await show_details_prompt(call.message, state, edit=True)

@router.message(OrderState.waiting_for_details)
async def process_details(message: Message, state: FSMContext):
    await state.update_data(details=message.text)
    await show_promo_question(message, state, edit=False)

@router.callback_query(F.data == "enter_promo", OrderState.waiting_for_promo)
async def enter_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(tw("✏️ Введите ваш промокод:"), reply_markup=back_kb("nav_promo"))

@router.callback_query(F.data == "skip_promo", OrderState.waiting_for_promo)
async def skip_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await process_promo_logic(call.message, state, promo_code=None, user_id=call.from_user.id)

@router.message(OrderState.waiting_for_promo)
async def process_promo_msg(message: Message, state: FSMContext):
    await process_promo_logic(message, state, promo_code=message.text.strip(), user_id=message.from_user.id)

async def process_promo_logic(target, state: FSMContext, promo_code: str = None, user_id: int = None):
    """Показывает предпросмотр заказа. Промокод ТОЛЬКО проверяется (активация НЕ списывается).
    Списание происходит один раз в confirm_and_create_order."""
    try:
        data = await state.get_data()
        total_base = data.get('base_price', 0) + data.get('addons_price', 0)

        promo_discount = 0
        normalized_code = None
        if promo_code:
            normalized_code = promo_code.strip().upper()
            promo = await get_promo(normalized_code)
            if not promo or promo[1] <= 0:
                # Состояние НЕ меняем — пользователь остаётся в waiting_for_promo
                # и может ввести код заново или нажать «Пропустить»
                await target.answer(
                    tw(f"❌ Промокод «{html.escape(normalized_code)}» недействителен или закончились активации.\n"
                       "Попробуй другой код или нажми «⏭ Пропустить»."),
                    reply_markup=promo_prompt_kb()
                )
                return
            promo_discount = promo[0]

        final_price, reason_str = await calculate_price(
            total_base, user_id, promo_discount=promo_discount, promo_code=normalized_code
        )

        await state.update_data(
            final_price=final_price, promo_reason=reason_str, promo_code=normalized_code
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_promo")]
        ])

        addons_line = f"🧩 Доп. услуги: {html.escape(data.get('addons_label') or '')}\n" if data.get('addons_label') else ""
        tier_line = f"🖥 Тариф: {html.escape(data.get('server_tier_label') or '')}\n" if data.get('server_tier_label') else ""

        await target.answer(
            tw(
                f"📋 <b>Предварительный итог:</b>\n"
                f"📦 План: {html.escape(data.get('package_label', '🤖 Только бот'))}\n"
                f"{tier_line}"
                f"{addons_line}"
                f"🛠 Услуга: {html.escape(data.get('service_name', 'Заказ'))}\n"
                f"📝 ТЗ: {html.escape(data.get('details', '(не указано)'))}\n\n"
                f"💰 <b>Итоговая цена: {final_price}₽</b>{reason_str}"
            ),
            reply_markup=kb, parse_mode="HTML"
        )
        await state.set_state(OrderState.confirming_order)
    except Exception as e:
        print(f"❌ Ошибка в process_promo_logic: {type(e).__name__}: {e}")
        try:
            await target.answer("⚠️ Произошла ошибка. Нажми /start и попробуй ещё раз.")
        except Exception:
            pass

@router.callback_query(F.data == "confirm_order", OrderState.confirming_order)
async def confirm_and_create_order(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    user_id = call.from_user.id
    total_base = data.get('base_price', 0) + data.get('addons_price', 0)
    promo_code = data.get('promo_code')

    # --- ФИНАЛЬНЫЙ расчёт цены и ОДНОРАЗОВОЕ списание промокода ---
    promo_discount = 0
    promo_note = ""
    if promo_code:
        promo = await get_promo(promo_code)
        if promo and promo[1] > 0:
            if await consume_promo(promo_code):
                promo_discount = promo[0]
            else:
                promo_note = "\n\nℹ️ Промокод только что закончился — заказ оформлен без скидки по нему."
        else:
            promo_note = "\n\nℹ️ Промокод недействителен — заказ оформлен без скидки по нему."

    amount, reason_str = await calculate_price(
        total_base, user_id, promo_discount=promo_discount, promo_code=promo_code
    )

    service_name = data.get('service_name', 'Заказ')
    details = data.get('details', '')
    package_label = data.get('package_label', '🤖 Только бот')
    server_tier_label = data.get('server_tier_label')
    addons_label = data.get('addons_label')
    user_contact = f"@{call.from_user.username}" if call.from_user.username else f"ID: {user_id}"

    # --- Сохранение в SQLite (с повтором при коллизии номера) ---
    order_number = None
    for _attempt in range(5):
        candidate = await generate_order_number()
        try:
            async with aiosqlite.connect("nil_bots.db") as db_sqlite:
                await db_sqlite.execute("""
                    INSERT INTO orders (order_number, user_id, service, details, price, status)
                    VALUES (?, ?, ?, ?, ?, 'new')
                """, (candidate, user_id, service_name, details, amount))
                await db_sqlite.execute("UPDATE users SET first_order=0 WHERE id=?", (user_id,))
                await db_sqlite.commit()
            order_number = candidate
            break
        except aiosqlite.IntegrityError:
            continue  # номер занят — генерируем новый

    if not order_number:
        await call.message.answer("⚠️ Не удалось создать заказ. Нажми /start и попробуй ещё раз.")
        await state.clear()
        return

    # --- Сохранение в Firebase (не должно ломать заказ для клиента) ---
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
            "addons": data.get('addons', []),
            "addons_label": addons_label,
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

    await call.message.answer(
        tw(
            f"🎉 <b>Заказ #{order_number} успешно создан!</b>\n\n"
            f"Я передал ваше ТЗ разработчику. В ближайшее время с вами свяжутся.\n\n"
            f"📊 <b>Отслеживать статус заказа:</b>\n{SITE_URL}\n(номер: <b>{order_number}</b>){promo_note}"
        ),
        reply_markup=main_menu(), parse_mode="HTML"
    )

    # --- Уведомление админу (любая ошибка НЕ должна показываться клиенту) ---
    plan_line = f"📦 План: {package_label}"
    if server_tier_label:
        plan_line += f"\n🖥 Тариф сервера: {server_tier_label}"
    if addons_label:
        plan_line += f"\n🧩 Доп. услуги: {addons_label}"

    try:
        await bot.send_message(
            ADMIN_ID,
            tw(
                f"🔥 <b>НОВЫЙ ЗАКАЗ #{order_number}</b>\n\n"
                f"👤 Клиент: {html.escape(user_contact)} (ID: {user_id})\n"
                f"{html.escape(plan_line)}\n"
                f"🛠 Услуга: {html.escape(service_name)}\n"
                f"💬 ТЗ: {html.escape(details)}\n"
                f"💵 Сумма: {amount}₽\n\n"
                f"⚠️ Требуется связаться с клиентом!"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"⚠️ Не удалось уведомить админа о заказе {order_number}: {type(e).__name__}: {e}")

# ============================================
# ПРОФИЛЬ
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

    text = f"👤 <b>Ваш профиль:</b>\n🆔 ID: <code>{user_id}</code>\n📱 Username: @{username}\n🎂 День рождения: {bday}\n\n"

    if orders:
        text += f"📦 <b>Ваши заказы ({len(orders)}):</b>\n"
        for o in orders:
            order_num, service, price, status, date = o
            status_emoji = get_status_emoji(status)
            short_date = date.split(' ')[0] if date else "Неизвестно"
            text += f"\n🔹 <b>#{order_num}</b> ({short_date})\n   {html.escape(str(service))} | {price}₽\n   Статус: {status_emoji}"
    else:
        text += "📭 У вас пока нет заказов."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎂 Изменить ДР", callback_data="set_bday")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="start_back_to_main")]
    ])
    await call.message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "set_bday")
async def set_bday(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(tw("🎂 Напиши дату в формате ДД.ММ:"), reply_markup=back_kb("profile"))
    await state.set_state(SetBdayState.waiting_for_bday)

@router.message(SetBdayState.waiting_for_bday)
async def save_bday(message: Message, state: FSMContext):
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("UPDATE users SET birthday=? WHERE id=?", (message.text.strip(), message.from_user.id))
        await db.commit()
    await state.clear()
    await message.answer(tw("✅ День рождения сохранён!"), reply_markup=main_menu())

# ============================================
# АДМИНКА
# ============================================
@router.callback_query(F.data == "admin_chats")
async def admin_chats(call: CallbackQuery):
    await call.answer()
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT DISTINCT user_id FROM messages")
        users = await cursor.fetchall()
    if not users:
        return await call.message.edit_text(tw("💬 Диалогов пока нет."), reply_markup=back_kb("start_back_to_main"))
    kb = [[InlineKeyboardButton(text=f"👤 {u[0]}", callback_data=f"chat_{u[0]}")] for u in users]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="start_back_to_main")])
    await call.message.edit_text(tw("💬 <b>Выберите пользователя:</b>"), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")

@router.callback_query(F.data.startswith("chat_"))
async def read_chat(call: CallbackQuery):
    await call.answer()
    user_id = int(call.data.split("_")[1])
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT text, is_user FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 15", (user_id,))
        msgs = await cursor.fetchall()
    history = "\n".join([f"{'👤 Клиент' if m[1] else '👑 Вы'}: {html.escape(str(m[0]))}" for m in reversed(msgs)])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Написать ответ", callback_data=f"reply_{user_id}")],
        [InlineKeyboardButton(text="🔙 К чатам", callback_data="admin_chats")]
    ])
    await call.message.edit_text(tw(f"💬 <b>Чат с {user_id}:</b>\n\n{history}"), reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("reply_"))
async def start_admin_reply(call: CallbackQuery, state: FSMContext):
    await call.answer()
    user_id = int(call.data.split("_")[1])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminReplyState.waiting_for_reply)
    await call.message.edit_text(tw(f"✏️ Введи ответ для {user_id}:\n(или /cancel)"), reply_markup=back_kb("admin_chats"))

@router.message(AdminReplyState.waiting_for_reply)
async def admin_send_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    if not target_user_id:
        await state.clear()
        return
    try:
        await bot.send_message(target_user_id, tw(f"👑 <b>Ответ от Nil Bots:</b>\n\n{html.escape(message.text)}"), parse_mode="HTML")
        async with aiosqlite.connect("nil_bots.db") as db:
            await db.execute("INSERT INTO messages (user_id, text, is_user) VALUES (?, ?, 0)", (target_user_id, message.text))
            await db.commit()
        await message.answer(tw(f"✅ Отправлено пользователю {target_user_id}."), reply_markup=admin_menu())
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    await state.clear()

@router.message(Command("cancel"))
async def cancel_state(message: Message, state: FSMContext):
    await state.clear()
    kb = admin_menu() if message.from_user.id == ADMIN_ID else main_menu()
    await message.answer(tw("❌ Действие отменено."), reply_markup=kb)

@router.callback_query(F.data == "admin_promos")
async def admin_promos(call: CallbackQuery):
    await call.answer()
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT code, discount, uses_left FROM promos ORDER BY code")
        promos = await cursor.fetchall()

    text = "🎟 <b>Управление промокодами:</b>\n\n"
    if promos:
        for code, discount, uses_left in promos:
            text += f"• <code>{html.escape(str(code))}</code> — {discount}% (осталось: {uses_left})\n"
    else:
        text += "Промокодов пока нет."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="create_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="start_back_to_main")]
    ])
    await call.message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "create_promo")
async def create_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(tw("✏️ Введи название промокода (например, NIL10):"), reply_markup=back_kb("admin_promos"))
    await state.set_state(AddPromoState.waiting_for_code)

@router.message(AddPromoState.waiting_for_code)
async def promo_code_input(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if not code or " " in code:
        await message.answer("❌ Код не должен быть пустым и содержать пробелы.")
        return
    existing = await get_promo(code)
    await state.update_data(code=code)
    note = "\n⚠️ Такой код уже существует — будет заменён." if existing else ""
    await message.answer(tw(f"💰 Введи размер скидки в % (1-100):{note}"))
    await state.set_state(AddPromoState.waiting_for_discount)

@router.message(AddPromoState.waiting_for_discount)
async def promo_discount_input(message: Message, state: FSMContext):
    try:
        discount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи целое число.")
        return
    if not (1 <= discount <= 100):
        await message.answer("❌ Скидка от 1 до 100.")
        return
    await state.update_data(discount=discount)
    await message.answer(tw("🔢 Введи количество активаций:"))
    await state.set_state(AddPromoState.waiting_for_uses)

@router.message(AddPromoState.waiting_for_uses)
async def promo_uses_input(message: Message, state: FSMContext):
    try:
        uses = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи целое число.")
        return
    if uses <= 0:
        await message.answer("❌ Должно быть больше 0.")
        return
    data = await state.get_data()
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("INSERT OR REPLACE INTO promos (code, discount, uses_left) VALUES (?, ?, ?)",
                       (data['code'], data['discount'], uses))
        await db.commit()
    await state.clear()
    await message.answer(
        tw(f"✅ Промокод <b>{html.escape(data['code'])}</b> создан!\nСкидка: {data['discount']}%\nАктиваций: {uses}"),
        reply_markup=admin_menu(), parse_mode="HTML"
    )

# ============================================
# ПОДДЕРЖКА (последний хендлер!)
# ============================================
@router.message(F.text)
async def support_msg(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        return
    # Не перехватываем сообщения, пока пользователь оформляет заказ или меняет ДР
    current_state = await state.get_state()
    if current_state is not None:
        return
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("INSERT INTO messages (user_id, text, is_user) VALUES (?, ?, 1)",
                         (message.from_user.id, message.text))
        await db.commit()
    try:
        await bot.send_message(ADMIN_ID, f"💬 <b>Сообщение от {html.escape(message.from_user.full_name)}</b> (ID: {message.from_user.id}):\n\n{html.escape(message.text)}", parse_mode="HTML")
    except Exception:
        pass
    await message.answer(tw("✅ Отправлено! Администратор ответит вам в ближайшее время."))

# ============================================
# ЗАПУСК
# ============================================
async def main():
    await init_db()
    print("🚀 Бот nil.bots запущен!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"💰 Цены: Бот={PRICE_BOT_ONLY}₽, Basic={PRICE_SERVER_BASIC}₽, Премиум=STOP LIST")
    start_settings_listener()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
