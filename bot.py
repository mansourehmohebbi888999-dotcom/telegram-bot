import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# توکن بات شما
API_TOKEN = "9180963261:AAFXffxf_X_-edaEXX-HkZQ2KUYxi9_lJxI"

# آیدی عددی گروه ادمین‌ها
ADMIN_GROUP_ID = -1001234567890  # آیدی گروه ادمین‌های خود را اینجا بگذارید

# آیدی کانال اصلی شما
CHANNEL_USERNAME = "@parham67nig"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class WithdrawStates(StatesGroup):
    waiting_for_post = State()
    waiting_for_count = State()
    waiting_for_gift_username = State()

# --- راه‌اندازی دیتابیس ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            stars INTEGER DEFAULT 0,
            invites_count INTEGER DEFAULT 0,
            referred_by INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- بررسی عضویت در کانال ---
async def check_channel_membership(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception as e:
        print(f"خطا در بررسی عضویت: {e}")
    return False

# --- شروع و سیستم دعوت ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    
    is_member = await check_channel_membership(user_id)
    if not is_member:
        join_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💎 ➔ ورود به کانال VIP", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
                [types.InlineKeyboardButton(text="✨ ➔ تایید عضویت (Verify)", callback_data="check_membership")]
            ]
        )
        await message.answer(
            f"✨ **به درگاه انحصاری و VIP ما خوش آمدید** ✨\n\n"
            f"🔒 برای استفاده از بات، شما باید حتماً در کانال ما عضو باشید:\n"
            f"👉 {CHANNEL_USERNAME}\n\n"
            f"⚠️ **نکته مهم:** اگر از قبل عضو هستید، لطفاً یک‌بار لفت بدهید (Leave) و دوباره جوین شوید، سپس روی دکمه‌ی «تایید عضویت» کلیک کنید.",
            reply_markup=join_kb
        )
        return

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        if referrer_id and referrer_id != user_id:
            referrer_in_channel = await check_channel_membership(referrer_id)
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
            if cursor.fetchone() and referrer_in_channel:
                # تغییر مقدار جایزه به 3 ستاره
                cursor.execute("""
                    UPDATE users 
                    SET stars = stars + 3, invites_count = invites_count + 1 
                    WHERE user_id = ?
                """, (referrer_id,))
                
                cursor.execute("""
                    INSERT INTO users (user_id, username, stars, invites_count, referred_by) 
                    VALUES (?, ?, 0, 0, ?)
                """, (user_id, username, referrer_id))
                
                try:
                    await bot.send_message(
                        referrer_id, 
                        "🌟 **تبریک!** یک دوست با لینک دعوت شما وارد بات شد و عضو کانال گردید.\n⭐ `+3 stars` به حساب شما واریز شد."
                    )
                except:
                    pass
            else:
                cursor.execute("INSERT INTO users (user_id, username, stars, invites_count) VALUES (?, ?, 0, 0)", (user_id, username))
        else:
            cursor.execute("INSERT INTO users (user_id, username, stars, invites_count) VALUES (?, ?, 0, 0)", (user_id, username))
            
        conn.commit()

    conn.close()

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="💎 لینک دعوت من"), types.KeyboardButton(text="💼 موجودی من")],
            [types.KeyboardButton(text="🎁 برداشت / Withdraw")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "👑 **پنل کاربری اختصاصی شما** 👑\n\n"
        "از طریق گزینه‌های زیر می‌توانید بخش‌های مختلف را مدیریت کنید:",
        reply_markup=keyboard
    )

# --- تایید عضویت ---
@dp.callback_query(F.data == "check_membership")
async def verify_membership(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_member = await check_channel_membership(user_id)
    
    if is_member:
        await callback.message.answer("🌟 **عضویت شما با موفقیت تایید شد!**\n\nلطفاً برای شروع دستور `/start` را ارسال کنید.")
    else:
        await callback.message.answer(
            "❌ **خطا:** شما هنوز در کانال عضو نیستید!\n"
            "⚠️ ابتدا در کانال join شوید و در صورت لزوم یک‌بار لفت/جوین کنید."
        )
    await callback.answer()

# --- لینک دعوت ---
@dp.message(F.text == "💎 لینک دعوت من")
async def get_referral_link(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    await message.answer(
        f"💎 **سیستم افزایش ستاره (مجموعه دعوت)**\n\n"
        f"🔗 لینک اختصاصی شما:\n`{ref_link}`\n\n"
        f"📌 **راهنمای مهم:**\n"
        f"• شما و دوستانتان باید **حتماً** در کانال {CHANNEL_USERNAME} عضو باشید.\n"
        f"• این لینک را برای دوستان خود بفرستید.\n"
        f"• به ازای هر شخصی که با لینک شما وارد بات شود و در کانال {CHANNEL_USERNAME} عضو شود، **3 stars** به صورت اتوماتیک به حساب شما اضافه می‌شود."
    )

# --- موجودی من ---
@dp.message(F.text == "💼 موجودی من")
async def check_balance(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT stars, invites_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    stars = row[0] if row else 0
    invites = row[1] if row else 0
    
    await message.answer(
        f"💼 **گذرنامه و موجودی حساب:**\n\n"
        f"⭐ موجودی Stars: **{stars}** عدد\n"
        f"👥 تعداد دعوت‌های موفق: **{invites}** نفر"
    )

# --- منوی برداشت ---
@dp.message(F.text == "🎁 برداشت / Withdraw")
async def withdraw_menu(message: types.Message):
    inline_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="⭐ سفارش ری‌اکشن VIP", callback_data="order_reaction")],
            [types.InlineKeyboardButton(text="🎁 سفارش گیفت تلگرام", callback_data="order_gift_menu")]
        ]
    )
    await message.answer(
        "✨ **بخش استفاده از Stars (برداشت و تبادل)** ✨\n\n"
        "لطفاً یکی از خدمات لوکس زیر را انتخاب کنید:",
        reply_markup=inline_kb
    )

# --- سفارش ری‌اکشن ---
@dp.callback_query(F.data == "order_reaction")
async def process_reaction_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 **لطفاً لینک پست موردنظر خود را ارسال کنید یا پست را همین‌جا Forward کنید.**"
    )
    await state.set_state(WithdrawStates.waiting_for_post)
    await callback.answer()

@dp.message(WithdrawStates.waiting_for_post)
async def receive_post(message: types.Message, state: FSMContext):
    await state.update_data(post_message=message)
    
    await message.answer(
        "🔥 **پست شما با موفقیت دریافت شد!**\n\n"
        "🎯 حالا چند `stars` برای این پست ری‌اکشن می‌خواهید؟ (فقط عدد وارد کنید)"
    )
    await state.set_state(WithdrawStates.waiting_for_count)

@dp.message(WithdrawStates.waiting_for_count)
async def receive_count(message: types.Message, state: FSMContext):
    try:
        requested_stars = int(message.text)
    except ValueError:
        await message.answer("❌ لطفاً فقط یک عدد معتبر وارد کنید:")
        return

    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_stars = row[0] if row else 0

    if requested_stars <= 0:
        await message.answer("❌ مقدار باید بزرگ‌تر از صفر باشد.")
        conn.close()
        return

    if current_stars < requested_stars:
        await message.answer(
            f"❌ **موجودی کافی نیست!**\n\n"
            f"⭐ موجودی فعلی: {current_stars} stars\n"
            f"🎯 درخواست شما: {requested_stars} stars"
        )
        conn.close()
        return

    new_stars = current_stars - requested_stars
    cursor.execute("UPDATE users SET stars = ? WHERE user_id = ?", (new_stars, user_id))
    conn.commit()
    conn.close()

    data = await state.get_data()
    post_msg: types.Message = data.get("post_message")

    await message.answer(
        f"⚡️ **سفارش شما با موفقیت ثبت شد!** 🚀\n\n"
        f"🎯 تعداد: {requested_stars} stars\n"
        f"💰 موجودی جدید: **{new_stars} stars**\n\n"
        f"✨ به زودی اعمال خواهد شد."
    )

    try:
        await bot.send_message(
            ADMIN_GROUP_ID,
            f"🔔 **سفارش جدید ری‌اکشن!**\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"⭐ تعداد: {requested_stars} stars"
        )
        if post_msg:
            await post_msg.forward(ADMIN_GROUP_ID)
    except Exception as e:
        print(f"Error: {e}")

    await state.clear()

# --- منوی گیفت‌های تلگرام ---
@dp.callback_query(F.data == "order_gift_menu")
async def gift_menu(callback: types.CallbackQuery):
    gift_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="💖 قلب (Heart) - 15 stars", callback_data="buy_gift_15_heart"),
             types.InlineKeyboardButton(text="🧸 خرس (Teddy) - 15 stars", callback_data="buy_gift_15_bear")],
            [types.InlineKeyboardButton(text="🎁 جعبه هدیه - 25 stars", callback_data="buy_gift_25_box"),
             types.InlineKeyboardButton(text="🌹 رز قرمز - 25 stars", callback_data="buy_gift_25_rose")],
            [types.InlineKeyboardButton(text="🎂 کیک تولد - 50 stars", callback_data="buy_gift_50_cake"),
             types.InlineKeyboardButton(text="💐 دسته‌گل - 50 stars", callback_data="buy_gift_50_flowers")],
            [types.InlineKeyboardButton(text="🚀 موشک - 50 stars", callback_data="buy_gift_50_rocket"),
             types.InlineKeyboardButton(text="🍾 شامپاین - 50 stars", callback_data="buy_gift_50_champagne")],
            [types.InlineKeyboardButton(text="🏆 کاپ طلا - 100 stars", callback_data="buy_gift_100_trophy"),
             types.InlineKeyboardButton(text="💍 انگشتر - 100 stars", callback_data="buy_gift_100_ring")],
            [types.InlineKeyboardButton(text="💎 الماس - 100 stars", callback_data="buy_gift_100_diamond")]
        ]
    )
    await callback.message.answer(
        "🎁 **کاتالوگ گیفت‌های VIP تلگرام:**\n\n"
        "لطفاً هدیه مورد نظر خود را انتخاب کنید:",
        reply_markup=gift_kb
    )
    await callback.answer()

# --- انتخاب گیفت ---
@dp.callback_query(F.data.startswith("buy_gift_"))
async def process_gift_selection(callback: types.CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    gift_cost = int(data_parts[2])
    gift_name = "_".join(data_parts[3:])

    user_id = callback.from_user.id

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_stars = row[0] if row else 0

    if current_stars < gift_cost:
        await callback.message.answer(
            f"❌ **موجودی کافی نیست!**\n\n"
            f"⭐ موجودی فعلی: {current_stars} stars\n"
            f"🎁 هزینه هدیه: {gift_cost} stars"
        )
        conn.close()
        await callback.answer()
        return

    await state.update_data(gift_name=gift_name, gift_cost=gift_cost)
    await callback.message.answer(
        f"✅ هدیه `{gift_name}` با ارزش `{gift_cost} stars` انتخاب شد.\n\n"
        "💬 **لطفاً یوزرنیم (Username) تلگرام خود را وارد کنید (مثلاً: `@username`):**"
    )
    await state.set_state(WithdrawStates.waiting_for_gift_username)
    await callback.answer()

# --- دریافت یوزرنیم و ثبت سفارش گیفت ---
@dp.message(WithdrawStates.waiting_for_gift_username)
async def receive_gift_username(message: types.Message, state: FSMContext):
    target_username = message.text
    user_id = message.from_user.id

    data = await state.get_data()
    gift_name = data.get("gift_name")
    gift_cost = data.get("gift_cost")

    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_stars = row[0] if row else 0

    if current_stars < gift_cost:
        await message.answer("❌ موجودی کافی نیست.")
        conn.close()
        await state.clear()
        return

    new_stars = current_stars - gift_cost
    cursor.execute("UPDATE users SET stars = ? WHERE user_id = ?", (new_stars, user_id))
    conn.commit()
    conn.close()

    await message.answer(
        f"⚡️ **سفارش هدیه با موفقیت ثبت شد!** 🚀\n\n"
        f"🎁 هدیه: {gift_name}\n"
        f"🎯 هزینه: {gift_cost} stars\n"
        f"💰 موجودی جدید: **{new_stars} stars**\n\n"
        f"✨ به زودی ارسال خواهد شد."
    )

    try:
        await bot.send_message(
            ADMIN_GROUP_ID,
            f"🔔 **سفارش جدید گیفت تلگرام!**\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"🎯 Target Username: {target_username}\n"
            f"🎁 Gift: {gift_name} ({gift_cost} stars)"
        )
    except Exception as e:
        print(f"Error: {e}")

    await state.clear()

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))    asyncio.run(dp.start_polling(bot))
