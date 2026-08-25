import os
import sys
import threading
import asyncio
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# 1. Flask server (Render PORT uchun)
app = Flask(__name__)

@app.route("/")
def home():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. API Kalitlarni tekshirish
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_KEY:
    print("--> [XATO] BOT_TOKEN yoki GEMINI_API_KEY Environment variables qismida topilmadi!", flush=True)

try:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("--> Gemini AI muvaffaqiyatli sozlandi!", flush=True)
except Exception as e:
    print(f"--> [XATO] Gemini sozlanishida xato: {e}", flush=True)

SYSTEM_PROMPT = "Isming Nozima. Sobiq sinfdoshsan. Qisqa, samimiy va tez javob ber."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Boshladik! 😊")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip() if update.message and update.message.text else ""
    if not user_input:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = model.generate_content(f"{SYSTEM_PROMPT}\nFoydalanuvchi: {user_input}\nNozima:")
        ai_text = response.text.strip()
    except Exception as e:
        print(f"--> [XATO] Javob yaratishda xato: {e}", flush=True)
        ai_text = "Eshityapman, nimadir dedingmi? Qaytadan yozvorchi 😊"

    await update.message.reply_text(ai_text)

# 3. Asosiy ishga tushirish funksiyasi
async def main():
    print("--> Telegram Bot ishga tushmoqda...", flush=True)
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    async with bot_app:
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        print("--> BOT MUVAFFAQIYATLI ISHGA TUSHDI VA TINGLAMOQDA!", flush=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    # Flask veb-serverni alohida potokda yurgizish
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Telegram botni asyncio orqali ishga tushirish
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"--> [CRITICAL XATO]: {e}", flush=True)
