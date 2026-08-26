import os
import threading
import urllib.parse
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# =====================================================================
# 🛠 GITHUB'DA SHU YERNI O'ZINGIZ XO'SHLAGANDAY TAHRIRLAYSINGIZ (PROMPT)
# =====================================================================
SINFDOSH_PERSONA = """
Siz mening yaqin sinfdoshim va do'stim qiyofasidasiz. 
Gapirish uslubingiz: 
- O'zbekcha, samimiy, do'stona, biroz hazilkash va erkin (do'stona jargonlar ishlatsangiz bo'ladi).
- Rasmiy gapirmang, o'zingizni xuddi maktabdosh/sinfdosh do'stimdek tuting.
- Har qanday savolga javob berayotganda shu sinfdosh obrazidan zarracha ham chiqmang!
"""
# =====================================================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: ONLINE"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

# AI modelini sinfdosh prompti (system_instruction) bilan sozlaymiz
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SINFDOSH_PERSONA
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "Ooo, salom jo'ra! Nima gaplar? 🖐\n\n"
        "Men tayyorman. Gaplashamizmi yoki biror narsa chizib beraymi?\n"
        "• **Rasm kerak bo'lsa:** `/draw rasm ta'rifi` deb yubor."
    )
    await update.message.reply_text(welcome)

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Nimaning rasmini chizay? Promptni ham yoz-da! Masalan: `/draw futuristic city`")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_msg = await update.message.reply_text("Hozir, do'stim, zo'r rasm chizib beraman...")

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
        await status_msg.edit_text("Aka, rasm chizishda nimadir o'xshamay qoldi. Qaytadan urinib ko'raylik-chi?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = model.generate_content(user_text)
        if response and response.text:
            ai_text = response.text
            if len(ai_text) > 4000:
                for i in range(0, len(ai_text), 4000):
                    await update.message.reply_text(ai_text[i:i+4000])
            else:
                await update.message.reply_text(ai_text)
        else:
            await update.message.reply_text("Tushunmay qoldim, qaytadan yozib yubor-chi?")
    except Exception as e:
        print(f"AI Xatoligi: {e}")
        await update.message.reply_text("Biroz qotib qoldim, sal turib qayta yozvor.")

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("draw", generate_image))
    application.add_handler(CommandHandler("image", generate_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("--> BOT SINFDOSH RO'LIDA ISHGA TUSHDI!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
