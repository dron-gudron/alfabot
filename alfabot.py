import os
import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =======================
# 🔧 Настройки
# =======================
TOKEN = os.getenv("TOKEN") or "ТВОЙ_ТОКЕН_БОТА"
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://alfabot-wt8z.onrender.com{WEBHOOK_PATH}"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# =======================
# 🧠 Функция парсинга курса
# =======================
def get_eur_rate():
    url = "https://www.alfabank.by/exchange/digital/"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        # ищем элемент с EUR
        row = soup.find("div", text="EUR").find_parent("div", class_="currency-item")
        buy = row.find_all("span", class_="rate")[0].text.strip()
        sell = row.find_all("span", class_="rate")[1].text.strip()
        return f"💶 Курс евро:\nПокупка: {buy}\nПродажа: {sell}"
    except Exception as e:
        logging.error(f"Ошибка при получении курса: {e}")
        return "Не удалось получить курс 😕"

# =======================
# 🤖 Обработчики команд
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Курс евро 💶"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! 👋\nЯ показываю текущий курс евро.\nВыбери команду в меню ниже:",
        reply_markup=markup
    )

async def euro_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = get_eur_rate()
    await update.message.reply_text(text)

# =======================
# 🚀 Инициализация Telegram приложения
# =======================
async def setup_bot():
    app_telegram = Application.builder().token(TOKEN).build()

    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.Regex("Курс евро"), euro_rate))

    await app_telegram.initialize()
    await app_telegram.bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}")

    return app_telegram

telegram_app = asyncio.run(setup_bot())

# =======================
# 🌐 Flask webhook
# =======================
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return "ok", 200

@app.route("/")
def index():
    return "АльфаБот работает!", 200

# =======================
# 🏁 Запуск Flask
# =======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
