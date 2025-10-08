import os
import requests
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

# === Настройки ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# === Меню команд ===
menu = ReplyKeyboardMarkup(
    [["💶 Курс евро", "💵 Курс доллара"], ["ℹ️ Помощь"]],
    resize_keyboard=True
)

# === Обработчики ===
def start(update, context):
    update.message.reply_text("Привет! Я бот AlfaBot 🤖", reply_markup=menu)

def get_rate(update, context):
    text = update.message.text
    if "евро" in text.lower():
        currency = "EUR"
    elif "доллар" in text.lower():
        currency = "USD"
    else:
        update.message.reply_text("Выберите валюту из меню 🙂", reply_markup=menu)
        return

    try:
        res = requests.get(f"https://api.exchangerate.host/latest?base={currency}&symbols=RUB")
        rate = res.json()["rates"]["RUB"]
        update.message.reply_text(f"1 {currency} = {rate:.2f} RUB 🇷🇺")
    except Exception:
        update.message.reply_text("Не удалось получить курс 😕")

def help_command(update, context):
    update.message.reply_text(
        "Команды:\n"
        "💶 Курс евро — узнать курс евро к рублю\n"
        "💵 Курс доллара — узнать курс доллара к рублю\n"
        "/start — открыть меню"
    )

# === Webhook Flask ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Бот работает ✅"

# === Dispatcher ===
from telegram.ext import Dispatcher
dp = Dispatcher(bot, None, use_context=True)
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_rate))

# === Установка Webhook при старте ===
@app.before_first_request
def set_webhook():
    url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.set_webhook(url)
    print(f"Webhook установлен: {url}")

# === Пинг для Render ===
import threading, time
def ping_self():
    while True:
        try:
            requests.head(f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}")
        except Exception:
            pass
        time.sleep(600)

threading.Thread(target=ping_self, daemon=True).start()

# === Запуск ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
