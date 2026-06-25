import asyncio
import random
import time
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                            InlineKeyboardButton, ChatPermissions, FSInputFile,
                            ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
import os
from datetime import timedelta

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

DB_FILE = "db.json"

def save_db():
    data = {
        "shop_products": shop_products,
        "shop_users": {str(k): v for k, v in shop_users.items()},
        "shop_orders": shop_orders,
        "shop_reviews": shop_reviews,
        "purchase_logs": purchase_logs,
        "promo_usage": {k: [str(i) for i in v] for k, v in promo_usage.items()},
        "verified_users": {str(k): v for k, v in verified_users.items()},
        "user_lang": {str(k): v for k, v in user_lang.items()},
        "game_categories": GAME_CATEGORIES,
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_db():
    global shop_products, shop_users, shop_orders, shop_reviews
    global purchase_logs, promo_usage, verified_users, user_lang
    if not os.path.exists(DB_FILE):
        return
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        shop_products = data.get("shop_products", {})
        shop_users = {int(k): v for k, v in data.get("shop_users", {}).items()}
        shop_orders = data.get("shop_orders", [])
        shop_reviews = data.get("shop_reviews", [])
        purchase_logs = data.get("purchase_logs", [])
        promo_usage = {k: [int(i) for i in v] for k, v in data.get("promo_usage", {}).items()}
        verified_users = {int(k): v for k, v in data.get("verified_users", {}).items()}
        user_lang = {int(k): v for k, v in data.get("user_lang", {}).items()}
        if "game_categories" in data:
            GAME_CATEGORIES.clear()
            GAME_CATEGORIES.update(data["game_categories"])
        print("✅ База данных загружена.")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки БД: {e}")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

warns_db = {}
MAX_WARNS = 3

EMOJIS = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
          "🦁", "🐮", "🐷", "🐸", "🐙", "🦋", "🐬", "🦄", "🐲", "🦅"]
pending_verifications = {}

# Язык пользователей
user_lang = {}

# Верифицированные пользователи: user_id -> timestamp верификации
verified_users = {}
VERIFY_COOLDOWN = 86400  # 24 часа в секундах

class UserStates(StatesGroup):
    waiting_promo = State()
    waiting_topup = State()
    waiting_stars_amount = State()
    waiting_crypto_hash = State()

# Промокоды: код -> скидка/сообщение
PROMOCODES = {
    "ANISIMOV": "скидка 6%",
}

TEXTS = {
    "ru": {
        "welcome": "👋 Добро пожаловать!\n\nВыберите раздел ниже 👇",
        "catalog": "🏷️ Каталог",
        "stock": "📦 Наличие",
        "profile": "👤 Профиль",
        "about": "ℹ️ О магазине",
        "support": "💬 Поддержка",
        "language": "🌐 Язык",
        "info": "ℹ️ Информация",
        "catalog_text": "🏷️ <b>Каталог</b>\n\nЗдесь будет каталог товаров.",
        "stock_text": "📦 <b>Наличие</b>\n\nЗдесь будет информация о наличии.",
        "profile_text": "👤 <b>Профиль</b>\n\n👤 Имя: {name} 🪪 ID: <code>{user_id}</code>\n💳 Баланс: <b>0.0 ₽</b>",
        "topup": "💰 Пополнить баланс",
        "orders": "📋 История заказов",
        "topup_history": "📊 История пополнений",
        "favorites": "❤️ Избранное",
        "promo": "🎟️ Промокод",
        "main_menu": "🏠 Главное меню",
        "about_text": "🏠 <b>Магазин:</b> <code>Anisimov store</code>\n🕐 <b>Дата создания:</b> <code>2026-06-25</code>\n📢 <b>Канал:</b> <a href='https://t.me/Anisimovfunpay'>Посмотреть</a>",
        "support_text": "✈️ <b>Поддержка:</b> <a href='https://t.me/AnisimovWork'>@AnisimovWork</a>",
        "lang_choice": "🌐 Выберите язык / Choose language:",
        "back": "◀️ Назад",
        "lang_set": "✅ Язык установлен: Русский",
    },
    "en": {
        "welcome": "👋 Welcome!\n\nChoose a section below 👇",
        "catalog": "🏷️ Catalog",
        "stock": "📦 Stock",
        "profile": "👤 Profile",
        "about": "ℹ️ About",
        "support": "💬 Support",
        "language": "🌐 Language",
        "catalog_text": "🏷️ <b>Catalog</b>\n\nProduct catalog will be here.",
        "stock_text": "📦 <b>Stock</b>\n\nStock info will be here.",
        "profile_text": "👤 <b>Profile</b>\n\n👤 Name: {name} 🪪 ID: <code>{user_id}</code>\n💳 Balance: <b>0.0 ₽</b>",
        "topup": "💰 Top up balance",
        "orders": "📋 Order history",
        "topup_history": "📊 Top up history",
        "favorites": "❤️ Favorites",
        "promo": "🎟️ Promo code",
        "main_menu": "🏠 Main menu",
        "about_text": "🏠 <b>Shop:</b> <code>Anisimov store</code>\n🕐 <b>Created:</b> <code>2026-06-25</code>\n📢 <b>Channel:</b> <a href='https://t.me/Anisimovfunpay'>View</a>",
        "support_text": "✈️ <b>Support:</b> <a href='https://t.me/AnisimovWork'>@AnisimovWork</a>",
        "lang_choice": "🌐 Выберите язык / Choose language:",
        "back": "◀️ Back",
        "lang_set": "✅ Language set: English",
    }
}

MENU_IMAGE = "ChatGPT_Image_25_._2026_._15_48_32.png"
CATALOG_IMAGE = "каталог"

def get_lang(user_id: int) -> str:
    return user_lang.get(user_id, "ru")

def build_main_menu(user_id: int) -> InlineKeyboardMarkup:
    t = TEXTS[get_lang(user_id)]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t["catalog"], callback_data="menu:catalog"),
            InlineKeyboardButton(text=t["stock"], callback_data="menu:stock"),
        ],
        [InlineKeyboardButton(text=t["profile"], callback_data="menu:profile")],
        [
            InlineKeyboardButton(text=t["about"], callback_data="menu:about"),
            InlineKeyboardButton(text=t["support"], callback_data="menu:support"),
        ],
        [InlineKeyboardButton(text=t["language"], callback_data="menu:language")],
    ])

def build_back_keyboard(user_id: int) -> InlineKeyboardMarkup:
    t = TEXTS[get_lang(user_id)]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["back"], callback_data="menu:back")]
    ])

def build_profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    t = TEXTS[get_lang(user_id)]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["topup"], callback_data="profile:topup")],
        [
            InlineKeyboardButton(text=t["orders"], callback_data="profile:orders"),
            InlineKeyboardButton(text=t["topup_history"], callback_data="profile:topup_history"),
        ],
        [
            InlineKeyboardButton(text=t["favorites"], callback_data="profile:favorites"),
            InlineKeyboardButton(text=t["promo"], callback_data="profile:promo"),
        ],
        [InlineKeyboardButton(text=t["main_menu"], callback_data="menu:back")],
    ])

def build_lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ]
    ])

def build_reply_menu(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_lang(user_id)
    catalog_btn = "🏷️ Тарифы" if lang == "ru" else "🏷️ Tariffs"
    sub_btn = "📢 Подписка" if lang == "ru" else "📢 Subscribe"
    rows = [[KeyboardButton(text=catalog_btn), KeyboardButton(text=sub_btn)]]
    if user_id in ADMIN_IDS:
        rows.append([KeyboardButton(text="⚙️ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


    correct = random.choice(EMOJIS)
    options = [correct] + random.sample([e for e in EMOJIS if e != correct], 5)
    random.shuffle(options)
    return correct, options

def build_keyboard(options, user_id):
    buttons = []
    row = []
    for i, emoji in enumerate(options):
        row.append(InlineKeyboardButton(
            text=emoji, callback_data=f"verify:{user_id}:{emoji}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def generate_captcha():
    correct = random.choice(EMOJIS)
    options = [correct] + random.sample([e for e in EMOJIS if e != correct], 5)
    random.shuffle(options)
    return correct, options

def build_keyboard(options, user_id):
    buttons = []
    row = []
    for i, emoji in enumerate(options):
        row.append(InlineKeyboardButton(
            text=emoji, callback_data=f"verify:{user_id}:{emoji}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

CHANNEL_USERNAME = "@Anisimovfunpay"
CHANNEL_LINK = "https://t.me/Anisimovfunpay"

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        print(f"[check_subscription error] {e}")
        return False

def build_subscribe_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data=f"check_sub:{user_id}")]
    ])

async def send_main_menu(target, user_id: int, with_photo: bool = False):
    """Отправляет главное меню. target — Message или CallbackQuery."""
    t = TEXTS[get_lang(user_id)]
    reply_kb = build_reply_menu(user_id)
    if isinstance(target, CallbackQuery):
        if with_photo:
            try:
                await target.message.delete()
            except Exception:
                pass
            photo = FSInputFile(MENU_IMAGE)
            await target.message.answer_photo(
                photo=photo,
                caption=t["welcome"],
                reply_markup=build_main_menu(user_id),
                parse_mode="HTML"
            )
            await target.message.answer("👇", reply_markup=reply_kb)
        else:
            try:
                await target.message.edit_text(t["welcome"], reply_markup=build_main_menu(user_id), parse_mode="HTML")
            except Exception:
                await target.message.answer(t["welcome"], reply_markup=build_main_menu(user_id), parse_mode="HTML")
    else:
        if with_photo:
            photo = FSInputFile(MENU_IMAGE)
            await target.answer_photo(
                photo=photo,
                caption=t["welcome"],
                reply_markup=build_main_menu(user_id),
                parse_mode="HTML"
            )
            await target.answer("👇", reply_markup=reply_kb)
        else:
            await target.answer(t["welcome"], reply_markup=build_main_menu(user_id), parse_mode="HTML")


async def is_admin(message: Message) -> bool:
    if message.from_user.id in ADMIN_IDS:
        return True
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ("administrator", "creator")

def get_warns(chat_id, user_id):
    return warns_db.get(chat_id, {}).get(user_id, 0)

def add_warn(chat_id, user_id):
    if chat_id not in warns_db:
        warns_db[chat_id] = {}
    warns_db[chat_id][user_id] = warns_db[chat_id].get(user_id, 0) + 1
    return warns_db[chat_id][user_id]

def clear_warns(chat_id, user_id):
    if chat_id in warns_db and user_id in warns_db[chat_id]:
        del warns_db[chat_id][user_id]

@dp.message(F.new_chat_members)
async def on_new_member(message: Message):
    for new_member in message.new_chat_members:
        if new_member.is_bot:
            continue
        try:
            await bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=new_member.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception:
            pass
        correct, options = generate_captcha()
        pending_verifications[new_member.id] = {
            "correct": correct,
            "chat_id": message.chat.id
        }
        await message.answer(
            f"🤖 <b>Проверка, что вы не робот</b>\n"
            f"Нажмите на этот эмодзи: {correct}",
            reply_markup=build_keyboard(options, new_member.id),
            parse_mode="HTML"
        )

@dp.callback_query(F.data.startswith("verify:"))
async def on_verify(callback: CallbackQuery):
    _, user_id_str, chosen = callback.data.split(":")
    user_id = int(user_id_str)
    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не твоя капча!", show_alert=True)
        return
    data = pending_verifications.get(user_id)
    if not data:
        await callback.answer("⚠️ Капча устарела.", show_alert=True)
        return
    if chosen == data["correct"]:
        del pending_verifications[user_id]
        # Проверяем подписку сразу
        if await check_subscription(user_id):
            try:
                await bot.restrict_chat_member(
                    chat_id=data["chat_id"],
                    user_id=user_id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
            except Exception:
                pass
            verified_users[user_id] = time.time()
            # Регистрируем пользователя
            if user_id not in shop_users:
                shop_users[user_id] = {
                    "name": callback.from_user.full_name,
                    "username": callback.from_user.username or "—",
                    "join_time": time.strftime("%Y-%m-%d %H:%M")
                }
            save_db()
            await callback.message.edit_text(
                "🌐 Выберите язык / Choose language:",
                reply_markup=build_lang_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer("✅ Успешно!", show_alert=False)
        else:
            # Сохраняем chat_id для проверки подписки позже
            pending_verifications[f"sub_{user_id}"] = {"chat_id": data["chat_id"]}
            await callback.message.edit_text(
                f"✅ Капча пройдена!\n\n"
                f"📢 Теперь подпишись на канал и нажми <b>«Я подписался»</b>",
                reply_markup=build_subscribe_keyboard(user_id),
                parse_mode="HTML"
            )
            await callback.answer("✅ Капча пройдена!", show_alert=False)
    else:
        correct, options = generate_captcha()
        pending_verifications[user_id]["correct"] = correct
        await callback.message.edit_text(
            f"🤖 <b>Проверка, что вы не робот</b>\n"
            f"Нажмите на этот эмодзи: {correct}\n\n"
            f"❌ Неверно, попробуй ещё раз!",
            reply_markup=build_keyboard(options, user_id),
            parse_mode="HTML"
        )
        await callback.answer("❌ Неверно!", show_alert=True)

@dp.callback_query(F.data.startswith("check_sub:"))
async def on_check_sub(callback: CallbackQuery):
    _, user_id_str = callback.data.split(":")
    user_id = int(user_id_str)

    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не твоя кнопка!", show_alert=True)
        return

    data = pending_verifications.get(f"sub_{user_id}")
    if not data:
        await callback.answer("⚠️ Сессия устарела, напиши /start заново.", show_alert=True)
        return

    if await check_subscription(user_id):
        try:
            await bot.restrict_chat_member(
                chat_id=data["chat_id"],
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
        except Exception:
            pass
        del pending_verifications[f"sub_{user_id}"]
        verified_users[user_id] = time.time()
        # Регистрируем пользователя
        shop_users[user_id] = {
            "name": callback.from_user.full_name,
            "username": callback.from_user.username or "—",
            "join_time": time.strftime("%Y-%m-%d %H:%M")
        }
        save_db()
        await callback.message.edit_text(
            "🌐 Выберите язык / Choose language:",
            reply_markup=build_lang_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("✅ Добро пожаловать!", show_alert=False)
    else:
        await callback.answer(
            "❌ Ты не подписан на канал! Подпишись и нажми кнопку снова.",
            show_alert=True
        )

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    now = time.time()

    # Регистрируем пользователя при каждом /start
    register_user(message.from_user)
    log_action(message.from_user, "открыл бота (/start)")

    # Если уже верифицирован и не прошло 24 часа — сразу меню
    if user_id in verified_users and (now - verified_users[user_id]) < VERIFY_COOLDOWN:
        await send_main_menu(message, user_id, with_photo=True)
        return

    # Иначе — капча
    correct, options = generate_captcha()
    pending_verifications[user_id] = {
        "correct": correct,
        "chat_id": message.chat.id
    }
    await message.answer(
        f"🤖 <b>Проверка, что вы не робот</b>\n"
        f"Нажмите на этот эмодзи: {correct}",
        reply_markup=build_keyboard(options, user_id),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("profile:"))
async def on_profile_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    user_id = callback.from_user.id
    lang = get_lang(user_id)

    msgs = {
        "ru": {
            "topup": "💰 Пополнение баланса — скоро будет доступно.",
            "orders": "📋 История заказов пуста.",
            "topup_history": "📊 История пополнений пуста.",
            "favorites": "❤️ Избранное пусто.",
        },
        "en": {
            "topup": "💰 Top up — coming soon.",
            "orders": "📋 Order history is empty.",
            "topup_history": "📊 Top up history is empty.",
            "favorites": "❤️ Favorites is empty.",
        }
    }

    if action == "promo":
        await state.set_state(UserStates.waiting_promo)
        promo_text = "🎟️ Введите промокод:" if lang == "ru" else "🎟️ Enter promo code:"
        await callback.message.answer(promo_text)
        await callback.answer()
    elif action == "topup":
        await state.set_state(UserStates.waiting_topup)
        topup_text = "💰 Отправьте сумму пополнения (в рублях):" if lang == "ru" else "💰 Enter top up amount (in rubles):"
        await callback.message.answer(topup_text)
        await callback.answer()
    else:
        text = msgs[lang].get(action, "...")
        await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "cancel_stars")
async def on_cancel_stars(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()

@dp.message(UserStates.waiting_topup)
async def on_topup_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    await state.clear()
    if not message.text or not message.text.isdigit() or int(message.text) < 1:
        text = "❌ Введите корректную сумму." if lang == "ru" else "❌ Enter a valid amount."
        await message.answer(text)
        return
    amount = message.text
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦋 CryptoBot", callback_data=f"pay:crypto:{amount}")],
        [InlineKeyboardButton(text="🔀 СБП / Крипта", callback_data=f"pay:sbp:{amount}")],
        [InlineKeyboardButton(text="⭐ Звёзды", callback_data=f"pay:stars:{amount}")],
    ])
    await message.answer(
        f"💰 <b>{amount}.0 ₽</b>\n\nВыберите способ:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.message(UserStates.waiting_stars_amount)
async def on_stars_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not message.text.isdigit():
        await message.answer("❌ Введите только цифры.")
        return
    amount = int(message.text)
    if amount < 50:
        await message.answer("❌ Минимум 50 звёзд.")
        return
    if amount > 10000:
        await message.answer("❌ Максимум 10 000 звёзд за один заказ.")
        return
    await state.clear()
    price_rub = round(amount * 1.37, 2)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Отправить звёзды", url="https://t.me/AnisimovWork")],
    ])
    await message.answer(
        f"⭐ <b>Заявка на покупку звёзд</b>\n\n"
        f"⭐ Количество: <b>{amount} звёзд</b>\n"
        f"💰 Сумма: <b>{price_rub} ₽</b>\n\n"
        f"1. Нажми кнопку ниже\n"
        f"2. Открой @AnisimovWork\n"
        f"3. Отправь <b>{amount} звёзд</b>\n"
        f"4. Напиши что оплатил",
        reply_markup=kb,
        parse_mode="HTML"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⭐ <b>Заявка на покупку звёзд!</b>\n\n"
                f"👤 {message.from_user.full_name} | <code>{user_id}</code>\n"
                f"⭐ {amount} звёзд — {price_rub} ₽",
                parse_mode="HTML"
            )
        except Exception:
            pass
    log_action(message.from_user, f"запросил покупку {amount} звёзд")

@dp.callback_query(F.data.startswith("crypto_paid:"))
async def on_crypto_paid(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    amount = parts[1]
    uid = parts[2]
    await state.set_state(UserStates.waiting_crypto_hash)
    await state.update_data(crypto_amount=amount)
    await callback.message.edit_text(
        f"✅ Отлично! Теперь отправь хэш транзакции (TX Hash):\n\n"
        f"Его можно найти в кошельке после отправки.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(UserStates.waiting_crypto_hash)
async def on_crypto_hash(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("crypto_amount", "?")
    await state.clear()
    tx_hash = message.text.strip()
    # Уведомляем админов с кнопками подтверждения
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_pay:approve:{message.from_user.id}:{amount}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"confirm_pay:reject:{message.from_user.id}:{amount}"),
        ]
    ])
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🦋 <b>Заявка на пополнение TON!</b>\n\n"
                f"👤 {message.from_user.full_name} | <code>{message.from_user.id}</code>\n"
                f"💰 Сумма: <b>{amount} ₽</b>\n"
                f"🔗 TX Hash: <code>{tx_hash}</code>\n\n"
                f"Подтвердите или отклоните:",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
    await message.answer(
        f"✅ Заявка отправлена на проверку!\n\n"
        f"🔗 TX: <code>{tx_hash}</code>\n\n"
        f"Ожидайте подтверждения от администратора.\n\n"
        f"❓ Если не понимаете — пишите сюда: @AnisimovWork",
        parse_mode="HTML"
    )
    log_action(message.from_user, f"отправил TON оплату {amount}₽ TX:{tx_hash[:16]}...")

@dp.callback_query(F.data.startswith("confirm_pay:"))
async def on_confirm_pay(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    amount = parts[3]

    if action == "approve":
        try:
            await bot.send_message(
                user_id,
                f"✅ <b>Оплата подтверждена!</b>\n\n"
                f"💰 Баланс пополнен на <b>{amount} ₽</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ <b>Подтверждено администратором {callback.from_user.full_name}</b>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Подтверждено!", show_alert=True)
    else:
        try:
            await bot.send_message(
                user_id,
                f"❌ <b>Оплата отклонена.</b>\n\n"
                f"Если это ошибка — обратитесь в поддержку: @AnisimovWork",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await callback.message.edit_text(
            callback.message.text + f"\n\n❌ <b>Отклонено администратором {callback.from_user.full_name}</b>",
            parse_mode="HTML"
        )
        await callback.answer("❌ Отклонено.", show_alert=True)
async def on_topup_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    await state.clear()
    if not message.text.isdigit() or int(message.text) < 1:
        text = "❌ Введите корректную сумму." if lang == "ru" else "❌ Enter a valid amount."
        await message.answer(text)
        return
    amount = message.text
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦋 CryptoBot", callback_data=f"pay:crypto:{amount}")],
        [InlineKeyboardButton(text="🔀 СБП / Крипта", callback_data=f"pay:sbp:{amount}")],
        [InlineKeyboardButton(text="⭐ Звёзды", callback_data=f"pay:stars:{amount}")],
    ])
    await message.answer(
        f"💰 <b>{amount}.0 ₽</b>\n\nВыберите способ:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("pay:"))
async def on_pay_method(callback: CallbackQuery, state: FSMContext):
    _, method, amount = callback.data.split(":")
    user_id = callback.from_user.id
    lang = get_lang(user_id)

    if method == "crypto":
        ton_address = "UQBiw7YK0P9gOGXJ3oBRLwuye6OlStkVE5CcfoRMFr-KchOm"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"crypto_paid:{amount}:{user_id}")]
        ])
        await callback.message.edit_text(
            f"🦋 <b>Оплата через TON</b>\n\n"
            f"💰 Сумма: <b>{amount} ₽</b>\n\n"
            f"📤 Отправь TON на адрес:\n"
            f"<code>{ton_address}</code>\n\n"
            f"После оплаты нажми кнопку ниже и отправь хэш транзакции.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.answer()
    elif method == "sbp":
        text = (
            f"🔀 <b>СБП / Крипта</b>\n\n"
            f"💰 Сумма: <b>{amount} ₽</b>\n\n"
            f"Отправьте оплату и напишите в поддержку:\n@AnisimovWork"
        )
        await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    elif method == "stars":
        stars_amount = max(1, int(amount))
        await state.set_state(UserStates.waiting_stars_amount)
        await state.update_data(topup_amount=amount)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Пополнить через бота", url="https://t.me/AnisimovStartsNft_Bot")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_stars")]
        ])
        await callback.message.edit_text(
            f"⭐ <b>Покупка звёзд</b>\n\n"
            f"• Цена за 1 звезду: <b>1.37₽/шт.</b>\n\n"
            f"• Минимум: <b>50 звёзд</b>\n"
            f"• Максимум (за один заказ): <b>10 000 звёзд</b>\n\n"
            f"• Баланса хватает на покупку: ~0 звёзд (0₽)\n\n"
            f"🔎 Введите количество звёзд для покупки:\n\n"
            f"Или пополни напрямую через @AnisimovStartsNft_Bot 👆",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.answer()

@dp.message(UserStates.waiting_promo)
async def on_promo_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    code = message.text.strip().upper()

    await state.clear()

    if code in PROMOCODES:
        result = PROMOCODES[code]
        # Записываем кто использовал промокод
        if code not in promo_usage:
            promo_usage[code] = []
        if user_id not in promo_usage[code]:
            promo_usage[code].append(user_id)
        log_action(message.from_user, f"ввёл промокод {code} ✅")
        text = f"✅ Промокод принят! {result}" if lang == "ru" else f"✅ Promo accepted! {result}"
    else:
        log_action(message.from_user, f"ввёл неверный промокод: {code}")
        text = "❌ Промокод не найден." if lang == "ru" else "❌ Promo code not found."

    await message.answer(text)

async def edit_or_replace(callback: CallbackQuery, text: str, keyboard, parse_mode="HTML", disable_web_page_preview=False):
    """Редактирует сообщение. Если там фото — удаляет и отправляет текст заново."""
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
        else:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)

@dp.callback_query(F.data.startswith("menu:"))
async def on_menu(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    user_id = callback.from_user.id
    register_user(callback.from_user)
    t = TEXTS[get_lang(user_id)]

    if action == "back":
        log_action(callback.from_user, "открыл главное меню")
        await send_main_menu(callback, user_id, with_photo=True)
    elif action == "catalog":
        log_action(callback.from_user, "открыл каталог")
        # Показываем категории у которых есть товары
        cats = {}
        for pid, v in shop_products.items():
            g = v.get("game", "Other")
            cats.setdefault(g, 0)
            cats[g] += 1
        try:
            await callback.message.delete()
        except Exception:
            pass
        if cats:
            buttons = [[InlineKeyboardButton(text=f"🎮 {g}", callback_data=f"cat:catalog:{g}")] for g in cats]
            buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:back")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            caption = "🛍 <b>Выберите категорию:</b>"
        else:
            caption = "🏷️ <b>Каталог</b>\n\nТоваров пока нет."
            buttons = [[InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:back")]]
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        photo = FSInputFile(CATALOG_IMAGE)
        await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    elif action == "stock":
        log_action(callback.from_user, "открыл наличие")
        try:
            await callback.message.delete()
        except Exception:
            pass
        if shop_products:
            # Группируем по категориям
            cats = {}
            for pid, v in shop_products.items():
                g = v.get("game", "Other")
                cats.setdefault(g, [])
                cats[g].append(v)
            lines = []
            for g, items in cats.items():
                lines.append(f"——— {g} ———")
                for item in items:
                    stock = item.get("stock", 0)
                    lines.append(f"• • {item['name']} | {item['description']} - {item['price']} ₽ ({stock} штук)")
            caption = "📦 <b>Наличие товаров:</b>\n\n" + "\n".join(lines)
        else:
            caption = "📦 <b>Наличие</b>\n\nТоваров пока нет."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back")]])
        photo = FSInputFile("ChatGPT_Image_25_._2026_._15_51_56.png")
        await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    elif action == "profile":
        log_action(callback.from_user, "открыл профиль")
        name = callback.from_user.full_name
        text = t["profile_text"].format(name=name, user_id=user_id)
        try:
            await callback.message.delete()
        except Exception:
            pass
        photo = FSInputFile("профиль")
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=build_profile_keyboard(user_id),
            parse_mode="HTML"
        )
    elif action == "about":
        log_action(callback.from_user, "открыл о магазине")
        await edit_or_replace(callback, t["about_text"], build_back_keyboard(user_id), disable_web_page_preview=True)
    elif action == "support":
        log_action(callback.from_user, "открыл поддержку")
        await edit_or_replace(callback, t["support_text"], build_back_keyboard(user_id), disable_web_page_preview=True)
    elif action == "language":
        log_action(callback.from_user, "открыл выбор языка")
        await edit_or_replace(callback, t["lang_choice"], build_lang_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("lang:"))
async def on_lang(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user_lang[user_id] = lang
    save_db()
    t = TEXTS[lang]
    await callback.answer(t["lang_set"], show_alert=False)
    await send_main_menu(callback, user_id, with_photo=True)

# ===== ДАННЫЕ АДМИН ПАНЕЛИ =====
shop_products = {}   # id -> {name, price, description}
shop_orders = []     # [{user_id, product, price, time}]
shop_users = {}      # user_id -> {name, username, join_time}
shop_reviews = []    # [{user_id, name, text, time}]
purchase_logs = []   # [{user_id, name, product, price, time}]
promo_usage = {}     # promo_code -> [user_id, ...]
broadcast_pending = {}  # admin_id -> True
admin_states = {}    # admin_id -> state
action_logs = []     # все действия пользователей

def log_action(user, action: str):
    action_logs.append({
        "name": user.full_name,
        "user_id": user.id,
        "action": action,
        "time": time.strftime("%Y-%m-%d %H:%M")
    })
    # Держим только последние 200 записей
    if len(action_logs) > 200:
        action_logs.pop(0)

GAME_CATEGORIES = {
    "1": "CS2",
    "2": "Minecraft",
    "3": "Telegram",
    "4": "Discord",
    "5": "Valorant",
    "6": "GTA 5",
    "7": "Roblox",
    "8": "Other"
}

class AdminStates(StatesGroup):
    waiting_product_name = State()
    waiting_product_game = State()
    waiting_product_price = State()
    waiting_product_stars = State()
    waiting_product_stock = State()
    waiting_product_desc = State()
    waiting_broadcast = State()
    waiting_review_reply = State()
    waiting_settings_value = State()
    waiting_product_data = State()
    waiting_new_category = State()

def build_admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Товары", callback_data="adm:products"),
            InlineKeyboardButton(text="🛒 Заказы", callback_data="adm:orders"),
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="adm:users"),
            InlineKeyboardButton(text="🎟️ Промокоды", callback_data="adm:promos"),
        ],
        [
            InlineKeyboardButton(text="📋 Логи", callback_data="adm:logs"),
            InlineKeyboardButton(text="⭐ Отзывы", callback_data="adm:reviews"),
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast"),
            InlineKeyboardButton(text="🎮 Категории", callback_data="adm:categories"),
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="adm:settings")],
    ])

def build_admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:back")]
    ])

async def show_admin_products(callback: CallbackQuery, page: int = 0):
    PAGE_SIZE = 8
    all_products = list(shop_products.items())
    total = len(all_products)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    # Текст со списком всех товаров
    if not all_products:
        lines = "Товаров нет."
    else:
        lines_list = []
        for pid, v in all_products:
            stock = v.get("stock", 0)
            price = v.get("price", "0")
            data_count = len(v.get("data", []))
            icon = "✅" if stock > 0 else "❌"
            lines_list.append(f"{icon} {v['name']}\n💰 {price}₽ | 📦 {data_count}")
        lines = "\n\n".join(lines_list)

    text = f"📦 <b>Товары ({total})</b>\n\n{lines}"

    # Кнопки текущей страницы
    page_items = all_products[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    buttons = []
    for pid, v in page_items:
        stock = v.get("stock", 0)
        icon = "✅" if stock > 0 else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {v['name']}",
            callback_data=f"product_manage:{pid}"
        )])

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"adm:products_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="adm:products"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"adm:products_page_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить", callback_data="adm:add_product"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="adm:back"),
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(F.text == "⚙️ Админ панель")
async def reply_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    total_users = len(shop_users)
    total_products = len(shop_products)
    total_orders = len(shop_orders)
    text = (
        f"🔧 <b>Админ-панель: Anisimov Shop</b>\n\n"
        f"🟢 Статус: активен\n"
        f"📦 Товаров: <b>{total_products}</b>\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"🛒 Заказов: <b>{total_orders}</b>\n\n"
        f"Выберите раздел:"
    )
    await message.answer(text, reply_markup=build_admin_panel(), parse_mode="HTML")

@dp.message(F.text.in_({"🏷️ Тарифы", "🏷️ Tariffs"}))
async def reply_catalog(message: Message):
    user_id = message.from_user.id
    register_user(message.from_user)
    t = TEXTS[get_lang(user_id)]
    cats = {}
    for pid, v in shop_products.items():
        g = v.get("game", "Other")
        cats.setdefault(g, 0)
        cats[g] += 1
    try:
        await message.delete()
    except Exception:
        pass
    if cats:
        buttons = [[InlineKeyboardButton(text=f"🎮 {g}", callback_data=f"cat:catalog:{g}")] for g in cats]
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:back")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        caption = "🛍 <b>Выберите категорию:</b>"
    else:
        caption = "🏷️ <b>Каталог</b>\n\nТоваров пока нет."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:back")]])
    photo = FSInputFile(CATALOG_IMAGE)
    await message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")

@dp.message(F.text.in_({"📢 Подписка", "📢 Subscribe"}))
async def reply_subscription(message: Message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    text = "📢 <b>Подписка</b>\n\nПодпишись на наш канал:" if lang == "ru" else "📢 <b>Subscribe</b>\n\nFollow our channel:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 @Anisimovfunpay", url="https://t.me/Anisimovfunpay")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.message(Command("admins"))
async def cmd_admins(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("🚫 Нет прав.")
        return
    total_users = len(shop_users)
    total_products = len(shop_products)
    total_orders = len(shop_orders)
    text = (
        f"🔧 <b>Админ-панель: Anisimov Shop</b>\n\n"
        f"🟢 Статус: активен\n"
        f"📦 Товаров: <b>{total_products}</b>\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"🛒 Заказов: <b>{total_orders}</b>\n\n"
        f"Выберите раздел:"
    )
    await message.answer(text, reply_markup=build_admin_panel(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("cat:"))
async def on_category(callback: CallbackQuery):
    _, section, game = callback.data.split(":", 2)
    user_id = callback.from_user.id
    t = TEXTS[get_lang(user_id)]

    # Товары выбранной категории
    items = {pid: v for pid, v in shop_products.items() if v.get("game", "Other") == game}
    back_cb = "menu:catalog" if section == "catalog" else "menu:stock"

    if section == "catalog":
        if items:
            lines = "\n\n".join([
                f"📦 <b>{v['name']}</b>\n💰 Цена: <b>{v['price']}₽</b>\n📝 {v['description']}\n📊 В наличии: {v.get('stock',0)} шт."
                for v in items.values()
            ])
            caption = f"🎮 <b>{game}</b>\n\n{lines}"
            buttons = [[InlineKeyboardButton(text=f"🛒 Купить: {v['name']}", callback_data=f"buy:{pid}")] for pid, v in items.items()]
            buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb)])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        else:
            caption = f"🎮 <b>{game}</b>\n\n😔 Товаров пока нет."
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb)]])
        try:
            await callback.message.delete()
        except Exception:
            pass
        photo = FSInputFile(CATALOG_IMAGE)
        await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        # stock — с фото
        if items:
            lines = "\n".join([f"• <b>{v['name']}</b>" for v in items.values()])
            caption = f"🎮 <b>Категория: {game}</b>\n\n{lines}"
        else:
            caption = f"🎮 <b>Категория: {game}</b>\n\n😔 Товаров пока нет."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb)]])
        try:
            await callback.message.delete()
        except Exception:
            pass
        photo = FSInputFile("ChatGPT_Image_25_._2026_._15_51_56.png")
        await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="HTML")

    await callback.answer()

@dp.callback_query(F.data.startswith("buy:"))
async def on_buy(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    lang = get_lang(user_id)

    product = shop_products.get(product_id)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    stars = product.get("stars", 1)
    price = product.get("price", "0")

    text = (
        f"🛒 <b>{product['name']}</b>\n\n"
        f"💰 Цена: <b>{price} ₽</b>\n"
        f"⭐ или <b>{stars} звёзд</b>\n\n"
        f"Выберите способ оплаты:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 Оплатить {price} ₽", callback_data=f"buymethod:rub:{product_id}")],
        [InlineKeyboardButton(text=f"⭐ Оплатить {stars} звёздами", callback_data=f"buymethod:stars:{product_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat:catalog:{product.get('game','Other')}")],
    ])
    await edit_or_replace(callback, text, kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("buymethod:"))
async def on_buy_method(callback: CallbackQuery):
    _, method, product_id = callback.data.split(":")
    user_id = callback.from_user.id
    lang = get_lang(user_id)

    product = shop_products.get(product_id)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    if method == "stars":
        stars = product.get("stars", 1)
        from aiogram.types import LabeledPrice
        prices = [LabeledPrice(label=product["name"], amount=stars)]
        await callback.message.answer_invoice(
            title=product["name"],
            description=product.get("description", ""),
            payload=f"product_{product_id}",
            currency="XTR",
            prices=prices,
        )
        await callback.answer()
    else:
        # Рубли — выдаём данные из базы
        product_data = product.get("data", [])
        order = {
            "user_id": user_id,
            "name": callback.from_user.full_name,
            "product": product["name"],
            "price": product["price"],
            "time": time.strftime("%Y-%m-%d %H:%M")
        }
        shop_orders.append(order)
        purchase_logs.append(order)

        if product_data:
            # Выдаём первую строку и удаляем её
            item_data = product_data.pop(0)
            shop_products[product_id]["stock"] = len(product_data)
            save_db()
            text = (
                f"✅ <b>Заказ оформлен!</b>\n\n"
                f"📦 {product['name']}\n"
                f"💰 {product['price']} ₽\n\n"
                f"🔑 <b>Ваши данные:</b>\n"
                f"<code>{item_data}</code>"
            )
        else:
            text = (
                f"✅ <b>Заказ оформлен!</b>\n\n"
                f"📦 {product['name']}\n"
                f"💰 {product['price']} ₽\n\n"
                f"⚠️ Данные закончились. Напишите в поддержку: @AnisimovWork"
            )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🛒 <b>Новый заказ!</b>\n\n"
                    f"👤 {callback.from_user.full_name} | <code>{user_id}</code>\n"
                    f"📦 {product['name']} — {product['price']}₽\n"
                    f"📊 Осталось данных: {len(product.get('data', []))}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В каталог", callback_data="menu:catalog")]
        ])
        await edit_or_replace(callback, text, kb, disable_web_page_preview=True)
        await callback.answer()

@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id

    if payload.startswith("topup_"):
        # Пополнение баланса звёздами
        parts = payload.split("_")
        amount = parts[2] if len(parts) > 2 else "?"
        stars = message.successful_payment.total_amount

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"⭐ <b>Пополнение звёздами!</b>\n\n"
                    f"👤 {message.from_user.full_name} | <code>{user_id}</code>\n"
                    f"⭐ {stars} звёзд",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await message.answer(
            f"✅ <b>Баланс пополнен!</b>\n\n"
            f"⭐ Оплачено: {stars} звёзд\n\n"
            f"📞 Подтверждение: @AnisimovWork",
            parse_mode="HTML"
        )

    elif payload.startswith("product_"):
        product_id = payload.replace("product_", "")
        product = shop_products.get(product_id)

        if product:
            order = {
                "user_id": user_id,
                "name": message.from_user.full_name,
                "product": product["name"],
                "price": f"{product.get('stars','?')}⭐",
                "time": time.strftime("%Y-%m-%d %H:%M")
            }
            shop_orders.append(order)
            purchase_logs.append(order)

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⭐ <b>Покупка за звёзды!</b>\n\n"
                        f"👤 {message.from_user.full_name} | <code>{user_id}</code>\n"
                        f"📦 {product['name']} — {product.get('stars','?')} звёзд",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

        await message.answer(
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"📦 {product['name'] if product else 'Товар'}\n\n"
            f"📞 Для получения: @AnisimovWork",
            parse_mode="HTML"
        )

@dp.callback_query(F.data.startswith("product_manage:"))
async def on_product_manage(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет прав.", show_alert=True)
        return
    pid = callback.data.split(":")[1]
    product = shop_products.get(pid)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return
    data_count = len(product.get("data", []))
    text = (
        f"📦 <b>{product['name']}</b>\n"
        f"🎮 {product.get('game','—')} | 💰 {product['price']}₽\n"
        f"📊 Данных в базе: <b>{data_count} шт.</b>\n\n"
        f"Отправь TXT файл или текст с данными\n"
        f"(каждая строка = один аккаунт/ключ)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить данные", callback_data=f"upload_data:{pid}")],
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"del_product:{pid}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:products")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("upload_data:"))
async def on_upload_data(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет прав.", show_alert=True)
        return
    pid = callback.data.split(":")[1]
    await state.set_state(AdminStates.waiting_product_data)
    await state.update_data(upload_pid=pid)
    await callback.message.edit_text(
        "📤 Отправь TXT файл или текст с данными.\n\n"
        "Каждая строка = один товар (аккаунт/ключ/пароль):\n"
        "<code>login1:pass1\nlogin2:pass2</code>\n\n"
        "/cancel — отмена",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(AdminStates.waiting_product_data)
async def on_product_data_upload(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    pid = data.get("upload_pid")
    await state.clear()

    if not pid or pid not in shop_products:
        await message.answer("❌ Товар не найден.")
        return

    lines = []

    if message.document:
        # Получаем TXT файл
        try:
            file = await bot.get_file(message.document.file_id)
            file_bytes = await bot.download_file(file.file_path)
            content = file_bytes.read().decode("utf-8")
            lines = [l.strip() for l in content.splitlines() if l.strip()]
        except Exception as e:
            await message.answer(f"❌ Ошибка чтения файла: {e}")
            return
    elif message.text:
        lines = [l.strip() for l in message.text.splitlines() if l.strip()]

    if not lines:
        await message.answer("❌ Данные пустые.")
        return

    if "data" not in shop_products[pid]:
        shop_products[pid]["data"] = []
    shop_products[pid]["data"].extend(lines)
    shop_products[pid]["stock"] = len(shop_products[pid]["data"])
    save_db()
    await message.answer(
        f"✅ Добавлено <b>{len(lines)}</b> строк.\n"
        f"📊 Всего в базе: <b>{len(shop_products[pid]['data'])}</b> шт.",
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("del_cat:"))
async def on_del_category(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет прав.", show_alert=True)
        return
    num = callback.data.split(":")[1]
    name = GAME_CATEGORIES.pop(num, None)
    if name:
        # Перенумеруем
        items = list(GAME_CATEGORIES.values())
        GAME_CATEGORIES.clear()
        for i, item in enumerate(items, 1):
            GAME_CATEGORIES[str(i)] = item
        save_db()
        await callback.answer(f"🗑 Удалена: {name}", show_alert=True)
    # Обновляем список
    cats_list = "\n".join([f"{num}. {name}" for num, name in GAME_CATEGORIES.items()]) if GAME_CATEGORIES else "Категорий нет."
    text = f"🎮 <b>Категории ({len(GAME_CATEGORIES)})</b>\n\n{cats_list}"
    buttons = [[InlineKeyboardButton(text=f"🗑 Удалить: {n}", callback_data=f"del_cat:{num}")] for num, n in GAME_CATEGORIES.items()]
    buttons.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="adm:add_category")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm:back")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.message(AdminStates.waiting_new_category)
async def on_new_category(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    name = message.text.strip()
    new_num = str(len(GAME_CATEGORIES) + 1)
    GAME_CATEGORIES[new_num] = name
    save_db()
    await message.answer(f"✅ Категория <b>{name}</b> добавлена!", parse_mode="HTML")

@dp.callback_query(F.data.startswith("del_product:"))
async def on_del_product(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет прав.", show_alert=True)
        return
    pid = callback.data.split(":")[1]
    product = shop_products.pop(pid, None)
    if product:
        save_db()
        await callback.answer(f"🗑 Удалён: {product['name']}", show_alert=True)
    else:
        await callback.answer("❌ Товар не найден.", show_alert=True)
    # Обновляем список
    if not shop_products:
        text = "📦 <b>Товары</b>\n\nТоваров нет."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm:add_product")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:back")],
        ])
    else:
        cats = {}
        for p_id, v in shop_products.items():
            g = v.get("game", "Other")
            cats.setdefault(g, [])
            cats[g].append((p_id, v))
        lines = []
        for g, items in cats.items():
            lines.append(f"🎮 <b>{g}</b>")
            for p_id, item in items:
                stock = item.get("stock", 0)
                stock_icon = "✅" if stock > 0 else "❌"
                lines.append(f"  {stock_icon} {item['name']} — {item['price']}₽ | Кол-во: {stock}")
        text = f"📦 <b>Товары ({len(shop_products)})</b>\n\n" + "\n".join(lines)
        buttons = []
        for p_id, v in shop_products.items():
            buttons.append([InlineKeyboardButton(text=f"🗑 Удалить: {v['name']}", callback_data=f"del_product:{p_id}")])
        buttons.append([InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm:add_product")])
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm:back")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm:"))
async def on_admin_action(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет прав.", show_alert=True)
        return

    action = callback.data.split(":")[1]

    if action == "back":
        total_users = len(shop_users)
        total_products = len(shop_products)
        total_orders = len(shop_orders)
        text = (
            f"🔧 <b>Админ-панель: Anisimov Shop</b>\n\n"
            f"🟢 Статус: активен\n"
            f"📦 Товаров: <b>{total_products}</b>\n"
            f"👥 Пользователей: <b>{total_users}</b>\n"
            f"🛒 Заказов: <b>{total_orders}</b>\n\n"
            f"Выберите раздел:"
        )
        await callback.message.edit_text(text, reply_markup=build_admin_panel(), parse_mode="HTML")

    elif action == "products":
        await show_admin_products(callback, page=0)

    elif action.startswith("products_page_"):
        page = int(action.replace("products_page_", ""))
        await show_admin_products(callback, page=page)

    elif action == "add_product":
        await state.set_state(AdminStates.waiting_product_name)
        await callback.message.edit_text("📦 Введите название товара:", reply_markup=build_admin_back())

    elif action == "orders":
        if not shop_orders:
            text = "🛒 <b>Заказы</b>\n\nЗаказов нет."
        else:
            lines = "\n".join([f"• {o['name']} — {o['product']} — {o['price']}₽ [{o['time']}]" for o in shop_orders[-20:]])
            text = f"🛒 <b>Заказы (последние 20)</b>\n\n{lines}"
        await callback.message.edit_text(text, reply_markup=build_admin_back(), parse_mode="HTML")

    elif action == "users":
        if not shop_users:
            text = "👥 <b>Пользователи</b>\n\nНикого нет."
        else:
            lines = "\n".join([f"• <b>{v['name']}</b> | @{v.get('username','—')} | ID: <code>{uid}</code>" for uid, v in list(shop_users.items())[-30:]])
            text = f"👥 <b>Пользователи ({len(shop_users)})</b>\n\n{lines}"
        await callback.message.edit_text(text, reply_markup=build_admin_back(), parse_mode="HTML")

    elif action == "promos":
        lines = []
        for code, info in PROMOCODES.items():
            users = promo_usage.get(code, [])
            lines.append(f"• <b>{code}</b> — {info}\n  Использовали: {len(users)} чел.")
            for uid in users:
                u = shop_users.get(uid, {})
                lines.append(f"    └ {u.get('name','?')} | <code>{uid}</code>")
        text = "🎟️ <b>Промокоды</b>\n\n" + ("\n".join(lines) if lines else "Нет промокодов.")
        await callback.message.edit_text(text, reply_markup=build_admin_back(), parse_mode="HTML")

    elif action == "logs":
        if not action_logs:
            text = "📋 <b>Логи действий</b>\n\nПусто."
        else:
            lines = "\n".join([
                f"• <b>{l['name']}</b> | <code>{l['user_id']}</code>\n  {l['action']} [{l['time']}]"
                for l in reversed(action_logs[-50:])
            ])
            text = f"📋 <b>Логи действий (последние 50)</b>\n\n{lines}"
        await callback.message.edit_text(text, reply_markup=build_admin_back(), parse_mode="HTML")

    elif action == "reviews":
        if not shop_reviews:
            text = "⭐ <b>Отзывы</b>\n\nОтзывов нет."
        else:
            lines = "\n".join([f"• <b>{r['name']}</b> [{r['time']}]:\n  {r['text']}" for r in shop_reviews[-20:]])
            text = f"⭐ <b>Отзывы ({len(shop_reviews)})</b>\n\n{lines}"
        await callback.message.edit_text(text, reply_markup=build_admin_back(), parse_mode="HTML")

    elif action == "broadcast":
        await state.set_state(AdminStates.waiting_broadcast)
        await callback.message.edit_text(
            "📢 <b>Рассылка</b>\n\n"
            "Введите текст рассылки (поддерживается HTML: <b>&lt;b&gt;</b>, <b>&lt;i&gt;</b>, <b>&lt;u&gt;</b>, <b>&lt;a&gt;</b>) или отправьте фото с подписью:\n\n"
            "/cancel — отмена",
            reply_markup=build_admin_back(),
            parse_mode="HTML"
        )

    elif action == "settings":
        text = (
            "⚙️ <b>Настройки</b>\n\n"
            f"📛 Название магазина: <b>Anisimov store</b>\n"
            f"📢 Канал: @Anisimovfunpay\n"
            f"💬 Поддержка: @AnisimovWork\n"
        )
        await callback.message.edit_text(text, reply_markup=build_admin_back(), parse_mode="HTML")

    elif action == "categories":
        cats_list = "\n".join([f"{num}. {name}" for num, name in GAME_CATEGORIES.items()])
        text = f"🎮 <b>Категории ({len(GAME_CATEGORIES)})</b>\n\n{cats_list}"
        buttons = [[InlineKeyboardButton(text=f"🗑 Удалить: {name}", callback_data=f"del_cat:{num}")] for num, name in GAME_CATEGORIES.items()]
        buttons.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="adm:add_category")])
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm:back")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    elif action == "add_category":
        await state.set_state(AdminStates.waiting_new_category)
        await callback.message.edit_text(
            "🎮 Введите название новой категории:\n\n/cancel — отмена",
            reply_markup=build_admin_back()
        )

    await callback.answer()

@dp.message(AdminStates.waiting_product_name)
async def admin_product_name(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.update_data(product_name=message.text)
    await state.set_state(AdminStates.waiting_product_game)
    # Показываем кнопки выбора категории
    buttons = []
    row = []
    for num, name in GAME_CATEGORIES.items():
        row.append(InlineKeyboardButton(text=f"{num}. {name}", callback_data=f"game_cat:{num}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("🎮 Выберите категорию игры:", reply_markup=kb)

@dp.callback_query(F.data.startswith("game_cat:"))
async def on_game_category(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет прав.", show_alert=True)
        return
    num = callback.data.split(":")[1]
    game = GAME_CATEGORIES.get(num, "Other")
    await state.update_data(product_game=game)
    await state.set_state(AdminStates.waiting_product_price)
    await callback.message.edit_text(f"✅ Категория: <b>{game}</b>\n\n💰 Введите цену товара (только цифры):", parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.waiting_product_price)
async def admin_product_price(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.text.isdigit():
        await message.answer("❌ Введите только цифры.")
        return
    await state.update_data(product_price=message.text)
    await state.set_state(AdminStates.waiting_product_desc)
    await message.answer("⭐ Введите цену в звёздах Telegram (только цифры, мин. 1):")

@dp.message(AdminStates.waiting_product_desc)
async def admin_product_desc(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.text.isdigit() or int(message.text) < 1:
        await message.answer("❌ Введите число от 1.")
        return
    await state.update_data(product_stars=message.text)
    await state.set_state(AdminStates.waiting_product_stock)
    await message.answer("📦 Введите количество товара (от 1 до 999):")

@dp.message(AdminStates.waiting_product_stock)
async def admin_product_stock(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.text.isdigit() or not (1 <= int(message.text) <= 999):
        await message.answer("❌ Введите число от 1 до 999.")
        return
    await state.update_data(product_stock=message.text)
    await state.set_state(AdminStates.waiting_settings_value)
    await message.answer("📝 Введите описание товара:")

@dp.message(AdminStates.waiting_settings_value)
async def admin_product_final(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    await state.clear()
    product_id = str(int(time.time()))
    shop_products[product_id] = {
        "name": data["product_name"],
        "game": data.get("product_game", "Other"),
        "price": data["product_price"],
        "stars": int(data.get("product_stars", 1)),
        "stock": int(data.get("product_stock", 0)),
        "description": message.text
    }
    save_db()
    await message.answer(
        f"✅ Товар добавлен!\n\n"
        f"📦 <b>{data['product_name']}</b>\n"
        f"🎮 {data.get('product_game','Other')}\n"
        f"💰 {data['product_price']}₽ | ⭐ {data.get('product_stars','1')} звёзд\n"
        f"📊 Кол-во: {data.get('product_stock','0')}\n"
        f"📝 {message.text}",
        parse_mode="HTML"
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current = await state.get_state()
    if current:
        await state.clear()
        await message.answer("✅ Отменено.")

def register_user(user):
    """Регистрирует пользователя если его ещё нет."""
    if user.id not in shop_users:
        shop_users[user.id] = {
            "name": user.full_name,
            "username": user.username or "—",
            "join_time": time.strftime("%Y-%m-%d %H:%M")
        }
        save_db()

@dp.message(AdminStates.waiting_broadcast)
async def admin_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    sent = 0
    failed = 0
    for uid in list(shop_users.keys()):
        try:
            if message.photo:
                # Рассылка с фото
                await bot.send_photo(
                    uid,
                    photo=message.photo[-1].file_id,
                    caption=message.caption or "",
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(uid, message.text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Рассылка завершена!\n✉️ Отправлено: {sent}\n❌ Не доставлено: {failed}")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"🔨 <b>{target.full_name}</b> забанен.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    try:
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"✅ <b>{target.full_name}</b> разбанен.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("kick"))
async def cmd_kick(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"👟 <b>{target.full_name}</b> кикнут.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    args = message.text.split()
    minutes = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
    try:
        until = timedelta(minutes=minutes)
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await message.reply(f"🔇 <b>{target.full_name}</b> замьючен на {minutes} мин.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await message.reply(f"🔊 <b>{target.full_name}</b> размьючен.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("warn"))
async def cmd_warn(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    count = add_warn(message.chat.id, target.id)
    if count >= MAX_WARNS:
        try:
            await bot.ban_chat_member(message.chat.id, target.id)
            clear_warns(message.chat.id, target.id)
            await message.reply(
                f"⚠️ <b>{target.full_name}</b> получил {count}/{MAX_WARNS} варн и забанен!",
                parse_mode="HTML"
            )
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")
    else:
        await message.reply(
            f"⚠️ <b>{target.full_name}</b> варн: {count}/{MAX_WARNS}",
            parse_mode="HTML"
        )

@dp.message(Command("warns"))
async def cmd_warns(message: Message):
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    count = get_warns(message.chat.id, target.id)
    await message.reply(f"📋 <b>{target.full_name}</b> — варнов: {count}/{MAX_WARNS}", parse_mode="HTML")

@dp.message(Command("clearwarns"))
async def cmd_clearwarns(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответь на сообщение пользователя.")
        return
    target = message.reply_to_message.from_user
    clear_warns(message.chat.id, target.id)
    await message.reply(f"✅ Варны <b>{target.full_name}</b> сброшены.", parse_mode="HTML")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not await is_admin(message):
        await message.reply("🚫 Нет прав.")
        return
    count = await bot.get_chat_member_count(message.chat.id)
    chat = message.chat
    await message.reply(
        f"📊 <b>Статистика</b>\n\n"
        f"📌 Название: <b>{chat.title}</b>\n"
        f"👥 Участников: <b>{count}</b>\n"
        f"🆔 ID: <code>{chat.id}</code>",
        parse_mode="HTML"
    )

@dp.message(Command("id"))
async def cmd_id(message: Message):
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        await message.reply(f"🆔 <b>{target.full_name}</b>: <code>{target.id}</code>", parse_mode="HTML")
    else:
        await message.reply(f"🆔 Твой ID: <code>{message.from_user.id}</code>", parse_mode="HTML")

async def main():
    load_db()
    print("🤖 Бот запущен...")
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="admins", description="⚙️ Админ панель"),
        BotCommand(command="cancel", description="❌ Отмена"),
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
