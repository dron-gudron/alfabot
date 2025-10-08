from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import requests
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN") or "ВАШ_ТОКЕН_БОТА"
WEBHOOK_URL = f"https://alfabot-wt8z.onrender.com/{TOKEN}"

app = Flask(__name__)

# === Получение курса евро с сайта Альфа-Банка ===
def get_eur_rate():
    try:
        url = "https://www.alfabank.by/api/exchange-rates/public/digital"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()

        # ищем евро в списке
        for item in data:
            if item["sellCurrency"] == "EUR" and item["buyCurrency"] == "BYN":
                rate_buy = item["buyRate"]
                rate_sell = item["sellRate"]
                return rate_buy, rate_sell

        return None
    except Exception as e:
        print(f"Ошибка при получении курса: {e}")
        return None

# === Обработчики команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Курс евро 💶"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! 👋\nЯ показываю курс евро по данным Альфа-Банка Беларусь.\nВыбери команду в меню ниже:",
        reply_markup=reply_markup
    )

async def eur_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate = get_eur_rate()
    if rate:
        buy, sell = rate
        await update.message.reply_text(
            f"💶 Курс евро по Альфа-Банку:\n\nПокупка: {buy:.2f} BYN\nПродажа: {sell:.2f} BYN"
        )
    else:
        await update.message.reply_text("Не удалось получить курс с сайта Альфа-Банка 😔")

# === Инициализация бота ===
async def setup_bot():
    app_telegram = Application.builder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, eur_rate))

    # Устанавливаем вебхук
    await app_telegram.bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    return app_telegram

# === Flask webhook ===
telegram_app = None

@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    global telegram_app
    if telegram_app is None:
        return "Bot not initialized", 500

    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return "ok", 200

@app.route("/")
def home():
    return "Бот работает!"

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    telegram_app = loop.run_until_complete(setup_bot())
    app.run(host="0.0.0.0", port=10000)
