import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv

# 🔐 .env fayldan ma'lumotlarni yuklash
load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID", "6067594310"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🎬 Kino kodlari (file_id)
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

# 📢 Obuna bo‘lishi kerak bo‘lgan kanallar
CHANNELS = [
    {"link": "https://t.me/+0HH1L-dHrLdmMTUy", "id": -1003053807994},
    {"link": "https://t.me/+_tOVOccPH_cwMTcy", "id": -1002758258380},
    {"link": "https://t.me/+24H2NggcXrFmNjUy", "id": -1002976392716},
    {"link": "https://t.me/+nJuibwCPd0Q4NmE6", "id": -1002920857610}
]

PENDING_FILE = "pending.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


# 📌 Kino olish uchun holatlar
class CinemaStates(StatesGroup):
    waiting_for_code = State()


# 📁 Pending foydalanuvchilarni o‘qish
def load_pending():
    if not os.path.exists(PENDING_FILE):
        return {}
    try:
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Pending faylni o‘qishda xatolik: {e}")
        return {}


# 📁 Pending foydalanuvchilarni saqlash
def save_pending(data):
    try:
        with open(PENDING_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"Pending faylni yozishda xatolik: {e}")


# 🔘 Obunani tekshirish
async def check_subscriptions(user_id: int) -> bool:
    try:
        for ch in CHANNELS:
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception as e:
        logging.error(f"Obunani tekshirishda xatolik: {e}")
        return False


# 🔘 Start komandasi
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    pending = load_pending()

    if pending.get(user_id) == "confirmed":
        await message.answer("✅ Siz allaqachon tasdiqlangansiz! Kino kodini yuboring:")
        await state.set_state(CinemaStates.waiting_for_code)
    else:
        text = f"🎬 Assalomu alaykum, {message.from_user.full_name}!\n\n"
        text += "Kino olish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
        for ch in CHANNELS:
            text += f"👉 {ch['link']}\n"
        text += "\nSo‘ngra «✅ Men obuna bo‘ldim» tugmasini bosing."

        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Men obuna bo‘ldim", callback_data="confirmed_request")]]
        )

        await message.answer(text, reply_markup=markup)


# 🔘 Kino kodi yuborish
@dp.message(CinemaStates.waiting_for_code)
async def code_handler(message: types.Message, state: FSMContext):
    code = message.text.strip()
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    if code in MOVIES:
        file_id = MOVIES[code]
        await message.answer_document(file_id)
        await bot.send_message(ADMIN_ID, f"🎬 Kino yuborildi: {user_name} ({user_id}) -> kod {code}")
        await state.clear()
    else:
        await message.answer("❌ Noto‘g‘ri kod! Iltimos, qayta urinib ko‘ring.")


# 🔘 "Men obuna bo‘ldim" tugmasi
@dp.callback_query(F.data == "confirmed_request")
async def confirm_subscription(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    user_name = callback.from_user.full_name

    if await check_subscriptions(callback.from_user.id):
        pending = load_pending()
        pending[user_id] = "confirmed"
        save_pending(pending)

        await callback.message.edit_text("✅ Obuna tasdiqlandi! Endi kino kodini yuboring:")
        await bot.send_message(ADMIN_ID, f"🟢 Yangi foydalanuvchi tasdiqlandi: {user_name} ({user_id})")
        await state.set_state(CinemaStates.waiting_for_code)
    else:
        await callback.answer("❌ Hali hamma kanallarga obuna bo‘lmadingiz!", show_alert=True)


# 🚀 Botni ishga tushirish
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot ishida xatolik: {e}")


if __name__ == "__main__":
    asyncio.run(main())
