import os
import threading
import urllib.parse
import urllib.request
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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

# 2. TELEGRAM TOKEN
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")

def generate_ai_response(prompt_text):
    try:
        # Prompt va xarakterni aniq ajratib yuboramiz
        full_prompt = f"System: {SINFDOSH_PERSONA}\nUser: {prompt_text}\nNozima:"
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        # Sekinlashib qolmasligi uchun modelni aniq ko'rsatamiz (openai modeli o'rnida)
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&cache=true"
        
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        # Timeout vaqtini oshiramiz (30 soniya)
        with urllib.request.urlopen(req, timeout=30) as response:
            res_text = response.read().decode('utf-8')
            if res_text and len(res_text.strip()) > 0:
                return res_text.strip()
    except Exception as e:
        print(f"AI ulanish xatosi: {e}")
    
    return "Hozir internetim biroz qotib qoldi, yana bir marta yozvor-chi? 😅"

# 3. TUGMALAR SOZLAMASI
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
    status_msg = await update.message.reply_text("Hozir, yuqori sifatli rasm chizaman, biroz kuting...")

    try:
        # Rasmlar tiniq va 4K formatda chiqishi uchun qo'shimcha parametrlar
        enhanced_prompt = f"{prompt}, highly detailed, 4k, sharp focus, professional lighting"
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&enhance=true"
        
        await update.message.reply_photo(photo=image_url, caption=f"Mana: {prompt}")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text("Rasm chizishda xatolik bo'ldi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if user_text == "🎨 Rasm chizish":
        context.user_data['waiting_for_photo'] = True
        await update.message.reply_text("Nimaning rasmini chizib beray? Promptni yozib yubor (Masalan: *Kosmosdagi tayyora*):", parse_mode="Markdown")
        return

    if context.user_data.get('waiting_for_photo'):
        context.user_data['waiting_for_photo'] = False
        context.args = user_text.split()
        await generate_image(update, context)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    ai_reply = generate_ai_response(user_text)
    await update.message.reply_text(ai_reply)

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
