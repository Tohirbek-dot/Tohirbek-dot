import os
import threading
import urllib.parse
import urllib.request
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# =====================================================================
# SINFDOSH NOZIMA PROMPTI (Erkin suhbat va ko'p qirrali yordamchi)
# =====================================================================
SINFDOSH_PERSONA = """
Sizning ismingiz Nozima. Siz foydalanuvchining yaqin, samimiy va sho'x sinfdosh qiz do'stisiz.
- O'zbek tilida do'stona, samimiy va erkin gapiring.
- Foydalanuvchi bilan har qanday mavzuda (kun tartibi, darslar, kayfiyat, hayotiy maslahatlar, ingliz tilida mashq qilish) suhbatlashing.
- Rasmiy jargonlar ishlatmang, kitobiy gapirmang va sinfdosh ro'lidan chiqib ketmang.
- Doim kayfiyatni ko'taruvchi va samimiy javoblar bering.
"""

# 1. FLASK (Render uxlab qolmasligi uchun)
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
    """
    Pollinations AI orqali har qanday mavzuda erkin va qotmaydigan suhbat
    """
    try:
        full_prompt = f"System: {SINFDOSH_PERSONA}\nUser: {prompt_text}\nNozima:"
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&cache=true"
        
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
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
        "Men bilan bemalol istalgan mavzuda gaplashishing mumkin! 😊\n"
        "Rasm chizdirish uchun esa pastdagi **'🎨 Rasm chizish'** "
        "tugmasini bos yoki `/draw matn` deb yubor!"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_keyboard)

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Nimaning rasmini chizay? Masalan: `/draw Oy` yoki `/draw Koinotdagi mushuk`")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_msg = await update.message.reply_text("Hozir, so'ragan rasmingni tiniq qilib chizaman, biroz kut...")

    try:
        # Promptni inglizcha sifat so'zlari bilan boyitish va FLUX modelidan foydalanish
        enhanced_prompt = f"{prompt}, highly detailed, 4k photo, realistic, sharp focus, cinematic lighting"
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&enhance=true&model=flux"
        
        await update.message.reply_photo(photo=image_url, caption=f"Mana so'ragan rasming: {prompt}")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text("Rasm chizishda xatolik bo'ldi, qaytadan urinib ko'r-chi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # "🎨 Rasm chizish" tugmasi bosilganda
    if user_text == "🎨 Rasm chizish":
        context.user_data['waiting_for_photo'] = True
        await update.message.reply_text("Nimaning rasmini chizib beray? Yozib yubor (Masalan: *Oy*, *Dengiz bo'yidagi mashina*):", parse_mode="Markdown")
        return

    # Avval tugma bosilib, keyin rasm ta'rifi kelganda
    if context.user_data.get('waiting_for_photo'):
        context.user_data['waiting_for_photo'] = False
        context.args = user_text.split()
        await generate_image(update, context)
        return

    # Oddiy erkin suhbat
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
