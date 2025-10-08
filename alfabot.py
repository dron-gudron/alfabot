import os
import requests
import threading
import time
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# === Настройки ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
app = Flask(__name__)

# === Меню ===
menu = ReplyKeyboardMarkup(
    [["💶 Курс евро", "💵 Курс доллара"], ["ℹ️ Помощь"]],
    resize_keyboard=True
)

# === Обработчики ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот AlfaBot 🤖", reply_markup=menu)

async def get_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "евро" in text.lower():
        currency = "EUR"
    elif "доллар" in text.lower():
        currency = "USD"
    else:
        await update.message.reply_text("Выберите валюту из меню 🙂", reply_markup=menu)
        return

    try:
        res = requests.get(f"https://api.exchangerate.host/latest?base={currency}&symbols=RUB")
        rate = res.json()["rates"]["RUB"]
        await update.message.reply_text(f"1 {currency} = {rate:.2f} RUB 🇷🇺")
    except Exception:
        await update.message.reply_text("Не удалось получить курс 😕")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "💶 Курс евро — узнать курс евро к рублю\n"
        "💵 Курс доллара — узнать курс доллара к рублю\n"
        "/start — открыть меню"
    )

# === Flask маршруты ===
@app.route("/")
def index():
    return "Бот работает ✅"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, application.bot)
    application.create_task(application.process_update(update))
    return "OK", 200

# === Пинг Render каждые 10 минут ===
def ping_self():
    while True:
        try:
            requests.head(f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}")
        except Exception:
            pass
        time.sleep(600)

threading.Thread(target=ping_self, daemon=True).start()

# === Создание Telegram приложения ===
application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate))

# === Функция установки Webhook ===
def set_webhook():
    try:
        url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
        if url and TOKEN:
            application.bot.set_webhook(url)
            print(f"✅ Webhook установлен: {url}")
        else:
            print("⚠️ Не удалось установить webhook — проверь переменные окружения")
    except Exception as e:
        print(f"Ошибка установки webhook: {e}")

# === Запуск Flask ===
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
