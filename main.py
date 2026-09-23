import asyncio
import datetime
import random
import os
import json
import html
import traceback
import uuid
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ErrorEvent
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import aiohttp
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
        "label": " Отдельный бот тех. поддержки",
        "price": float(os.environ.get("PRICE_ADDON_SUPPORT", "99")),
    },
    "priority": {
        "label": "⚡ Приоритет к заказу",
        "price": float(os.environ.get("PRICE_ADDON_PRIORITY", "50")),
    },
}

SITE_URL = "https://nil-bots-site-with-bot.vercel.app/"
SUPPORT_URL = "https://t.me/nilbots_support_bot"

# RollyPay
ROLLY_API_KEY = os.environ.get("ROLLY_API_KEY", "")
ROLLY_API_URL = os.environ.get("ROLLY_API_URL", "https://rollypay.io/api/v1")
PAYMENT_CHECK_INTERVAL = 30  # секунд между проверками

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"

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
# СОГЛАШЕНИЕ ПРИ ПЕРВОМ ЗАПУСКЕ
# ============================================
AGREEMENT_TEXT = (
    "✨ <b>Добро пожаловать в Nil Bots!</b> ✨\n"
    f"{DIVIDER}\n\n"
    "Прежде чем продолжить, пожалуйста, ознакомься с документами ниже.\n\n"
    "Нажимая «✅ Я согласен с условиями», ты подтверждаешь, что прочитал(а) "
    "и принимаешь условия <b>Публичной оферты</b> и <b>Политики конфиденциальности</b>.\n\n"
    "⚠️ Без согласия использование бота недоступно."
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
# FIRESTORE-ХЕЛПЕРЫ
# ============================================
def _fb_promo_get(code: str):
    snap = firebase_db.collection("promos").document(code).get()
    if not snap.exists:
        return None
    d = snap.to_dict() or {}
    return (int(d.get("discount", 0)), int(d.get("uses_left", 0)))

async def get_promo(code: str):
    return await asyncio.to_thread(_fb_promo_get, code.strip().upper())

def _fb_promo_consume(code: str) -> bool:
    ref = firebase_db.collection("promos").document(code)
    snap = ref.get()
    if not snap.exists:
        return False
    left = int((snap.to_dict() or {}).get("uses_left", 0))
    if left <= 0:
        return False
    ref.update({"uses_left": firestore.Increment(-1)})
    return True

async def consume_promo(code: str) -> bool:
    return await asyncio.to_thread(_fb_promo_consume, code.strip().upper())

def _fb_promo_set(code: str, discount: int, uses: int):
    firebase_db.collection("promos").document(code).set({
        "code": code,
        "discount": int(discount),
        "uses_left": int(uses),
        "created_at": datetime.datetime.now().isoformat(),
    })

def _fb_promo_list():
    out = []
    for d in firebase_db.collection("promos").stream():
        v = d.to_dict() or {}
        out.append((v.get("code", d.id), int(v.get("discount", 0)), int(v.get("uses_left", 0))))
    out.sort(key=lambda x: x[0])
    return out

def _fb_user_get(user_id: int):
    snap = firebase_db.collection("users").document(str(user_id)).get()
    return snap.to_dict() if snap.exists else None

async def get_user(user_id: int):
    return await asyncio.to_thread(_fb_user_get, user_id)

def _fb_user_ensure(user_id: int, username):
    ref = firebase_db.collection("users").document(str(user_id))
    snap = ref.get()
    if not snap.exists:
        data = {
            "user_id": user_id,
            "username": username,
            "birthday": None,
            "first_order": 1,
            "agreed_terms": False,
            "agreed_terms_at": None,
            "created_at": datetime.datetime.now().isoformat(),
        }
        ref.set(data)
        return data
    return snap.to_dict()

async def ensure_user(user_id: int, username):
    return await asyncio.to_thread(_fb_user_ensure, user_id, username)

def _fb_user_set(user_id: int, fields: dict):
    firebase_db.collection("users").document(str(user_id)).set(fields, merge=True)

def _fb_user_ids():
    return [(d.to_dict() or {}).get("user_id") or int(d.id)
            for d in firebase_db.collection("users").stream()]

def _fb_order_exists(number: str) -> bool:
    return firebase_db.collection("orders").document(number).get().exists

def _fb_orders_of(user_id: int):
    docs = firebase_db.collection("orders").where("user_id", "==", user_id).stream()
    out = [d.to_dict() for d in docs]
    out.sort(key=lambda o: o.get("created_at") or "", reverse=True)
    return out

def _fb_get_order_by_number(number: str):
    """Возвращает (doc_id, data) заказа по номеру или (None, None)."""
    try:
        docs = firebase_db.collection("orders").where("number", "==", number).limit(1).stream()
        for d in docs:
            return d.id, d.to_dict()
    except Exception as e:
        print(f"⚠️ Ошибка поиска заказа {number}: {e}")
    return None, None

def _mask_contact(contact: str) -> str:
    c = (contact or "").strip()
    if c.startswith("@"):
        c = c[1:]
    if len(c) <= 3:
        return "*" * max(len(c), 1)
    return c[:2] + "*" * max(len(c) - 4, 1) + c[-2:]

# ============================================
# ROLLYPAY ИНТЕГРАЦИЯ
# ============================================
async def create_rollypay_payment(order_number: str, amount: float, description: str):
    """Создаёт платёж в RollyPay. Возвращает (pay_url, payment_id) или (None, None)."""
    if not ROLLY_API_KEY:
        print(" ROLLY_API_KEY не задан — оплата недоступна")
        return None, None

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": ROLLY_API_KEY,
        "X-Nonce": str(uuid.uuid4())
    }

    data = {
        "amount": f"{amount:.2f}",
        "payment_currency": "RUB",
        "order_id": order_number,
        "description": description
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{ROLLY_API_URL}/payments", headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    pay_url = result.get("pay_url")
                    payment_id = result.get("payment_id")
                    print(f"✅ Платёж {payment_id} создан для заказа {order_number}")
                    return pay_url, payment_id
                else:
                    error = await resp.text()
                    print(f"❌ Ошибка создания платежа: {resp.status} - {error}")
                    return None, None
    except Exception as e:
        print(f"❌ Ошибка RollyPay: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return None, None

async def check_rollypay_payment_status(payment_id: str):
    """Проверяет статус платежа. Возвращает статус или None."""
    if not ROLLY_API_KEY or not payment_id:
        return None

    headers = {
        "X-API-Key": ROLLY_API_KEY,
        "X-Nonce": str(uuid.uuid4())
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ROLLY_API_URL}/payments/{payment_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("status")
                return None
    except Exception as e:
        print(f"⚠️ Ошибка проверки статуса {payment_id}: {e}")
        return None

# Хранилище активных проверок оплат: {order_number: {"payment_id": ..., "user_id": ...}}
payment_tasks = {}

async def payment_polling_task():
    """Фоновая задача: проверяет статусы оплат каждые PAYMENT_CHECK_INTERVAL секунд."""
    print(f"🔄 Запущена фоновая проверка оплат (интервал {PAYMENT_CHECK_INTERVAL}с)")
    while True:
        try:
            await asyncio.sleep(PAYMENT_CHECK_INTERVAL)
            if not payment_tasks:
                continue

            for order_number, task_data in list(payment_tasks.items()):
                payment_id = task_data.get("payment_id")
                if not payment_id:
                    continue

                status = await check_rollypay_payment_status(payment_id)

                if status == "paid":
                    print(f"💰 Заказ {order_number} — оплата получена!")
                    await confirm_order_payment(order_number, task_data)
                    payment_tasks.pop(order_number, None)
                elif status in ["canceled", "expired"]:
                    print(f"️ Заказ {order_number} — оплата {status}")
                    await cancel_order_payment(order_number, task_data)
                    payment_tasks.pop(order_number, None)
        except Exception as e:
            print(f"❌ Ошибка в payment_polling_task: {e}")
            print(traceback.format_exc())

async def confirm_order_payment(order_number: str, task_data: dict):
    """Подтверждает заказ после успешной оплаты."""
    try:
        doc_id, order_data = await asyncio.to_thread(_fb_get_order_by_number, order_number)
        if not order_data:
            print(f"⚠️ Заказ {order_number} не найден при подтверждении")
            return

        user_id = order_data.get("user_id")

        # Обновляем заказ
        firebase_db.collection("orders").document(doc_id).update({
            "status": "new",
            "payment_status": "paid",
            "paid_at": datetime.datetime.now().isoformat()
        })

        # Обновляем публичную версию
        try:
            firebase_db.collection("orders_public").document(order_number).update({
                "status": "new"
            })
        except Exception as e:
            print(f"⚠️ orders_public ошибка: {e}")

        # Уведомляем клиента
        if user_id:
            try:
                await bot.send_message(
                    user_id,
                    f"✅ <b>Заказ #{order_number} оплачен!</b>\n\n"
                    f"💵 Сумма: {order_data.get('price', 0)}₽\n"
                    f" Статус: <b>Новый</b> (принят в работу)\n\n"
                    f"Я передал ТЗ разработчику. В ближайшее время с вами свяжутся!\n\n"
                    f"📊 Отслеживать статус: {SITE_URL}",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"⚠️ Не удалось уведомить клиента {user_id}: {e}")

        # Уведомляем админа
        try:
            await bot.send_message(
                ADMIN_ID,
                f"💰 <b>Заказ #{order_number} ОПЛАЧЕН!</b>\n\n"
                f" Клиент: {order_data.get('client', '—')}\n"
                f" Сумма: {order_data.get('price', 0)}₽\n"
                f" Услуга: {order_data.get('service', '—')}\n\n"
                f"✅ Можно начинать работу!",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"⚠️ Не удалось уведомить админа: {e}")

        print(f"✅ Заказ {order_number} подтверждён (оплата получена)")

    except Exception as e:
        print(f"❌ Ошибка подтверждения заказа {order_number}: {e}")
        print(traceback.format_exc())

async def cancel_order_payment(order_number: str, task_data: dict):
    """Отменяет заказ если оплата не прошла."""
    try:
        doc_id, order_data = await asyncio.to_thread(_fb_get_order_by_number, order_number)
        if not order_data:
            return

        user_id = order_data.get("user_id")

        # Помечаем заказ как неоплаченный
        if doc_id:
            firebase_db.collection("orders").document(doc_id).update({
                "status": "cancelled",
                "payment_status": "failed"
            })

        if user_id:
            try:
                await bot.send_message(
                    user_id,
                    f"⚠️ <b>Заказ #{order_number}</b>\n\n"
                    f"Оплата не была подтверждена (платёж отменён или истёк).\n\n"
                    f"Если у вас возникли проблемы — напишите в поддержку: @nilbots_support_bot",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        print(f"⚠️ Заказ {order_number} отменён (оплата не получена)")

    except Exception as e:
        print(f"❌ Ошибка отмены заказа {order_number}: {e}")

async def restore_pending_payments():
    """При старте бота восстанавливает polling для неоплаченных заказов."""
    try:
        docs = firebase_db.collection("orders").where("status", "==", "waiting_payment").stream()
        count = 0
        for d in docs:
            data = d.to_dict()
            payment_id = data.get("payment_id")
            order_number = data.get("number")
            user_id = data.get("user_id")
            if payment_id and order_number:
                payment_tasks[order_number] = {
                    "payment_id": payment_id,
                    "user_id": user_id
                }
                count += 1
        if count > 0:
            print(f"🔄 Восстановлено {count} ожидающих оплат")
    except Exception as e:
        print(f"⚠️ Ошибка восстановления оплат: {e}")

# ============================================
# ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК
# ============================================
@router.errors()
async def on_handler_error(event: ErrorEvent):
    print(f" ХЕНДЛЕР УПАЛ: {type(event.exception).__name__}: {event.exception}")
    print(traceback.format_exc())
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

# ============================================
# РЕЖИМ ТЕХ. РАБОТ
# ============================================
MAINTENANCE = {"on": False}
MAIN_LOOP = None

def tw(text: str) -> str:
    if MAINTENANCE["on"]:
        return f"{text}\n\n🚧 Технические работы!"
    return text

async def broadcast_maintenance():
    user_ids = await asyncio.to_thread(_fb_user_ids)
    sent = 0
    for uid in user_ids:
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
        await asyncio.sleep(0.05)
    print(f" Оповещение о тех. работах: {sent}/{len(user_ids)}")

def _settings_listener(snapshot, changes, read_time):
    try:
        data = snapshot.to_dict() if snapshot.exists else {}
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
    print(" Listener тех. работ запущен")

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

class BroadcastState(StatesGroup):
    waiting_text = State()
    confirming = State()

# ============================================
# БАЗА ДАННЫХ (SQLite — только чаты админа)
# ============================================
async def init_db():
    async with aiosqlite.connect("nil_bots.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT, is_user INTEGER)""")
        await db.commit()

async def generate_order_number():
    for _ in range(20):
        number = f"NB-{random.randint(1000, 9999)}"
        if not await asyncio.to_thread(_fb_order_exists, number):
            return number
    return f"NB-{int(datetime.datetime.now().timestamp()) % 1000000}"

# ============================================
# РАСЧЁТ ЦЕНЫ (потолок 100%)
# ============================================
async def calculate_price(base_price: float, user_id: int, promo_discount: int = 0, promo_code: str = None):
    user = await get_user(user_id)

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

    discount = min(discount, 100)
    final_price = round(base_price * (1 - discount / 100), 2)
    if final_price < 0:
        final_price = 0.0
    reason_str = f"\n🎁 Скидка {discount}% ({', '.join(reasons)})" if discount > 0 else ""

    return final_price, reason_str

def get_status_emoji(status: str) -> str:
    return {
        "new": "🟡 Создан",
        "waiting_payment": "⏳ Ожидает оплаты",
        "working": " В работе",
        "done": " Готов",
        "cancelled": " Отменен",
        "closed": "⚫ Закрыт",
    }.get(status, "❓ Неизвестно")

# ============================================
# КЛАВИАТУРЫ
# ============================================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Заказать разработку", callback_data="order_start")],
        [InlineKeyboardButton(text="👤 Мой профиль и заказы", callback_data="profile")],
        [InlineKeyboardButton(text=" Документация", callback_data="docs")],
        [InlineKeyboardButton(text="🌐 Наш сайт", url=SITE_URL)],
        [InlineKeyboardButton(text="💬 Техподдержка", url=SUPPORT_URL)]
    ])

def docs_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Политика конфиденциальности", callback_data="doc_privacy")],
        [InlineKeyboardButton(text="🔴 Публичная оферта", callback_data="doc_offer")],
        [InlineKeyboardButton(text="⚠️ Ограничение ответственности", callback_data="docs_liability")],
        [InlineKeyboardButton(text=" В главное меню", callback_data="start_back_to_main")]
    ])

def agreement_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Публичная оферта", callback_data="agree_view_offer")],
        [InlineKeyboardButton(text="🔴 Политика конфиденциальности", callback_data="agree_view_privacy")],
        [InlineKeyboardButton(text="✅ Я согласен с условиями", callback_data="agree_accept")]
    ])

def agreement_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к соглашению", callback_data="agree_back")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Чаты с клиентами", callback_data="admin_chats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
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
        mark = "✅" if key in selected else "▫️"
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

async def send_document_text(message: Message, text: str, keyboard_fn=docs_kb):
    chunks = split_telegram_text(text)
    if chunks:
        chunks[-1] = tw(chunks[-1])
    for i, chunk in enumerate(chunks):
        markup = keyboard_fn() if i == len(chunks) - 1 else None
        await message.answer(chunk, parse_mode="HTML", reply_markup=markup)

# ============================================
# ЭКРАНЫ
# ============================================
async def show_main_menu(message, edit=False, maintenance_notice=False):
    notice = ""
    if maintenance_notice and MAINTENANCE["on"]:
        notice = ("🚧 <b>Сейчас идут технические работы!</b>\n"
                  "Некоторые функции могут работать нестабильно.\n\n")
    text = (
        notice +
        "✨ <b>Nil Bots — создаём Telegram-ботов под ключ</b> ✨\n"
        f"{DIVIDER}\n\n"
        "🤖 Помогу тебе заказать идеального бота под любые задачи — "
        "от простого помощника до бота с хостингом и доп. функциями.\n\n"
        "👇 Выбери, что тебя интересует:"
    )
    if edit:
        await message.edit_text(tw(text), reply_markup=main_menu(), parse_mode="HTML")
    else:
        await message.answer(tw(text), reply_markup=main_menu(), parse_mode="HTML")

async def show_package_screen(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Только бот", callback_data="pkg_bot_only")],
        [InlineKeyboardButton(text="+ Бот + Сервер", callback_data="pkg_bot_server")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="start_back_to_main")]
    ])
    text = (
        "🛠 <b>Шаг 1 из 4 — Пакет услуг</b>\n"
        f"{DIVIDER}\n\n"
        "Что именно вы хотите заказать?"
    )
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
        "🖥 <b>Шаг 2 из 4 — Тариф хостинга</b>\n"
        f"{DIVIDER}\n\n"
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
        "🧩 <b>Шаг 3 из 4 — Дополнительные услуги</b>\n"
        f"{DIVIDER}\n\n"
        "Нажимай, чтобы добавить или убрать услугу (по желанию).\n"
        "Когда всё выберешь — жми «✅ Продолжить»."
    )
    if edit:
        await message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.choosing_addons)

async def show_details_prompt(message, state, edit=False):
    kb = back_kb("nav_back_from_details")
    text = (
        "📝 <b>Шаг 4 из 4 — Техническое задание</b>\n"
        f"{DIVIDER}\n\n"
        "Отлично! Опиши подробно, какого бота ты хочешь:"
    )
    if edit:
        await message.edit_text(tw(text), reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(tw(text), reply_markup=kb, parse_mode="HTML")
    await state.set_state(OrderState.waiting_for_details)

async def show_promo_question(message, state, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Есть промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="nav_details")]
    ])
    text = f"💬 <b>Есть ли у вас промокод?</b>\n{DIVIDER}"
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
    user = await ensure_user(message.from_user.id, message.from_user.username)

    if message.from_user.id == ADMIN_ID:
        await message.answer(
            tw(f"👑 <b>Админ-панель</b>\n{DIVIDER}"),
            reply_markup=admin_menu(), parse_mode="HTML"
        )
        return

    if not user.get("agreed_terms"):
        await message.answer(tw(AGREEMENT_TEXT), reply_markup=agreement_kb(), parse_mode="HTML")
        return

    await show_main_menu(message, maintenance_notice=True)

# ============================================
# СОГЛАШЕНИЕ (ПУБЛ. ОФЕРТА / ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ)
# ============================================
@router.callback_query(F.data == "agree_view_offer")
async def agree_view_offer(call: CallbackQuery):
    await call.answer()
    await send_document_text(call.message, PUBLIC_OFFER, keyboard_fn=agreement_back_kb)

@router.callback_query(F.data == "agree_view_privacy")
async def agree_view_privacy(call: CallbackQuery):
    await call.answer()
    await send_document_text(call.message, PRIVACY_POLICY, keyboard_fn=agreement_back_kb)

@router.callback_query(F.data == "agree_back")
async def agree_back(call: CallbackQuery):
    await call.answer()
    await call.message.answer(tw(AGREEMENT_TEXT), reply_markup=agreement_kb(), parse_mode="HTML")

@router.callback_query(F.data == "agree_accept")
async def agree_accept(call: CallbackQuery):
    await call.answer("✅ Спасибо! Условия приняты.")
    await asyncio.to_thread(_fb_user_set, call.from_user.id, {
        "agreed_terms": True,
        "agreed_terms_at": datetime.datetime.now().isoformat()
    })
    try:
        await call.message.edit_text(
            tw(f"✅ <b>Спасибо! Вы приняли условия соглашения.</b>\n{DIVIDER}"),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await show_main_menu(call.message, maintenance_notice=True)

# ============================================
# ДОКУМЕНТАЦИЯ
# ============================================
@router.callback_query(F.data == "docs")
async def docs_handler(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        tw(f"📄 <b>Документация</b>\n{DIVIDER}\n\nВыбери документ:"),
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
    if call.from_user.id == ADMIN_ID:
        await call.message.edit_text(tw(f"👑 <b>Админ-панель</b>\n{DIVIDER}"), reply_markup=admin_menu(), parse_mode="HTML")
    else:
        await show_main_menu(call.message, edit=True)

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
        package="bot_only", package_label=" Только бот",
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
    try:
        data = await state.get_data()
        total_base = data.get('base_price', 0) + data.get('addons_price', 0)

        promo_discount = 0
        normalized_code = None
        if promo_code:
            normalized_code = promo_code.strip().upper()
            promo = await get_promo(normalized_code)
            if not promo or promo[1] <= 0:
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
            [InlineKeyboardButton(text=" Назад", callback_data="nav_promo")]
        ])

        addons_line = f"🧩 Доп. услуги: {html.escape(data.get('addons_label') or '')}\n" if data.get('addons_label') else ""
        tier_line = f"🖥 Тариф: {html.escape(data.get('server_tier_label') or '')}\n" if data.get('server_tier_label') else ""

        await target.answer(
            tw(
                f"📋 <b>Предварительный итог заказа</b>\n"
                f"{DIVIDER}\n"
                f"📦 План: {html.escape(data.get('package_label', '🤖 Только бот'))}\n"
                f"{tier_line}"
                f"{addons_line}"
                f"🛠 Услуга: {html.escape(data.get('service_name', 'Заказ'))}\n"
                f" ТЗ: {html.escape(data.get('details', '(не указано)'))}\n"
                f"{DIVIDER}\n"
                f"💰 <b>Итоговая цена: {final_price}₽</b>{reason_str}"
            ),
            reply_markup=kb, parse_mode="HTML"
        )
        await state.set_state(OrderState.confirming_order)
    except Exception as e:
        print(f"❌ Ошибка в process_promo_logic: {type(e).__name__}: {e}")
        print(traceback.format_exc())
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

    # --- Промокод ---
    promo_discount = 0
    promo_note = ""
    if promo_code:
        try:
            promo = await get_promo(promo_code)
            if promo and promo[1] > 0:
                if await consume_promo(promo_code):
                    promo_discount = promo[0]
                else:
                    promo_note = "\n\nℹ️ Промокод только что закончился — заказ оформлен без скидки по нему."
            else:
                promo_note = "\n\nℹ️ Промокод недействителен — заказ оформлен без скидки по нему."
        except Exception as e:
            print(f"⚠️ Ошибка промокода {promo_code}: {type(e).__name__}: {e}")
            promo_note = "\n\n⚠️ Промокод не применён из-за технической ошибки."

    amount, reason_str = await calculate_price(
        total_base, user_id, promo_discount=promo_discount, promo_code=promo_code
    )

    service_name = data.get('service_name', 'Заказ')
    details = data.get('details', '')
    package_label = data.get('package_label', ' Только бот')
    server_tier_label = data.get('server_tier_label')
    addons_label = data.get('addons_label')
    user_contact = f"@{call.from_user.username}" if call.from_user.username else f"ID: {user_id}"

    order_number = await generate_order_number()
    now_iso = datetime.datetime.now().isoformat()

    # --- 1. Создаём заказ со статусом waiting_payment ---
    try:
        firebase_db.collection("orders").document(order_number).set({
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
            "status": "waiting_payment",
            "payment_status": "waiting_payment",
            "payment_id": None,
            "date": now_iso,
            "created_at": now_iso
        })
        print(f"✅ Заказ {order_number} создан (ожидает оплаты)")
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ошибка создания заказа: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        await state.clear()
        await call.message.answer(
            "❌ Не удалось сохранить заказ в базе. Пожалуйста, нажми /start и попробуй ещё раз."
        )
        return

    # --- 2. Создаём платёж в RollyPay ---
    pay_url, payment_id = await create_rollypay_payment(
        order_number=order_number,
        amount=amount,
        description=f"Заказ #{order_number} — {service_name}"
    )

    # Сохраняем payment_id в заказе
    if payment_id:
        try:
            firebase_db.collection("orders").document(order_number).update({
                "payment_id": payment_id
            })
        except Exception as e:
            print(f"⚠️ Не удалось сохранить payment_id: {e}")

    # --- 3. Публичная карточка (пока со статусом waiting) ---
    try:
        firebase_db.collection("orders_public").document(order_number).set({
            "number": order_number,
            "status": "waiting_payment",
            "price": amount,
            "package_label": package_label,
            "server_tier_label": server_tier_label,
            "client_masked": _mask_contact(user_contact),
            "created_at": now_iso,
            "date": now_iso,
        })
    except Exception as e:
        print(f"⚠️ orders_public ошибка: {e}")

    # --- 4. first_order = 0 ---
    try:
        await asyncio.to_thread(_fb_user_set, user_id, {"first_order": 0})
    except Exception as e:
        print(f"⚠️ Не удалось обновить first_order: {e}")

    await state.clear()

    # --- 5. Если оплата не настроена — показываем сообщение об этом ---
    if not pay_url:
        await call.message.answer(
            tw(
                f"📋 <b>Заказ #{order_number} создан!</b>\n"
                f"{DIVIDER}\n\n"
                f"⚠️ Оплата сейчас недоступна — напиши в поддержку для оформления: @nilbots_support_bot\n\n"
                f"💵 Сумма: <b>{amount}₽</b>{reason_str}{promo_note}"
            ),
            reply_markup=main_menu(), parse_mode="HTML"
        )
        return

    # --- 6. Добавляем в polling ---
    payment_tasks[order_number] = {
        "payment_id": payment_id,
        "user_id": user_id
    }

    # --- 7. Отправляем клиенту ссылку на оплату ---
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить заказ", url=pay_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_pay_{order_number}")],
        [InlineKeyboardButton(text="📋 Мой профиль", callback_data="profile")]
    ])

    await call.message.answer(
        tw(
            f"🎉 <b>Заказ #{order_number} создан!</b>\n"
            f"{DIVIDER}\n\n"
            f"💵 Сумма: <b>{amount}₽</b>{reason_str}\n\n"
            f"⏳ <b>Важно:</b> после оплаты бот автоматически проверит платёж.\n"
            f"⚠️ <b>Проверка занимает до 30 секунд</b> — пожалуйста, подожди.\n\n"
            f"Нажми «💳 Оплатить заказ» и заверши оплату. Как только платёж подтвердится — "
            f"я пришлю уведомление и передам ТЗ разработчику.{promo_note}"
        ),
        reply_markup=kb, parse_mode="HTML"
    )

    # --- 8. Уведомление админу о новом заказе (ещё не оплачен) ---
    plan_line = f" План: {package_label}"
    if server_tier_label:
        plan_line += f"\n🖥 Тариф сервера: {server_tier_label}"
    if addons_label:
        plan_line += f"\n🧩 Доп. услуги: {addons_label}"

    try:
        await bot.send_message(
            ADMIN_ID,
            tw(
                f"🆕 <b>НОВЫЙ ЗАКАЗ #{order_number} (ожидает оплаты)</b>\n"
                f"{DIVIDER}\n"
                f"👤 Клиент: {html.escape(user_contact)} (ID: {user_id})\n"
                f"{html.escape(plan_line)}\n"
                f"🛠 Услуга: {html.escape(service_name)}\n"
                f"💬 ТЗ: {html.escape(details)}\n"
                f"💵 Сумма: {amount}₽\n\n"
                f" Ждём оплату..."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"️ Не удалось уведомить админа: {type(e).__name__}: {e}")

# --- Ручная проверка оплаты ---
@router.callback_query(F.data.startswith("check_pay_"))
async def manual_check_payment(call: CallbackQuery):
    order_number = call.data.replace("check_pay_", "")
    await call.answer("⏳ Проверяю оплату...")

    task_data = payment_tasks.get(order_number)
    if not task_data:
        # Проверяем в Firebase напрямую
        _, order_data = await asyncio.to_thread(_fb_get_order_by_number, order_number)
        if order_data and order_data.get("payment_status") == "paid":
            await call.message.answer("✅ Этот заказ уже оплачен!")
            return
        await call.message.answer("⚠️ Платёж не найден. Если ты уже оплатил — напиши в поддержку.")
        return

    status = await check_rollypay_payment_status(task_data.get("payment_id"))
    if status == "paid":
        await confirm_order_payment(order_number, task_data)
        payment_tasks.pop(order_number, None)
        await call.message.answer("✅ Оплата подтверждена! Заказ принят в работу.")
    elif status in ["canceled", "expired"]:
        await cancel_order_payment(order_number, task_data)
        payment_tasks.pop(order_number, None)
        await call.message.answer("⚠️ Платёж отменён или истёк. Создай заказ заново.")
    else:
        await call.message.answer(
            f" Оплата ещё не подтверждена. Статус: <b>{status or 'неизвестно'}</b>.\n\n"
            f"Подожди ещё немного или нажми «🔄 Проверить оплату» через 30 секунд.",
            parse_mode="HTML"
        )

# ============================================
# ПРОФИЛЬ
# ============================================
@router.callback_query(F.data == "profile")
async def show_profile(call: CallbackQuery, state: FSMContext):
    await call.answer()
    user_id = call.from_user.id
    user = await get_user(user_id)
    orders = await asyncio.to_thread(_fb_orders_of, user_id)

    username = (user or {}).get("username") or "Не указан"
    bday = (user or {}).get("birthday") or "Не указан"

    text = (
        f"👤 <b>Ваш профиль</b>\n{DIVIDER}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📱 Username: @{html.escape(str(username))}\n"
        f"🎂 День рождения: {html.escape(str(bday))}\n\n"
    )

    if orders:
        text += f"📦 <b>Ваши заказы ({len(orders)}):</b>\n"
        for o in orders:
            order_num = o.get("number", "—")
            service = o.get("service", "—")
            price = o.get("price", 0)
            status_emoji = get_status_emoji(o.get("status", "new"))
            created = o.get("created_at") or o.get("date") or ""
            short_date = created.split("T")[0] if created else "Неизвестно"
            text += f"\n🔹 <b>#{html.escape(str(order_num))}</b> ({short_date})\n   {html.escape(str(service))} | {price}₽\n   Статус: {status_emoji}"
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
    await asyncio.to_thread(_fb_user_set, message.from_user.id, {"birthday": message.text.strip()})
    await state.clear()
    await message.answer(tw("✅ День рождения сохранён!"), reply_markup=main_menu())

# ============================================
# АДМИНКА: ЧАТЫ
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
    history = "\n".join([f"{'👤 Клиент' if m[1] else ' Вы'}: {html.escape(str(m[0]))}" for m in reversed(msgs)])
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
        await bot.send_message(target_user_id, tw(f" <b>Ответ от Nil Bots:</b>\n\n{html.escape(message.text)}"), parse_mode="HTML")
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

# ============================================
# АДМИНКА: РАССЫЛКА
# ============================================
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer(" Недоступно", show_alert=True)
        return
    await call.answer()
    await state.clear()
    await call.message.edit_text(
        tw(
            "📢 <b>Рассылка</b>\n\n"
            "Напиши текст сообщения — его получат все пользователи бота.\n\n"
            "Можно использовать разметку:\n"
            "<b>жирный</b>, <i>курсив</i>, <u>подчёркнутый</u>\n"
            "<a href=\"https://example.com\">ссылка</a>\n\n"
            "(отмена — /cancel)"
        ),
        reply_markup=back_kb("start_back_to_main"), parse_mode="HTML"
    )
    await state.set_state(BroadcastState.waiting_text)

@router.message(BroadcastState.waiting_text)
async def broadcast_text_received(message: Message, state: FSMContext):
    text = message.text
    await state.update_data(broadcast_text=text)
    users = await asyncio.to_thread(_fb_user_ids)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="✏️ Переписать", callback_data="broadcast_rewrite")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ])
    preview = f"📢 <b>Предпросмотр рассылки:</b>\n\n{text}\n\n👥 Получателей: <b>{len(users)}</b>"
    try:
        await message.answer(preview, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(
            f"📢 Предпросмотр рассылки:\n\n{text}\n\n👥 Получателей: {len(users)}\n\n"
            "⚠️ В тексте ошибка разметки! При отправке сообщение уйдёт обычным текстом.",
            reply_markup=kb
        )
    await state.set_state(BroadcastState.confirming)

@router.callback_query(F.data == "broadcast_rewrite", BroadcastState.confirming)
async def broadcast_rewrite(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(tw("✏️ Напиши новый текст рассылки:"), reply_markup=back_kb("start_back_to_main"))
    await state.set_state(BroadcastState.waiting_text)

@router.callback_query(F.data == "broadcast_cancel", BroadcastState.confirming)
async def broadcast_cancel(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text(tw("❌ Рассылка отменена."), reply_markup=admin_menu())

@router.callback_query(F.data == "broadcast_confirm", BroadcastState.confirming)
async def broadcast_confirm(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    text = data.get("broadcast_text")
    if not text:
        await state.clear()
        await call.message.edit_text(tw("❌ Текст не найден. Начни заново."), reply_markup=admin_menu())
        return
    await state.clear()
    users = await asyncio.to_thread(_fb_user_ids)
    total = len([u for u in users if u != ADMIN_ID])
    await call.message.edit_text(tw(f"📢 Рассылка начата...\n👥 Получателей: {total}"), reply_markup=None)

    sent = 0
    failed = 0
    for uid in users:
        if uid == ADMIN_ID:
            continue
        try:
            try:
                await bot.send_message(uid, text, parse_mode="HTML")
            except Exception:
                await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await bot.send_message(
        ADMIN_ID,
        f"✅ <b>Рассылка завершена!</b>\n\n📤 Отправлено: {sent}\n⚠️ Не доставлено: {failed}\n👥 Всего: {total}",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )

# ============================================
# АДМИНКА: ПРОМОКОДЫ
# ============================================
@router.callback_query(F.data == "admin_promos")
async def admin_promos(call: CallbackQuery):
    await call.answer()
    promos = await asyncio.to_thread(_fb_promo_list)

    text = f"🎟 <b>Управление промокодами</b>\n{DIVIDER}\n\n"
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
    await message.answer(tw(" Введи количество активаций:"))
    await state.set_state(AddPromoState.waiting_for_uses)

@router.message(AddPromoState.waiting_for_uses)
async def promo_uses_input(message: Message, state: FSMContext):
    try:
        uses = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи целое число.")
        return
    if uses <= 0:
        await message.answer(" Должно быть больше 0.")
        return
    data = await state.get_data()
    try:
        await asyncio.to_thread(_fb_promo_set, data['code'], data['discount'], uses)
    except Exception as e:
        await message.answer(f"❌ Ошибка сохранения: {e}")
        await state.clear()
        return
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
    print(f" Admin ID: {ADMIN_ID}")
    print(f"💰 Цены: Бот={PRICE_BOT_ONLY}₽, Basic={PRICE_SERVER_BASIC}₽, Премиум=STOP LIST")
    print(f" RollyPay: {'✅ подключён' if ROLLY_API_KEY else '⚠️ НЕ подключён (оплата недоступна)'}")

    start_settings_listener()
    await restore_pending_payments()  # Восстанавливаем неоплаченные заказы
    asyncio.create_task(payment_polling_task())  # Запускаем фоновую проверку

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
