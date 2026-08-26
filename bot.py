import os
import threading
import urllib.parse
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# =====================================================================
# SINFDOSH PROMPTI
# =====================================================================
SINFDOSH_PERSONA = """
Sizning ismingiz Nozima. Siz foydalanuvchining yaqin sinfdosh qiz do'stisiz.
O'zbekcha, samimiy, do'stona, biroz sho'x va hazilkash gapiring.
Rasmiy jargonlar ishlatmang va sinfdosh ro'lidan chiqmang!
"""

# 1. FLASK (ORQA FONDA ISHLAYDIGAN QILAMIZ)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: ONLINE"

def start_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. BOT VA GEMINI SOZLAMALARI
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SINFDOSH_PERSONA
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ooo, salom sinfdosh! 🖐\n\nRasm kerak bo'lsa `/draw rasm ta'rifi` deb yubor.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Nimaning rasmini chizay? Masalan: `/draw Cyberpunk city`")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_msg = await update.message.reply_text("Hozir, zo'r rasm chizaman...")

    try:
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        await update.message.reply_photo(photo=image_url, caption=f"Mana: {prompt}")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text("Rasm chizishda xatolik bo'ldi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = model.generate_content(user_text)
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("Tushunmadim, qayta yozvor-chi?")
    except Exception as e:
        await update.message.reply_text("Biroz qotib qoldim, sal turib qayta yoz.")

# 3. ISHGA TUSHIRISH
def main():
    # Flask'ni alohida Thread (oqim)da fonda yurgazamiz:
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    # Telegram Botni asosiy oqimda ishga tushiramiz:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("draw", generate_image))
    application.add_handler(CommandHandler("image", generate_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("--> BOT SHAXSIY REJIMDA ISHGA TUSHDI!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
