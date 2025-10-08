import os
import asyncio
import threading
import requests
from flask import Flask, request
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# === Конфигурация ===
TOKEN = os.getenv("TOKEN")  # твой токен телеграм-бота
WEBHOOK_URL = "https://alfabot-wt8z.onrender.com/webhook"  # твой Render URL + /webhook

app = Flask(__name__)

# === Функция получения курса евро ===
def get_exchange_rate():
    try:
        url = "https://www.alfabank.by/api/v1/exchange-rates/rates/?currencyCode=978&rateType=cash"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        rate = data["rates"][0]
        buy = rate["buyRate"]
        sell = rate["sellRate"]

        return f"💶 Курс евро в Альфа-Банке (наличный):\nПокупка: {buy} BYN\nПродажа: {sell} BYN"
    except Exception as e:
        print(f"Ошибка получения курса: {e}")
        return "Не удалось получить курс 😕"


# === Хэндлеры команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Курс евро")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! 👋\nЯ показываю текущий курс евро.\nВыбери команду в меню ниже:",
        reply_markup=reply_markup,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "евро" in text:
        rate_message = get_exchange_rate()
        await update.message.reply_text(rate_message)
    else:
        await update.message.reply_text("Я понимаю только команду 'Курс евро' 😊")


# === Настройка Telegram-приложения ===
async def setup_bot():
    app_telegram = Application.builder().token(TOKEN).build()

    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app_telegram.bot.set_webhook(WEBHOOK_URL)
    return app_telegram


# === Flask-маршруты ===
@app.route("/")
def index():
    return "✅ Telegram bot is running"


@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), app_telegram.bot)
    await app_telegram.process_update(update)
    return "OK", 200


# === Запуск ===
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app_telegram = loop.run_until_complete(setup_bot())

    def run_flask():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

    threading.Thread(target=run_flask).start()
