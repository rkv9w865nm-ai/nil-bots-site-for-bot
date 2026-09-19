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

============================================
НАСТРОЙКИ
============================================
BOTTOKEN = os.environ.get("BOTTOKEN")
ADMINID = int(os.environ.get("ADMINID", "0"))

PRICEBOTONLY = float(os.environ.get("PRICEBOTONLY", "115"))
PRICESERVERBASIC = float(os.environ.get("PRICESERVERBASIC", "300"))

ADDONS = {
    "support_bot": {
        "label": "🛟 Отдельный бот тех. поддержки",
        "price": float(os.environ.get("PRICEADDONSUPPORT", "99")),
    },
    "priority": {
        "label": "⚡ Приоритет к заказу",
        "price": float(os.environ.get("PRICEADDONPRIORITY", "50")),
    },
}

SITE_URL = "https://nil-bots-site-with-bot.vercel.app/"
SUPPORTURL = "https://t.me/nilbotssupport_bot"

============================================
ПОЛНЫЕ ТЕКСТЫ ДОКУМЕНТОВ
============================================
PRIVACY_POLICY = """\
🔒 ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ

1. Общие положения
1.1. Настоящая Политика конфиденциальности определяет порядок сбора, обработки, хранения и защиты персональных данных Пользователей онлайн-сервиса (далее — «Сервис»).
1.2. Обработка персональных данных Пользователей осуществляется в соответствии с настоящей Политикой и применимым законодательством.
1.3. Используя Сервис, Пользователь подтверждает, что ознакомился с настоящей Политикой.

2. Обрабатываемые данные
2.1. В зависимости от используемого функционала Оператор может обрабатывать:
• имя и контактные данные;
• идентификаторы учётной записи;
• адрес электронной почты и номер телефона, если они предоставлены;
• сведения о заказах и подписках;
• сведения о платежах и их статусе;
• технические данные устройства и подключения;
• информацию, предоставленную Пользователем при обращении в поддержку.
2.2. Оператор не запрашивает пароли, платёжные коды и иные конфиденциальные данные, если их предоставление не требуется соответствующим официальным сервисом.

3. Цели обработки
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

4. Основания обработки
4.1. Обработка персональных данных осуществляется на основании согласия Пользователя, необходимости исполнения договора, выполнения требований законодательства, а также иных законных оснований, предусмотренных применимым законодательством.

5. Передача данных третьим лицам
5.1. Оператор не продаёт персональные данные Пользователей третьим лицам.
5.2. Данные могут передаваться платёжным, техническим, информационным и иным поставщикам услуг в объёме, необходимом для функционирования Сервиса.
5.3. Передача данных государственным органам осуществляется исключительно в случаях и порядке, предусмотренных применимым законодательством.

6. Платёжные данные
6.1. Обработка банковских карт и иных платёжных реквизитов может осуществляться непосредственно сторонним платёжным провайдером.
6.2. Если иное не предусмотрено используемой платёжной инфраструктурой, Оператор не хранит полные реквизиты банковских карт Пользователей.

7. Хранение и защита данных
7.1. Персональные данные хранятся только в течение периода, необходимого для достижения целей обработки, либо в течение срока, установленного законодательством.
7.2. Оператор принимает разумные технические и организационные меры для защиты данных от утраты, изменения, раскрытия и несанкционированного доступа.
7.3. После достижения целей обработки данные могут быть удалены или обезличены, если их дальнейшее хранение не требуется законодательством.

8. Права Пользователя
8.1. В предусмотренных законом случаях Пользователь вправе запросить доступ к своим персональным данным, их изменение или удаление, а также воспользоваться иными предусмотренными законодательством правами.
8.2. Для реализации своих прав Пользователь может обратиться к Оператору по указанным в Сервисе контактным данным.

9. Изменение Политики
9.1. Оператор вправе изменять настоящую Политику в связи с изменением законодательства, функциональности Сервиса или порядка обработки данных.
9.2. Актуальная редакция Политики публикуется в Сервисе.

10. Контактная информация
10.1. По вопросам использования Сервиса Заказчик может обратиться в службу поддержки по указанным в Сервисе контактным данным."""

PUBLIC_OFFER = """\
📄 ПУБЛИЧНАЯ ОФЕРТА
Пользовательское соглашение

1. Общие положения
1.1. Настоящая оферта (далее — «Договор») регулирует отношения между Исполнителем и Заказчиком в связи с предоставлением Исполнителем цифровых товаров и/или услуг посредством онлайн-сервиса (далее — «Сервис»).
1.2. Использование Сервиса, регистрация, оформление заказа, оплата услуг или получение доступа к цифровым материалам означают полное и безоговорочное принятие Заказчиком условий настоящего Договора.
1.3. В случае несогласия с условиями Договора Заказчик обязан прекратить использование Сервиса.

2. Предмет договора
2.1. В соответствии с условиями настоящего Договора Исполнитель принимает на себя обязательство по предоставлению Заказчику цифровых товаров и/или услуг, а Заказчик обязуется принять указанные товары и услуги и произвести их оплату в порядке и на условиях, определённых настоящей офертой.
2.2. Доступ к услугам и цифровым товарам обеспечивается посредством программных, технических и информационных средств Сервиса.
2.3. Конкретный состав, стоимость, срок действия и условия предоставления соответствующего товара или услуги указываются в Сервисе до момента оплаты.

3. Порядок предоставления услуг
3.1. После успешной оплаты Заказчику предоставляется доступ к приобретённому товару или услуге в порядке, предусмотренном Сервисом.
3.2. Заказчик самостоятельно обеспечивает наличие необходимых технических средств и доступа к сети Интернет.
3.3. Срок предоставления доступа определяется условиями соответствующего тарифа или заказа.

4. Оплата и возвраты
4.1. Стоимость определяется тарифами на момент оформления заказа.
4.2. Оплата производится доступными в Сервисе платёжными инструментами.
4.3. Возврат осуществляется в соответствии с законодательством.
4.4. При технической проблеме Заказчик вправе обратиться в поддержку.

5. Права и обязанности Заказчика
5.1. Заказчик обязуется использовать Сервис исключительно законным способом и соблюдать условия настоящего Договора.
5.2. Запрещается использовать Сервис для мошенничества, нарушения законодательства, распространения вредоносного программного обеспечения, нарушения прав третьих лиц или иных противоправных действий.
5.3. Заказчик несёт ответственность за достоверность предоставляемой им информации и законность своих действий при использовании Сервиса.

6. Интеллектуальная собственность
6.1. Материалы, размещённые в Сервисе, охраняются законодательством об интеллектуальной собственности.
6.2. Приобретение товара или услуги не означает передачу Заказчику исключительных прав на соответствующие материалы.
6.3. Копирование, перепродажа, распространение, публикация и передача материалов третьим лицам запрещены, если иное прямо не предусмотрено условиями конкретного товара или законодательством.

7. Права Исполнителя
7.1. Исполнитель вправе временно ограничить работу Сервиса для проведения технических работ, обновлений или устранения неисправностей.
7.2. Исполнитель вправе ограничить или прекратить доступ Заказчика к Сервису при нарушении настоящего Договора или применимого законодательства.
7.3. Исполнитель вправе изменять функциональность Сервиса, условия тарифов и настоящий Договор с публикацией актуальной редакции в Сервисе.

8. Ответственность
8.1. Исполнитель не гарантирует бесперебойную работу Сервиса и достижение Заказчиком какого-либо конкретного результата, если такой результат прямо не предусмотрен условиями приобретённой услуги.
8.2. Исполнитель не несёт ответственности за сбои, вызванные действиями третьих лиц, операторов связи, платёжных систем, техническими неисправностями или иными обстоятельствами, находящимися вне разумного контроля Исполнителя.
8.3. Заказчик самостоятельно несёт ответственность за использование предоставленных товаров, материалов и услуг.

9. Конфиденциальность
9.1. Обработка персональных данных осуществляется в соответствии с отдельной Политикой конфиденциальности.
9.2. Исполнитель принимает разумные технические и организационные меры для защиты информации Пользователей.

10. Заключительные положения
10.1. Актуальная редакция настоящего Договора публикуется в Сервисе.
10.2. Продолжение использования Сервиса после публикации новой редакции означает принятие её условий в той мере, в какой это допускается применимым законодательством.
10.3. По вопросам использования Сервиса Заказчик может обратиться в службу поддержки по указанным в Сервисе контактным данным."""

LIABILITY_TEXT = (
    "⚠️ Ограничение ответственности и особые условия\n\n"
    "1. Ограничение ответственности: Исполнитель не несёт ответственности за "
    "блокировку бота Telegram, изменения в API сторонних сервисов, упущенную выгоду Заказчика.\n\n"
    "2. Законность использования: Заказчик несёт единоличную ответственность за "
    "соблюдение законодательства, включая 152-ФЗ «О персональных данных».\n\n"
    "3. Интеллектуальная собственность: Передаётся неисключительное право "
    "использования бота. Заказчик не вправе публиковать исходный код без согласия Исполнителя.\n\n"
    "4. Возврат средств: За качественно оказанную услугу возврат не производится, "
    "так как результат имеет индивидуально-определённые свойства.\n\n"
    "5. Расторжение: Исполнитель вправе расторгнуть договор в одностороннем порядке "
    "при использовании бота для спама, мошенничества или иной незаконной деятельности."
)

============================================
FIREBASE
============================================
firebasekeyjson = os.environ.get("FIREBASEKEYJSON")
if firebasekeyjson:
    cred = credentials.Certificate(json.loads(firebasekeyjson))
else:
    current_dir = os.path.dirname(os.path.abspath(file))
    cred = credentials.Certificate(os.path.join(current_dir, "firebase-key.json"))

firebaseadmin.initializeapp(cred)
firebase_db = firestore.client()

if not BOT_TOKEN:
    raise SystemExit("❌ ОШИБКА: Переменная BOT_TOKEN не задана!")

============================================
БОТ
============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

============================================
FIRESTORE-ХЕЛПЕРЫ (промокоды + пользователи)
============================================
def fbpromo_get(code: str):
    snap = firebase_db.collection("promos").document(code).get()
    if not snap.exists:
        return None
    d = snap.to_dict() or {}
    return (int(d.get("discount", 0)), int(d.get("uses_left", 0)))

async def get_promo(code: str):
    """Возвращает (discount, uses_left) или None. НЕ списывает активацию."""
    return await asyncio.tothread(fbpromoget, code.strip().upper())

def fbpromo_consume(code: str) -> bool:
    """Атомарная транзакция: списывает 1 активацию, защищает от двойного списания."""
    ref = firebase_db.collection("promos").document(code)

    @firestore.transactional
    def txn(transaction, docref):
        snap = doc_ref.get(transaction)
        if not snap.exists:
            return False
        left = int((snap.todict() or {}).get("usesleft", 0))
        if left  bool:
    return await asyncio.tothread(fbpromoconsume, code.strip().upper())

def fbpromo_set(code: str, discount: int, uses: int):
    firebase_db.collection("promos").document(code).set({
        "code": code,
        "discount": int(discount),
        "uses_left": int(uses),
        "created_at": datetime.datetime.now().isoformat(),
    })

def fbpromo_list():
    out = []
    for d in firebase_db.collection("promos").stream():
        v = d.to_dict() or {}
        out.append((v.get("code", d.id), int(v.get("discount", 0)), int(v.get("uses_left", 0))))
    out.sort(key=lambda x: x[0])
    return out

def fbuserget(userid: int):
    snap = firebasedb.collection("users").document(str(userid)).get()
    return snap.to_dict() if snap.exists else None

async def getuser(userid: int):
    return await asyncio.tothread(fbuserget, user_id)

def fbuserensure(userid: int, username):
    ref = firebasedb.collection("users").document(str(userid))
    snap = ref.get()
    if not snap.exists:
        data = {
            "userid": userid,
            "username": username,
            "birthday": None,
            "first_order": 1,
            "created_at": datetime.datetime.now().isoformat(),
        }
        ref.set(data)
        return data
    return snap.to_dict()

async def ensureuser(userid: int, username):
    return await asyncio.tothread(fbuserensure, user_id, username)

def fbuserset(userid: int, fields: dict):
    firebasedb.collection("users").document(str(userid)).set(fields, merge=True)

def fbuser_ids():
    return [(d.todict() or {}).get("userid") or int(d.id)
            for d in firebase_db.collection("users").stream()]

def fborder_exists(number: str) -> bool:
    return firebase_db.collection("orders").document(number).get().exists

def fbordersof(userid: int):
    docs = firebasedb.collection("orders").where("userid", "==", user_id).stream()
    out = [d.to_dict() for d in docs]
    out.sort(key=lambda o: o.get("created_at") or "", reverse=True)
    return out

============================================
ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК
============================================
@router.errors()
async def onhandlererror(event: ErrorEvent):
    print(f"🔥 ХЕНДЛЕР УПАЛ: {type(event.exception).name}: {event.exception}")
    try:
        if event.update.message:
            await event.update.message.answer("⚠️ Произошла ошибка. Попробуй ещё раз или нажми /start.")
        elif event.update.callback_query:
            await event.update.callback_query.answer()
            await event.update.callback_query.message.answer(
                "⚠️ Произошла ошибка. Попробуй ещё раз или нажми /start."
            )
    except Exception:
        pass
    return True

============================================
РЕЖИМ ТЕХ. РАБОТ (общий с сайтом через Firebase)
============================================
MAINTENANCE = {"on": False}
MAIN_LOOP = None

def tw(text: str) -> str:
    if MAINTENANCE["on"]:
        return f"{text}\n\n🚧 Технические работы!"
    return text

async def broadcast_maintenance():
    userids = await asyncio.tothread(fbuser_ids)
    sent = 0
    for uid in user_ids:
        try:
            await bot.send_message(
                uid,
                "🚧 Технические работы!\n"
                "Сайт и некоторые функции могут временно работать нестабильно. "
                "Тех. работы временны — скоро всё вернётся!",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass
    print(f"📢 Оповещение о тех. работах: {sent}/{len(user_ids)}")

def settingslistener(snapshot, changes, read_time):
    """Слушает документ settings/main в Firebase (3 параметра)."""
    try:
        data = snapshot.to_dict() if snapshot.exists else {}
        on = bool((data or {}).get("maintenance", False))
        prev = MAINTENANCE["on"]
        MAINTENANCE["on"] = on
        print(f"🚧 Режим тех. работ: {'ВКЛЮЧЕН' if on else 'выключен'}")
        if on and not prev and MAIN_LOOP:
            MAINLOOP.callsoonthreadsafe(MAINLOOP.createtask, broadcastmaintenance())
    except Exception as e:
        print(f"⚠️ Ошибка в settings_listener: {e}")

def startsettingslistener():
    global MAIN_LOOP
    MAINLOOP = asyncio.getevent_loop()
    firebasedb.collection("settings").document("main").onsnapshot(settingslistener)
    print("👂 Listener тех. работ запущен")

============================================
СОСТОЯНИЯ
============================================
class OrderState(StatesGroup):
    choosing_package = State()
    choosingservertier = State()
    choosing_addons = State()
    waitingfordetails = State()
    waitingforpromo = State()
    confirming_order = State()

class SetBdayState(StatesGroup):
    waitingforbday = State()

class AdminReplyState(StatesGroup):
    waitingforreply = State()

class AddPromoState(StatesGroup):
    waitingforcode = State()
    waitingfordiscount = State()
    waitingforuses = State()

============================================

============================================
async def init_db():
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, userid INTEGER, text TEXT, isuser INTEGER)""")
        await db.commit()

async def generateordernumber():
    for _ in range(20):
        number = f"NB-{random.randint(1000, 9999)}"
        if not await asyncio.tothread(fborderexists, number):
            return number
    return f"NB-{int(datetime.datetime.now().timestamp()) % 1000000}"

============================================
РАСЧЁТ ЦЕНЫ (пользователь — из Firestore)
============================================
async def calculateprice(baseprice: float, userid: int, promodiscount: int = 0, promo_code: str = None):
    """Чистый расчёт цены. Промокод только ВАЛИДИРУЕТСЯ, списание — при подтверждении."""
    user = await getuser(userid)

    discount = 0
    reasons = []

    if user and user.get("first_order") == 1:
        discount += 10
        reasons.append("первый заказ")

    bday = (user or {}).get("birthday")
    if bday:
        today = datetime.datetime.now().strftime("%d.%m")
        if bday == today:
            discount += 10
            reasons.append("день рождения")

    if promo_discount > 0:
        discount += promo_discount
        reasons.append(f"промокод {html.escape((promo_code or '').strip().upper())}")

    discount = min(discount, 20)
    finalprice = round(baseprice * (1 - discount / 100), 2)
    reason_str = f"\n🎁 Скидка {discount}% ({', '.join(reasons)})" if discount > 0 else ""

    return finalprice, reasonstr

def getstatusemoji(status: str) -> str:
    return {
        "new": "🟡 Создан", "working": "🔵 В работе", "done": "🟢 Готов",
        "cancelled": "🔴 Отменен", "closed": "⚫ Закрыт",
    }.get(status, "❓ Неизвестно")

============================================
КЛАВИАТУРЫ
============================================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Заказать разработку", callbackdata="orderstart")],
        [InlineKeyboardButton(text="👤 Мой профиль и заказы", callback_data="profile")],
        [InlineKeyboardButton(text="📄 Документация", callback_data="docs")],
        [InlineKeyboardButton(text="🌐 Наш сайт", url=SITE_URL)],
        [InlineKeyboardButton(text="💬 Техподдержка", url=SUPPORT_URL)]
    ])

def docs_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Политика конфиденциальности", callbackdata="docprivacy")],
        [InlineKeyboardButton(text="📄 Публичная оферта", callbackdata="docoffer")],
        [InlineKeyboardButton(text="⚠️ Ограничение ответственности", callbackdata="docsliability")],
        [InlineKeyboardButton(text="🔙 В главное меню", callbackdata="startbacktomain")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Чаты с клиентами", callbackdata="adminchats")],
        [InlineKeyboardButton(text="🎟 Промокоды", callbackdata="adminpromos")],
        [InlineKeyboardButton(text="📄 Документация", callback_data="docs")]
    ])

def backkb(callbackdata: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callbackdata=callbackdata)]
    ])

def addons_kb(selected: list):
    rows = []
    for key, addon in ADDONS.items():
        mark = "✅" if key in selected else "⬜"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {addon['label']} (+{addon['price']:.0f}₽)",
            callbackdata=f"add{key}"
        )])
    rows.append([InlineKeyboardButton(text="✅ Продолжить", callbackdata="addonsdone")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callbackdata="navbackfromaddons")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def promopromptkb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callbackdata="skippromo")],
        [InlineKeyboardButton(text="🔙 Назад", callbackdata="navdetails")]
    ])

============================================
РАЗБИВКА ДЛИННЫХ СООБЩЕНИЙ
============================================
def splittelegramtext(text: str, limit: int = 3900):
    if len(text) Что именно вы хотите заказать?"
    if edit:
        await message.edittext(tw(text), replymarkup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), replymarkup=kb, parsemode="HTML")
    await state.setstate(OrderState.choosingpackage)

async def showtiersscreen(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⚡ Базовый ({PRICESERVERBASIC:.0f}₽/мес)", callbackdata="srvbasic")],
        [InlineKeyboardButton(text="🚫 Премиум — stop list", callbackdata="srvstop")],
        [InlineKeyboardButton(text="🔙 Назад", callbackdata="navpackage")]
    ])
    text = (
        "🖥 Выберите тариф хостинга:\n\n"
        f"⚡ Базовый: {PRICESERVERBASIC:.0f}₽/мес\n"
        "🚀 Премиум: stop list — временно недоступен"
    )
    if edit:
        await message.edittext(tw(text), replymarkup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), replymarkup=kb, parsemode="HTML")
    await state.setstate(OrderState.choosingserver_tier)

async def showaddonsscreen(message, state, edit=False):
    data = await state.get_data()
    selected = data.get("addons", [])
    kb = addons_kb(selected)
    text = (
        "🧩 Дополнительные услуги (по желанию):\n\n"
        "Нажимай, чтобы добавить или убрать услугу.\n"
        "Когда всё выберешь — жми «✅ Продолжить»."
    )
    if edit:
        await message.edittext(tw(text), replymarkup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), replymarkup=kb, parsemode="HTML")
    await state.setstate(OrderState.choosingaddons)

async def showdetailsprompt(message, state, edit=False):
    kb = backkb("navbackfromdetails")
    text = "📝 Отлично! Опиши подробно, какого бота ты хочешь:"
    if edit:
        await message.edittext(tw(text), replymarkup=kb)
    else:
        await message.answer(tw(text), reply_markup=kb)
    await state.setstate(OrderState.waitingfor_details)

async def showpromoquestion(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Есть промокод", callbackdata="enterpromo")],
        [InlineKeyboardButton(text="⏭ Пропустить", callbackdata="skippromo")],
        [InlineKeyboardButton(text="🔙 Назад", callbackdata="navdetails")]
    ])
    text = "💬 Есть ли у вас промокод?"
    if edit:
        await message.edittext(tw(text), replymarkup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), replymarkup=kb, parsemode="HTML")
    await state.setstate(OrderState.waitingfor_promo)

============================================
СТАРТ
============================================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await ensureuser(message.fromuser.id, message.from_user.username)

    if message.fromuser.id == ADMINID:
        await message.answer(tw("👑 Админ-панель:"), replymarkup=adminmenu(), parse_mode="HTML")
    else:
        notice = ""
        if MAINTENANCE["on"]:
            notice = ("🚧 Сейчас идут технические работы!\n"
                      "Некоторые функции могут работать нестабильно.\n\n")
        await message.answer(
            tw(notice + "👋 Привет!\nЯ помогу тебе заказать идеального Telegram-бота."),
            replymarkup=mainmenu(), parse_mode="HTML"
        )

============================================
ДОКУМЕНТАЦИЯ
============================================
@router.callback_query(F.data == "docs")
async def docs_handler(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        tw("📄 Документация\n\nВыбери документ:"),
        replymarkup=docskb(), parse_mode="HTML"
    )

@router.callbackquery(F.data == "docprivacy")
async def docprivacyhandler(call: CallbackQuery):
    await call.answer()
    await senddocumenttext(call.message, PRIVACY_POLICY)

@router.callbackquery(F.data == "docoffer")
async def docofferhandler(call: CallbackQuery):
    await call.answer()
    await senddocumenttext(call.message, PUBLIC_OFFER)

@router.callbackquery(F.data == "docsliability")
async def docsliabilityhandler(call: CallbackQuery):
    await call.answer()
    await call.message.edittext(tw(LIABILITYTEXT), replymarkup=backkb("docs"), parse_mode="HTML")

============================================
НАВИГАЦИЯ
============================================
@router.callbackquery(F.data == "navpackage")
async def nav_package(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await showpackagescreen(call.message, state, edit=True)

@router.callbackquery(F.data == "navtiers")
async def nav_tiers(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await showtiersscreen(call.message, state, edit=True)

@router.callbackquery(F.data == "navaddons")
async def nav_addons(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await showaddonsscreen(call.message, state, edit=True)

@router.callbackquery(F.data == "navdetails")
async def nav_details(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await showdetailsprompt(call.message, state, edit=True)

@router.callbackquery(F.data == "navpromo")
async def nav_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await showpromoquestion(call.message, state, edit=True)

@router.callbackquery(F.data == "navbackfromaddons")
async def navbackfrom_addons(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    if data.get('package') == 'bot_server':
        await showtiersscreen(call.message, state, edit=True)
    else:
        await showpackagescreen(call.message, state, edit=True)

@router.callbackquery(F.data == "navbackfromdetails")
async def navbackfrom_details(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await showaddonsscreen(call.message, state, edit=True)

@router.callbackquery(F.data == "startbacktomain")
async def startbackto_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    kb = adminmenu() if call.fromuser.id == ADMINID else mainmenu()
    await call.message.edittext(tw("🏠 Главное меню:"), replymarkup=kb, parse_mode="HTML")

============================================
ПРОЦЕСС ЗАКАЗА
============================================
@router.callbackquery(F.data == "orderstart")
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await showpackagescreen(call.message, state, edit=True)

@router.callbackquery(F.data == "pkgbotonly", OrderState.choosingpackage)
async def pkgbotonly(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(
        package="botonly", packagelabel="🤖 Только бот",
        servertier=None, servertier_label=None,
        baseprice=PRICEBOTONLY, servicename="Разработка бота",
        addons=[], addonsprice=0.0, addonslabel=None
    )
    await showaddonsscreen(call.message, state, edit=True)

@router.callbackquery(F.data == "pkgbotserver", OrderState.choosingpackage)
async def pkgbotserver(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(
        package="botserver", packagelabel="🤖+ Бот + Сервер",
        baseprice=PRICEBOTONLY, servicename="Разработка бота",
        addons=[], addonsprice=0.0, addonslabel=None
    )
    await showtiersscreen(call.message, state, edit=True)

@router.callbackquery(F.data.in(["srvbasic", "srvstop"]), OrderState.choosingservertier)
async def processservertier(call: CallbackQuery, state: FSMContext):
    if call.data == "srv_stop":
        await call.answer("🚫 Премиум сейчас в stop list!", show_alert=True)
        return
    await call.answer()
    data = await state.get_data()
    baseprice = data.get('baseprice', PRICEBOTONLY)
    await state.update_data(
        package="botserver", packagelabel="🤖+ Бот + Сервер",
        server_tier="basic",
        servertierlabel=f"⚡ Базовый ({PRICESERVERBASIC:.0f}₽/мес)",
        baseprice=baseprice + PRICESERVERBASIC,
        service_name="Разработка бота + Хостинг (Базовый)"
    )
    await showaddonsscreen(call.message, state, edit=True)

@router.callbackquery(F.data.startswith("add"), OrderState.choosing_addons)
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
    await call.message.editreplymarkup(replymarkup=addonskb(selected))

@router.callbackquery(F.data == "addonsdone", OrderState.choosing_addons)
async def addons_done(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    selected = data.get("addons", [])
    addons_price = sum(ADDONS[k]["price"] for k in selected if k in ADDONS)
    addons_label = ", ".join(f"{ADDONS[k]['label']} (+{ADDONS[k]['price']:.0f}₽)" for k in selected if k in ADDONS) or None
    await state.updatedata(addonsprice=addonsprice, addonslabel=addons_label)
    await showdetailsprompt(call.message, state, edit=True)

@router.message(OrderState.waitingfordetails)
async def process_details(message: Message, state: FSMContext):
    await state.update_data(details=message.text)
    await showpromoquestion(message, state, edit=False)

@router.callbackquery(F.data == "enterpromo", OrderState.waitingforpromo)
async def enter_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(tw("✏️ Введите ваш промокод:"), replymarkup=backkb("nav_promo"))

@router.callbackquery(F.data == "skippromo", OrderState.waitingforpromo)
async def skip_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await processpromologic(call.message, state, promocode=None, userid=call.from_user.id)

@router.message(OrderState.waitingforpromo)
async def processpromomsg(message: Message, state: FSMContext):
    await processpromologic(message, state, promocode=message.text.strip(), userid=message.from_user.id)

async def processpromologic(target, state: FSMContext, promocode: str = None, userid: int = None):
    """Предпросмотр заказа. Промокод ТОЛЬКО проверяется — списание при подтверждении."""
    try:
        data = await state.get_data()
        totalbase = data.get('baseprice', 0) + data.get('addons_price', 0)

        promo_discount = 0
        normalized_code = None
        if promo_code:
            normalizedcode = promocode.strip().upper()
            promo = await getpromo(normalizedcode)
            if not promo or promo[1] Предварительный итог:\n"
                f"📦 План: {html.escape(data.get('package_label', '🤖 Только бот'))}\n"
                f"{tier_line}"
                f"{addons_line}"
                f"🛠 Услуга: {html.escape(data.get('service_name', 'Заказ'))}\n"
                f"📝 ТЗ: {html.escape(data.get('details', '(не указано)'))}\n\n"
                f"💰 Итоговая цена: {finalprice}₽{reasonstr}"
            ),
            replymarkup=kb, parsemode="HTML"
        )
        await state.setstate(OrderState.confirmingorder)
    except Exception as e:
        print(f"❌ Ошибка в processpromologic: {type(e).name}: {e}")
        try:
            await target.answer("⚠️ Произошла ошибка. Нажми /start и попробуй ещё раз.")
        except Exception:
            pass

@router.callbackquery(F.data == "confirmorder", OrderState.confirming_order)
async def confirmandcreate_order(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    userid = call.fromuser.id
    totalbase = data.get('baseprice', 0) + data.get('addons_price', 0)
    promocode = data.get('promocode')

    # --- ФИНАЛЬНЫЙ расчёт и ОДНОРАЗОВОЕ списание промокода (транзакция) ---
    promo_discount = 0
    promo_note = ""
    if promo_code:
        promo = await getpromo(promocode)
        if promo and promo[1] > 0:
            if await consumepromo(promocode):
                promo_discount = promo[0]
            else:
                promo_note = "\n\nℹ️ Промокод только что закончился — заказ оформлен без скидки по нему."
        else:
            promo_note = "\n\nℹ️ Промокод недействителен — заказ оформлен без скидки по нему."

    amount, reasonstr = await calculateprice(
        totalbase, userid, promodiscount=promodiscount, promocode=promocode
    )

    servicename = data.get('servicename', 'Заказ')
    details = data.get('details', '')
    packagelabel = data.get('packagelabel', '🤖 Только бот')
    servertierlabel = data.get('servertierlabel')
    addonslabel = data.get('addonslabel')
    usercontact = f"@{call.fromuser.username}" if call.fromuser.username else f"ID: {userid}"

    ordernumber = await generateorder_number()

    # --- Сохранение в Firebase ---
    try:
        firebasedb.collection("orders").document(ordernumber).set({
            "number": order_number,
            "userid": userid,
            "client": user_contact,
            "contact": user_contact,
            "service": service_name,
            "package": data.get('package', 'bot_only'),
            "packagelabel": packagelabel,
            "servertier": data.get('servertier'),
            "servertierlabel": servertierlabel,
            "addons": data.get('addons', []),
            "addonslabel": addonslabel,
            "desc": details,
            "price": amount,
            "status": "new",
            "paymentstatus": "waitingmanual_payment",
            "date": datetime.datetime.now().isoformat(),
            "created_at": datetime.datetime.now().isoformat()
        })
        print(f"✅ Заказ {order_number} сохранён в Firebase")
    except Exception as e:
        print(f"❌ Ошибка Firebase: {e}")

    # --- Пользователь больше не «первый заказ» ---
    try:
        await asyncio.tothread(fbuserset, userid, {"firstorder": 0})
    except Exception as e:
        print(f"⚠️ Не удалось обновить first_order: {e}")

    await state.clear()

    await call.message.answer(
        tw(
            f"🎉 Заказ #{order_number} успешно создан!\n\n"
            f"Я передал ваше ТЗ разработчику. В ближайшее время с вами свяжутся.\n\n"
            f"📊 Отслеживать статус заказа:\n{SITEURL}\n(номер: {ordernumber}){promo_note}"
        ),
        replymarkup=mainmenu(), parse_mode="HTML"
    )

    planline = f"📦 План: {packagelabel}"
    if servertierlabel:
        planline += f"\n🖥 Тариф сервера: {servertier_label}"
    if addons_label:
        planline += f"\n🧩 Доп. услуги: {addonslabel}"

    try:
        await bot.send_message(
            ADMIN_ID,
            tw(
                f"🔥 НОВЫЙ ЗАКАЗ #{order_number}\n\n"
                f"👤 Клиент: {html.escape(usercontact)} (ID: {userid})\n"
                f"{html.escape(plan_line)}\n"
                f"🛠 Услуга: {html.escape(service_name)}\n"
                f"💬 ТЗ: {html.escape(details)}\n"
                f"💵 Сумма: {amount}₽\n\n"
                f"⚠️ Требуется связаться с клиентом!"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"⚠️ Не удалось уведомить админа о заказе {order_number}: {type(e).name}: {e}")

============================================
ПРОФИЛЬ (данные из Firestore)
============================================
@router.callback_query(F.data == "profile")
async def show_profile(call: CallbackQuery, state: FSMContext):
    await call.answer()
    userid = call.fromuser.id
    user = await getuser(userid)
    orders = await asyncio.tothread(fbordersof, user_id)

    username = (user or {}).get("username") or "Не указан"
    bday = (user or {}).get("birthday") or "Не указан"

    text = f"👤 Ваш профиль:\n🆔 ID: {user_id}\n📱 Username: @{html.escape(str(username))}\n🎂 День рождения: {html.escape(str(bday))}\n\n"

    if orders:
        text += f"📦 Ваши заказы ({len(orders)}):\n"
        for o in orders:
            order_num = o.get("number", "—")
            service = o.get("service", "—")
            price = o.get("price", 0)
            statusemoji = getstatus_emoji(o.get("status", "new"))
            created = o.get("created_at") or o.get("date") or ""
            short_date = created.split("T")[0] if created else "Неизвестно"
            text += f"\n🔹 #{html.escape(str(ordernum))} ({shortdate})\n   {html.escape(str(service))} | {price}₽\n   Статус: {status_emoji}"
    else:
        text += "📭 У вас пока нет заказов."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎂 Изменить ДР", callbackdata="setbday")],
        [InlineKeyboardButton(text="🔙 В главное меню", callbackdata="startbacktomain")]
    ])
    await call.message.edittext(tw(text), replymarkup=kb, parse_mode="HTML")

@router.callbackquery(F.data == "setbday")
async def set_bday(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edittext(tw("🎂 Напиши дату в формате ДД.ММ:"), replymarkup=back_kb("profile"))
    await state.setstate(SetBdayState.waitingfor_bday)

@router.message(SetBdayState.waitingforbday)
async def save_bday(message: Message, state: FSMContext):
    await asyncio.tothread(fbuserset, message.from_user.id, {"birthday": message.text.strip()})
    await state.clear()
    await message.answer(tw("✅ День рождения сохранён!"), replymarkup=mainmenu())

============================================
АДМИНКА
============================================
@router.callbackquery(F.data == "adminchats")
async def admin_chats(call: CallbackQuery):
    await call.answer()
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT DISTINCT user_id FROM messages")
        users = await cursor.fetchall()
    if not users:
        return await call.message.edittext(tw("💬 Диалогов пока нет."), replymarkup=backkb("startbacktomain"))
    kb = [[InlineKeyboardButton(text=f"👤 {u[0]}", callbackdata=f"chat{u[0]}")] for u in users]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callbackdata="startbacktomain")])
    await call.message.edittext(tw("💬 Выберите пользователя:"), replymarkup=InlineKeyboardMarkup(inlinekeyboard=kb), parsemode="HTML")

@router.callbackquery(F.data.startswith("chat"))
async def read_chat(call: CallbackQuery):
    await call.answer()
    userid = int(call.data.split("")[1])
    async with aiosqlite.connect("nil_bots.db") as db:
        cursor = await db.execute("SELECT text, isuser FROM messages WHERE userid=? ORDER BY id DESC LIMIT 15", (user_id,))
        msgs = await cursor.fetchall()
    history = "\n".join([f"{'👤 Клиент' if m[1] else '👑 Вы'}: {html.escape(str(m[0]))}" for m in reversed(msgs)])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Написать ответ", callbackdata=f"reply{user_id}")],
        [InlineKeyboardButton(text="🔙 К чатам", callbackdata="adminchats")]
    ])
    await call.message.edittext(tw(f"💬 Чат с {userid}:\n\n{history}"), replymarkup=kb, parsemode="HTML")

@router.callbackquery(F.data.startswith("reply"))
async def startadminreply(call: CallbackQuery, state: FSMContext):
    await call.answer()
    userid = int(call.data.split("")[1])
    await state.updatedata(targetuserid=userid)
    await state.setstate(AdminReplyState.waitingfor_reply)
    await call.message.edittext(tw(f"✏️ Введи ответ для {userid}:\n(или /cancel)"), replymarkup=backkb("admin_chats"))

@router.message(AdminReplyState.waitingforreply)
async def adminsendreply(message: Message, state: FSMContext):
    data = await state.get_data()
    targetuserid = data.get('targetuserid')
    if not targetuserid:
        await state.clear()
        return
    try:
        await bot.sendmessage(targetuserid, tw(f"👑 Ответ от Nil Bots:\n\n{html.escape(message.text)}"), parsemode="HTML")
        async with aiosqlite.connect("nil_bots.db") as db:
            await db.execute("INSERT INTO messages (userid, text, isuser) VALUES (?, ?, 0)", (targetuserid, message.text))
            await db.commit()
        await message.answer(tw(f"✅ Отправлено пользователю {targetuserid}."), replymarkup=adminmenu())
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    await state.clear()

@router.message(Command("cancel"))
async def cancel_state(message: Message, state: FSMContext):
    await state.clear()
    kb = adminmenu() if message.fromuser.id == ADMINID else mainmenu()
    await message.answer(tw("❌ Действие отменено."), reply_markup=kb)

============================================
ПРОМОКОДЫ (админка, Firestore)
============================================
@router.callbackquery(F.data == "adminpromos")
async def admin_promos(call: CallbackQuery):
    await call.answer()
    promos = await asyncio.tothread(fbpromolist)

    text = "🎟 Управление промокодами:\n\n"
    if promos:
        for code, discount, uses_left in promos:
            text += f"• {html.escape(str(code))} — {discount}% (осталось: {uses_left})\n"
    else:
        text += "Промокодов пока нет."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callbackdata="createpromo")],
        [InlineKeyboardButton(text="🔙 Назад", callbackdata="startbacktomain")]
    ])
    await call.message.edittext(tw(text), replymarkup=kb, parse_mode="HTML")

@router.callbackquery(F.data == "createpromo")
async def create_promo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edittext(tw("✏️ Введи название промокода (например, NIL10):"), replymarkup=backkb("adminpromos"))
    await state.setstate(AddPromoState.waitingfor_code)

@router.message(AddPromoState.waitingforcode)
async def promocodeinput(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if not code or " " in code:
        await message.answer("❌ Код не должен быть пустым и содержать пробелы.")
        return
    existing = await get_promo(code)
    await state.update_data(code=code)
    note = "\n⚠️ Такой код уже существует — будет заменён." if existing else ""
    await message.answer(tw(f"💰 Введи размер скидки в % (1-100):{note}"))
    await state.setstate(AddPromoState.waitingfor_discount)

@router.message(AddPromoState.waitingfordiscount)
async def promodiscountinput(message: Message, state: FSMContext):
    try:
        discount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи целое число.")
        return
    if not (1 {html.escape(data['code'])} создан!\nСкидка: {data['discount']}%\nАктиваций: {uses}"),
        replymarkup=adminmenu(), parse_mode="HTML"
    )

============================================
ПОДДЕРЖКА (последний хендлер!)
============================================
@router.message(F.text)
async def support_msg(message: Message, state: FSMContext):
    if message.fromuser.id == ADMINID:
        return
    currentstate = await state.getstate()
    if current_state is not None:
        return
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("INSERT INTO messages (userid, text, isuser) VALUES (?, ?, 1)",
                         (message.from_user.id, message.text))
        await db.commit()
    try:
        await bot.sendmessage(ADMINID, f"💬 Сообщение от {html.escape(message.fromuser.fullname)} (ID: {message.fromuser.id}):\n\n{html.escape(message.text)}", parsemode="HTML")
    except Exception:
        pass
    await message.answer(tw("✅ Отправлено! Администратор ответит вам в ближайшее время."))

============================================
ЗАПУСК
============================================
async def main():
    await init_db()
    print("🚀 Бот nil.bots запущен!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"💰 Цены: Бот={PRICEBOTONLY}₽, Basic={PRICESERVERBASIC}₽, Премиум=STOP LIST")
    startsettingslistener()
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())

⚠️ Как копировать, чтобы файл НЕ побился снова:

Твой прошлый файл сломался из-за копирования через место, где съелись _ и  (markdown/HTML-рендер). Поэтому:

Копируй кнопкой копирования блока кода (или Ctrl+A внутри серого блока → Ctrl+C)
Вставь в VS Code / Блокнот, НЕ в Telegram-черновик и НЕ в онлайн-редакторы с «умным» форматированием
Самопроверка перед пушем (Ctrl+F в редакторе):
   - BOTTOKEN → ничего не найдено ✅
   - BOT_TOKEN → найдено ✅
   - def settingslistener(snapshot, changes, read_time): → найдено ✅
   - Первая строка файла = import asyncio ✅
git add main.py && git commit -m "clean restore" && git push

✅ После деплоя жду от тебя логи — норма:

🚀 Бот nil.bots запущен!
👑 Admin ID: 5244755472
💰 Цены: Бот=115.0₽, Basic=300.0₽, Премиум=STOP LIST
👂 Listener тех. работ запущен
🚧 Режим тех. работ: выключен
