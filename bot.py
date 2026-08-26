import os
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Flask ilovasini yaratish (Render portni tinglashi uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live!"

# API kalitlarni muhitdan olish
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini AI sozlamasi
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Men AI yordamchisiman. Istalgan savolingizni yuborishingiz mumkin.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Telegram'da bot "yozmoqda..." holatini ko'rsatib turadi
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    ai_response = None
    
    # AI javob bergunicha 3 marta qayta urinib ko'radi (har biriga timeout qo'yilgan)
    for attempt in range(3):
        try:
            # AI so'roviga ko'proq vaqt beramiz (asyncio orqali)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: model.generate_content(user_text)
            )
            if response and response.text:
                ai_response = response.text
                break
        except Exception as e:
            print(f"--> [URINISH {attempt+1}] AI xatosi: {e}")
            await asyncio.sleep(2) # Qayta urinishdan oldin 2 soniya kutiladi

    # Agar AI javob bera olgan bo'lsa, o'shani yuboradi
    if ai_response:
        # Telegram xabar uzunligi chekloviga moslab bo'lib yuborish
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 4000):
                await update.message.reply_text(ai_response[i:i+4000])
        else:
            await update.message.reply_text(ai_response)
    else:
        await update.message.reply_text("Kechirasiz, AI javob tayyorlashda kechikish bo'ldi. Iltimos, xabaringizni qayta yuboring.")

def main():
    # Telegram botni sozlash
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Flask va Telegram botni birga ishga tushirish
    loop = asyncio.get_event_loop()
    loop.create_task(application.initialize())
    loop.create_task(application.start())
    loop.create_task(application.updater.start_polling())
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    main()
