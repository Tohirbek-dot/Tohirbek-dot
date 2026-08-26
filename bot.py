import os
import threading
import urllib.parse
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# =====================================================================
# 🛠 SHU YERDAGI MATNNI KEYIN GITHUB'DA XO'SHLAGANDAY O'ZGARTIRASIZ
# =====================================================================
SINFDOSH_PERSONA = """
Sizning ismingiz Nozima. Siz foydalanuvchining yaqin sinfdosh qiz do'stisiz.
Muloqot uslubingiz:
- O'zbekcha, judayam samimiy, do'stona, biroz sho'x va hazilkash.
- Do'stona munosabatda bo'ling, "xo'p bo'ladi", "albatta", "do'stim" degan so'zlarni erkin ishlating.
- Rasmiy jargonlar yoki AI kabi sovuq javob bermang.
- Doimo sinfdosh qiz rolida qoling, xuddi maktabda birga o'qigan yaqin do'stingizdek gaplashing.
"""
# =====================================================================

# 1. Flask serverini sozlash (Render uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: ONLINE"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. API Kalitlar va Gemini AI
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SINFDOSH_PERSONA
)

# 3. Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "Ooo, salom! Nima gaplar sinfdosh? 🖐\n\n"
        "Yozib turgangingdan xursandman. Biror narsa haqida gaplashamizmi yoki rasm chizib beraymi?\n"
        "• **Rasm kerak bo'lsa:** `/draw rasm ta'rifi` deb yubor."
    )
    await update.message.reply_text(welcome)

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Nimaning rasmini chizay? Promptni ham yoz-da! Masalan: `/draw Cyberpunk city`")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_msg = await update.message.reply_text("Hozir, zo'r rasm chizib beraman...")

    try:
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        await update.message.reply_photo(
            photo=image_url,
            caption=f"Mana so'ragan rasming! 🎨\n**Prompt:** {prompt}",
            parse_mode="Markdown"
        )
        await status_msg.delete()
    except Exception as e:
        print(f"Rasm xatosi: {e}")
        await status_msg.edit_text("Voy, rasmda nimadir o'xshamay qoldi, qayta urinib ko'raylik-chi?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = model.generate_content(user_text)
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("Tushunmay qoldim, qayta yozvor-chi?")
    except Exception as e:
        print(f"AI xatosi: {e}")
        await update.message.reply_text("Biroz qotib qoldim, sal turib qayta yoz.")

# 4. Asosiy ishga tushirish qismi
def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("draw", generate_image))
    application.add_handler(CommandHandler("image", generate_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("--> NOZIMA BOT ISHGA TUSHDI!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
