import os
import threading
import urllib.parse
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, BotCommand
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

# 1. FLASK (Render uchun orqa fonda)
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

# Bir nechta muqobil modellarni ko'rsatamiz
MODELS_TO_TRY = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]

def generate_ai_response(prompt_text):
    """
    Agarda birorta model 404 xatosi bersa, avtomatik keyingi ishlaydigan modelga o'tadi.
    """
    for model_name in MODELS_TO_TRY:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SINFDOSH_PERSONA
            )
            response = model.generate_content(prompt_text)
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"[{model_name}] modelida xatolik: {e}")
            continue
    return "Kechirasiz, hozircha sun'iy intellekt javob bera olmadi. Birozdan keyin urinib ko'ring."

# 3. TUGMALAR SOTIROVI
main_keyboard = ReplyKeyboardMarkup(
    [["🎨 Rasm chizish"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_my_commands([
        BotCommand("start", "Botni qayta ishga tushirish"),
        BotCommand("draw", "Rasm chizish: /draw rasm ta'rifi")
    ])
    
    welcome_text = (
        "Ooo, salom sinfdosh! 🖐\n\n"
        "Men bilan bemalol gaplashishing mumkin. Rasm chizdirish uchun pastdagi **'🎨 Rasm chizish'** "
        "tugmasini bos yoki `/draw matn` deb yubor!"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_keyboard)

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

    # "🎨 Rasm chizish" tugmasi bosilganda
    if user_text == "🎨 Rasm chizish":
        context.user_data['waiting_for_photo'] = True
        await update.message.reply_text("Nimaning rasmini chizib beray? Promptni yozib yubor (Masalan: *Kosmosdagi tayyora*):", parse_mode="Markdown")
        return

    # Avval tugma bosilib, keyin rasm ta'rifi yuborilganda
    if context.user_data.get('waiting_for_photo'):
        context.user_data['waiting_for_photo'] = False
        context.args = user_text.split()
        await generate_image(update, context)
        return

    # AI bilan suhbat
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        ai_reply = generate_ai_response(user_text)
        await update.message.reply_text(ai_reply)
    except Exception as e:
        print(f"Umumiy xato: {e}")
        await update.message.reply_text("Biroz qotib qoldim, sal turib qayta yoz.")

# 4. ISHGA TUSHIRISH
def main():
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("draw", generate_image))
    application.add_handler(CommandHandler("image", generate_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("--> BOT SHAXSIY REJIMDA ISHGA TUSHDI!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
