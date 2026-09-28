import os
import threading
import requests
import urllib.parse
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# =====================================================================
# SINFDOSH NOZIMA PROMPTI
# =====================================================================
SINFDOSH_PERSONA = """
Sizning ismingiz Nozima. Siz foydalanuvchining yaqin, samimiy va sho'x sinfdosh qiz do'stisiz.
- O'zbek tilida do'stona, samimiy, zamonaviy va erkin gapiring.
- Foydalanuvchi bilan har qanday mavzuda (kun tartibi, darslar, kayfiyat, hayotiy maslahatlar, qiziqishlar) suhbatlashing.
- Rasmiy jargonlar ishlatmang, kitobiy gapirmang va sinfdosh ro'lidan chiqib ketmang.
- Doim kayfiyatni ko'taruvchi va samimiy javoblar bering.
- Qisqa va londa, Telegram chatiga mos ravishda javob qaytaring.
"""

# 1. FLASK (Render uxlab qolmasligi uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: ONLINE"

def start_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. ENVIRONMENT KALITLARI
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 

# 3. GEMINI API ORQALI MATN GENERATSIYASI
def generate_ai_response(user_text, user_id, context_data):
    if 'chat_history' not in context_data:
        context_data['chat_history'] = []

    history = context_data['chat_history'][-6:] 
    
    if not GEMINI_API_KEY:
        return "Gemini API kaliti kiritilmagan. Render'dagi Environment variables'ni tekshiring."

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        contents = [{"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {SINFDOSH_PERSONA}"}]}]
        for msg in history:
            contents.append({"role": msg['role'], "parts": [{"text": msg['text']}]})
        contents.append({"role": "user", "parts": [{"text": user_text}]})

        payload = {"contents": contents}
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            reply = res.json()['candidates'][0]['content']['parts'][0]['text']
            context_data['chat_history'].append({'role': 'user', 'text': user_text})
            context_data['chat_history'].append({'role': 'model', 'text': reply})
            return reply
        else:
            print(f"Gemini API xatolik kodi: {res.status_code}, javob: {res.text}")
    except Exception as e:
        print(f"Gemini API xatosi: {e}")

    return "Xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring."

# 4. HIGH-QUALITY (8K ULTRA HD FLUX) RASM GENERATSIYASI
def generate_image_url(prompt):
    """
    8K resolution, photorealistic va yuqori detalizatsiya bilan rasm yaratish
    """
    try:
        hq_prompt = f"{prompt}, 8k resolution, highly detailed, photorealistic, ultra HD, sharp focus, masterpiece, professional photo"
        encoded_prompt = urllib.parse.quote(hq_prompt)
        
        # 2048x2048 va Flux modeli orqali eng yuqori sifatli rasm
        image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=2048&height=2048&enhance=true&model=flux"
        return image_url
    except Exception as e:
        print(f"Rasm yaratishda xatolik: {e}")
        return None

# 5. TUGMALAR VA HANDLERLAR
main_keyboard = ReplyKeyboardMarkup(
    [["🎨 Rasm chizish", "💬 Chatni tozalash"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_my_commands([
        BotCommand("start", "Botni qayta ishga tushirish"),
        BotCommand("draw", "Rasm chizish: /draw rasm ta'rifi"),
        BotCommand("clear", "Muloqot tarixini tozalash")
    ])
    
    welcome_text = (
        "Ooo, salom sinfdosh! 🖐\n\n"
        "Men bilan bemalol istalgan mavzuda gaplashishing mumkin! 😊\n"
        "Rasm chizdirish uchun **'🎨 Rasm chizish'** tugmasini bos yoki `/draw matn` deb yubor!"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_keyboard)

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['chat_history'] = []
    await update.message.reply_text("Eski suhbatlarimizni esdan chiqardim! Yangitdan gaplashamiz 😉")

async def generate_image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        prompt = " ".join(context.args)
    else:
        prompt = update.message.text if update.message.text != "🎨 Rasm chizish" else ""

    if not prompt:
        await update.message.reply_text("Nimaning rasmini chizay? Masalan: `/draw Samarkand at sunset, realistic`", parse_mode="Markdown")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_msg = await update.message.reply_text("🎨 8K Ultra HD sifatdagi rasm tayyorlanmoqda, biroz kuting...")

    img_url = generate_image_url(prompt)
    if img_url:
        try:
            await update.message.reply_photo(photo=img_url, caption=f"🖼 **8K Natija:** {prompt}", parse_mode="Markdown")
            await status_msg.delete()
        except Exception as e:
            print(f"Rasm yuborishda xatolik: {e}")
            await status_msg.edit_text("Rasm yuborishda xatolik yuz berdi. Qayta urinib ko'ring.")
    else:
        await status_msg.edit_text("Rasm chizishda xatolik bo'ldi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if user_text == "💬 Chatni tozalash":
        await clear_history(update, context)
        return

    if user_text == "🎨 Rasm chizish":
        context.user_data['waiting_for_photo'] = True
        await update.message.reply_text("Nimaning rasmini chizib beray? Ta'rifini yozib yubor (Masalan: *Futuristic Tashkent city with flying cars*):", parse_mode="Markdown")
        return

    if context.user_data.get('waiting_for_photo'):
        context.user_data['waiting_for_photo'] = False
        await generate_image_cmd(update, context)
        return

    # Muloqot qismi
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    ai_reply = generate_ai_response(user_text, update.effective_user.id, context.user_data)
    await update.message.reply_text(ai_reply)

# 6. ISHGA TUSHIRISH
def main():
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("draw", generate_image_cmd))
    application.add_handler(CommandHandler("image", generate_image_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("--> BOT TAYYOR REJIMDA ISHGA TUSHDI!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
