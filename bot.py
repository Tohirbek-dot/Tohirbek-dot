import os
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import types

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Muhit o'zgaruvchilari (Environment Variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 1. FLASK SERVER (Render portini ushlab turish uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# 2. GEMINI CLIENT SOZLAMASI
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def ask_gemini(user_text: str) -> str:
    if not gemini_client:
        return "Gemini API kaliti sozlanmagan."
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_text,
            config=types.GenerateContentConfig(
                temperature=0.7,
            )
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini API xatoligi: {e}")
        return "Kechirasiz, javob berishda xatolik yuz berdi."


# 3. TELEGRAM BOT HANDLERLARI
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Assalomu alaykum, {user_name}! Men sun'iy intellekt botiman. "
        f"Menga savolingizni yuboring yoki rasm chizish uchun `/image tavsif` deb yozing."
    )

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Iltimos, rasm tavsifini kiriting. Masalan:\n`/image uzbekistan nature`", parse_mode="Markdown")
        return

    prompt = " ".join(context.args)
    await update.message.reply_text("🎨 Rasm tayyorlanmoqda, kuting...")

    # Pollinations AI orqali rasm URL yaratish
    image_url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1024&height=1024&seed=42"

    try:
        await update.message.reply_photo(photo=image_url, caption=f"🖼 Prompt: {prompt}")
    except Exception as e:
        logging.error(f"Rasm yuborishda xatolik: {e}")
        await update.message.reply_text("Rasm yaratishda xatolik yuz berdi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Telegram "typing..." statusini ko'rsatish
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    reply_text = ask_gemini(user_text)
    await update.message.reply_text(reply_text)


# 4. ASOSIY ISHGA TUSHIRISH
def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN topilmadi! Render Environment Variables qismini teshiring.")
        return

    # Flask serverni alohida thread'da ishga tushirish
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask veb-server ishga tushirildi.")

    # Telegram botni sozlash
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Botni polling rejimida ishga tushirish (drop_pending_updates=True eski konfliktlarni tozalaydi)
    logging.info("Telegram Bot ishga tushmoqda...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
