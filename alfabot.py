import os
import threading
import time
import requests
from flask import Flask, request
from telegram import Update, Bot, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Настройки ---
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = f"https://alfabot-wt8z.onrender.com/{TOKEN}"

app = Flask(__name__)

# --- Телеграм бот ---
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()


# --- Получение курса евро ---
def get_eur_rate():
    try:
        r = requests.get("https://api.exchangerate.host/latest?base=EUR&symbols=USD,RUB")
        data = r.json()
        eur_usd = data["rates"]["USD"]
        eur_rub = data["rates"]["RUB"]
        return f"💶 1 EUR = {eur_usd:.2f} USD\n💶 1 EUR = {eur_rub:.2f} RUB"
    except Exception as e:
        print("Ошибка при получении курса:", e)
        return "Не удалось получить курс 😕"


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("💶 Курс евро")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! 👋\nЯ показываю текущий курс евро.\nВыбери команду в меню ниже:",
        reply_markup=reply_markup
    )

async def eur_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = get_eur_rate()
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используй кнопки ниже, чтобы узнать курс евро 💶")


# --- Обработчики ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("курс евро"), eur_rate))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("помощь"), help_command))


# --- Flask webhook ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.create_task(application.process_update(update))
    return "ok", 200


@app.route("/")
def home():
    return "Бот работает ✅", 200


# --- Самопинг, чтобы Render не засыпал ---
def ping_self():
    while True:
        try:
            requests.head("https://alfabot-wt8z.onrender.com/")
        except:
            pass
        time.sleep(600)  # каждые 10 минут


# --- Фоновый запуск Telegram ---
def run_telegram():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        await application.initialize()
        await bot.set_webhook(WEBHOOK_URL)
        print(f"✅ Webhook установлен: {WEBHOOK_URL}")
        await application.start()
        await application.updater.start_polling()
        await asyncio.Event().wait()  # держим loop живым

    loop.run_until_complete(run())


if __name__ == "__main__":
    threading.Thread(target=ping_self, daemon=True).start()
    threading.Thread(target=run_telegram, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
