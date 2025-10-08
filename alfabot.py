import os
import time
import threading
import requests
from flask import Flask
from telegram import Bot, Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ——— Настройки ———
TOKEN = os.getenv("TOKEN")        # теперь токен читается из переменной TOKEN
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# ——— Получение курса евро из API Альфа-Банка ———
def get_eur_rate():
    try:
        url = "https://developerhub.alfabank.by:8273/partner/1.0.1/public/rates"
        response = requests.get(url, timeout=10)
        data = response.json()

        for rate in data.get("rates", []):
            if rate.get("sellCurrency") == "EUR" and rate.get("buyCurrency") == "BYN":
                return float(rate["buyRate"])
    except Exception as e:
        print("Ошибка при получении курса:", e)
    return None

# ——— Проверка изменений курса ———
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
        time.sleep(60)  # проверяем раз в минуту

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
        "/help — показать справку"
    )
    await update.message.reply_text(text)

# ——— Flask сервер, чтобы Render не засыпал ———
@app.route("/")
def home():
    return "Бот работает!"

def ping_self():
    while True:
        try:
            requests.get("https://alfabot-wt8z.onrender.com")  # ⚠️ замени на свой URL, если другой
        except:
            pass
        time.sleep(300)  # пинг каждые 5 минут

# ——— Запуск бота ———
def main():
    threading.Thread(target=check_rate_loop, daemon=True).start()
    threading.Thread(target=ping_self, daemon=True).start()

    app_builder = ApplicationBuilder().token(TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    app_builder.add_handler(CommandHandler("check", check))
    app_builder.add_handler(CommandHandler("help", help_command))

    # Меню команд в Telegram
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
