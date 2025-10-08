import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Bot, Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# ——— Получение курса евро ———
def get_eur_rate():
    url = "https://www.alfabank.by/exchange/digital/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    eur_block = soup.find("div", {"class": "exchange-currency", "data-currency": "EUR"})
    if eur_block:
        rate = eur_block.find("span", {"class": "rate-value"}).text.strip()
        return float(rate.replace(",", "."))
    return None

# ——— Основной цикл проверки курса ———
last_rate = None

def check_rate_loop():
    global last_rate
    while True:
        try:
            current = get_eur_rate()
            if current is not None:
                if last_rate is None:
                    last_rate = current
                elif abs(current - last_rate) >= 0.001:
                    text = f"💶 Курс евро изменился!\nБыло: {last_rate:.3f}\nСтало: {current:.3f}"
                    bot.send_message(chat_id=CHAT_ID, text=text)
                    last_rate = current
        except Exception as e:
            print("Ошибка при проверке курса:", e)
        time.sleep(60)

# ——— Команды Telegram ———
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate = get_eur_rate()
    if rate:
        await update.message.reply_text(f"Бот запущен ✅\nТекущий курс евро: {rate:.3f}")
    else:
        await update.message.reply_text("Не удалось получить курс 😕")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate = get_eur_rate()
    if rate:
        await update.message.reply_text(f"💶 Сейчас курс евро: {rate:.3f}")
    else:
        await update.message.reply_text("Не удалось получить курс 😕")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 Доступные команды:\n"
        "/start — запустить бота и показать текущий курс\n"
        "/check — проверить курс вручную\n"
        "/help — показать это сообщение"
    )
    await update.message.reply_text(text)

# ——— Flask, чтобы Render не засыпал ———
@app.route("/")
def home():
    return "Бот работает!"

def ping_self():
    while True:
        try:
            requests.get("https://alfabot-wt8z.onrender.com")  # ← замени на свой URL!
        except:
            pass
        time.sleep(300)

# ——— Запуск бота ———
def main():
    threading.Thread(target=check_rate_loop, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()

    app_builder = ApplicationBuilder().token(TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    app_builder.add_handler(CommandHandler("check", check))
    app_builder.add_handler(CommandHandler("help", help_command))

    # ——— Добавляем меню команд ———
    app_builder.bot.set_my_commands([
        BotCommand("start", "Запустить бота и показать курс"),
        BotCommand("check", "Проверить курс вручную"),
        BotCommand("help", "Показать справку"),
    ])

    print("Бот запущен и слушает команды...")
    app_builder.run_polling()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000), daemon=True).start()
    main()
