import asyncio
import logging
import json
import os
import threading
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from flask import Flask

# .env dan o'qish
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6067594310"))

# Kanal va kino sozlamalari
CHANNELS = [
    {"link": "https://t.me/+0HH1L-dHrLdmMTUy", "id": -1003053807994},
    {"link": "https://t.me/+_tOVOccPH_cwMTcy", "id": -1002758258380},
    {"link": "https://t.me/+24H2NggcXrFmNjUy", "id": -1002976392716},
    {"link": "https://t.me/+nJuibwCPd0Q4NmE6", "id": -1002920857610}
]

MOVIES = {
    "2010": "BAACAgQAAxkBAAIC1GjO8vcO2unvwjQGnUm_uVHnKpwTAAJqEAAC7WLIUQguwgnEAztxNgQ",
    "2011": "BAACAgIAAxkBAAIC4WjO9Zbrfu4FJdH7MaZsktxziQcZAAJcSgACty1wS8guQ5LS8pvONgQ",
    "2012": "BAACAgIAAxkBAAIC42jO9ae2kmz4PsHy1pAIPUfQas-NAAKheAACAksYSmqKH9rzGwKINgQ",
    "2013": "BAACAgIAAxkBAAIC5WjO9eVOw-g_6-iJxGY1Bb3nMJSaAAKHeAACAksYSmsRnyamltIRNgQ",
    "2014": "BAACAgQAAxkBAAIC52jO9fXhrNZpZQMBlPos5Z_D5VezAAK2EwACNhm4U3EPtcMfg8DGNgQ",
    "2015": "BAACAgQAAxkBAAIC6WjO9gdBeFuHCGseYXcNLTqH_cKGAALmFQACFAKwU6u0VaAjFLZTNgQ",
    "2016": "BAACAgQAAxkBAAIC62jO9lU8haqvrf22ycA3UUJ-B1p0AALDFAACFAKoU1lCKeXYmOU8NgQ",
    "2017": "BAACAgIAAxkBAAIC7WjO9mXXhua2JLEz5gqVH22QTyN-AALECQACD26hSuwELeZvNazENgQ",
    "2018": "BAACAgIAAxkBAAIC72jO9nLnRkrhARD7tVrUxkAfs732AAJtHgACbiGQS87F6MIjcC1LNgQ",
    "2019": "BAACAgIAAxkBAAIC8WjO9n1mEKg4GMkoLNITPThCDiiyAAK6SQAC_BdYSA38_PngLAmXNgQ",
    "2020": "BAACAgIAAxkBAAIC82jO9orOOqmR9rd6XQG_4RWlzctQAALpCQACy5koSl5i8GnIFuWVNg",
    "2021": "BAACAgIAAxkBAAIC9WjO9pVmy2UaJQzP6RpCjnqTI6coAAI6PgACoJuZSh7vxJcLs5XDNgQ"
}

PENDING_FILE = "pending.json"

# Bot & dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# FSM
class CinemaStates(StatesGroup):
    waiting_for_code = State()

# Pending faylni yuklash/saqlash
def load_pending():
    if not os.path.exists(PENDING_FILE):
        return {}
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"load_pending error: {e}")
        return {}

def save_pending(data):
    try:
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"save_pending error: {e}")

# /start handler — kanal linklarini chiqaradi
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    pending = load_pending()

    if pending.get(user_id) == "confirmed":
        await message.answer("✅ Siz allaqachon tasdiqlangansiz! Kino kodini yuboring:")
        await state.set_state(CinemaStates.waiting_for_code)
        return

    text = "🎬 Assalomu alaykum!\n\nQuyidagi 4 ta kanallarga *Join Request* yuboring:\n\n"
    for ch in CHANNELS:
        text += f"➡️ {ch['link']}\n"
    text += "\nSo‘ngra pastdagi tugmani bosing:"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Men obuna bo‘ldim", callback_data="confirmed_request")]
    ])

    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

# chat_join_request event — foydalanuvchi kanallardan biriga join request yuborganda ishlaydi
@dp.chat_join_request()
async def on_chat_join_request(update: types.ChatJoinRequest):
    uid = str(update.from_user.id)
    pending = load_pending()
    # agar birinchi martasi bo'lsa, ro'yxatga qo'shamiz
    # biz faqat "joined" flag qo'yamiz; hamma kanallarga join request berilganini tekshirish callbackda qilamiz
    pending.setdefault(uid, {})["joined_any"] = True
    save_pending(pending)
    # adminga xabar (ixtiyoriy)
    try:
        await bot.send_message(ADMIN_ID, f"📥 Join request: {update.from_user.full_name} ({uid})")
    except Exception:
        pass

# Obuna tekshirish tugmasi bosilganda — hamma kanallarga join request yuborilganmi tekshiramiz
@dp.callback_query(F.data == "confirmed_request")
async def confirmed_request(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_key = str(user_id)

    # tekshirish: har bir kanal bo'yicha get_chat_member, agar status "left" bo'lsa -> join request ham bo'lmagan
    not_requested = []
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch["id"], user_id)
            # agar user join request yuborgan lekin hali qabul qilinmagan bo'lsa — Telegram API ba'zan status "left" qaytaradi,
            # shuning uchun biz ham chat_join_request orqali hamma joinlarni pending.json ga yozishni talab qilamiz.
            if member.status == "left":
                # left => hali a'zo emas. lekin bu holda ham foydalanuvchi join request yuborgan bo'lishi mumkin;
                # biz join_request event bilan solishtiramiz: pending faylda uid mavjud bo'lsa, join request yuborgan deb hisoblaymiz.
                pending = load_pending()
                if pending.get(user_key) and pending[user_key].get("joined_any"):
                    # join_request event kelgan — demak u join request yuborgan, qabul qilinmagan
                    continue
                not_requested.append(ch["link"])
        except Exception:
            # agar get_chat_member xato bersa, shuni ham not_requested ga qo'shamiz
            not_requested.append(ch["link"])

    if not_requested:
        text = "❌ Siz quyidagi kanallarga hali *Join Request* yubormagansiz yoki bot ularni tekshira olmadi:\n\n"
        for l in not_requested:
            text += f"➡️ {l}\n"
        text += "\nIltimos, har bir kanalga Join Request yuboring (yoki agar private kanal bo'lsa — invite linkdan)."
        await callback.answer()  # callbackni bekor qilamiz
        await callback.message.edit_text(text, reply_markup=callback.message.reply_markup, parse_mode="Markdown")
        return

    # agar hamma kanallarga join_request yuborgan bo'lsa (yoki bot ularni a'zo deb topgan bo'lsa)
    pending = load_pending()
    pending[user_key] = {"confirmed": True}
    save_pending(pending)

    await callback.message.edit_text("✅ Tabriklaymiz! Hammasiga Join Request yubordingiz — endi /code buyrug'ini yozib, kinoning kodini yuboring.")
    await state.set_state(CinemaStates.waiting_for_code)

# Kino kodi qabul qilish
@dp.message(CinemaStates.waiting_for_code)
async def receive_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    user_key = str(message.from_user.id)
    pending = load_pending()

    if pending.get(user_key) and pending[user_key].get("confirmed"):
        if code in MOVIES:
            file_id = MOVIES[code]
            await message.answer_document(file_id)
            await bot.send_message(ADMIN_ID, f"🎬 Kino yuborildi: {message.from_user.full_name} ({user_key}) -> kod {code}")
            await state.clear()
            return
        else:
            await message.answer("❌ Noto‘g‘ri kod! Iltimos, 2010–2021 orasidan birini yozing.")
            return
    else:
        await message.answer("⚠️ Avval barcha kanallarga Join Request yuboring va 'Men obuna bo'ldim' tugmasini bosing.")

# Flask health-check (Render Web Service talab qiladi)
app = Flask("bot_health")

@app.route("/")
def home():
    return "OK - bot ishlayapti"

def run_flask():
    port = int(os.getenv("PORT", "5000"))
    # Bind 0.0.0.0 shart — Render kerakli portni tekshiradi
    app.run(host="0.0.0.0", port=port)

# Bot polling run
async def run_bot():
    logging.info("Start polling")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Flaskni alohida threadda ishga tushiramiz (port 5000 yoki Render PORT)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Keyin asyncio loopda botni ishga tushiramiz
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
