import os
import asyncio
import threading
import requests
from flask import Flask, request
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# === Конфигурация ===
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://alfabot-wt8z.onrender.com/webhook")
CHECK_INTERVAL = 300  # Проверка каждые 5 минут (в секундах)

app = Flask(__name__)

# === Глобальные переменные ===
app_telegram = None
loop = None

# === Хранилище ===
subscribed_users = set()
last_rate = {"buy": None, "sell": None}

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
        return {"buy": buy, "sell": sell}
    except Exception as e:
        print(f"Ошибка получения курса: {e}")
        return None

def format_rate_message(rate):
    return f"💶 Курс евро в Альфа-Банке (наличный):\nПокупка: {rate['buy']} BYN\nПродажа: {rate['sell']} BYN"

# === Функция проверки изменений ===
async def check_rate_changes(context: ContextTypes.DEFAULT_TYPE):
    global last_rate
    
    current_rate = get_exchange_rate()
    if not current_rate:
        return
    
    # Если это первая проверка, сохраняем курс и отправляем уведомление о запуске
    if last_rate["buy"] is None:
        last_rate = current_rate
        print(f"Начальный курс: покупка {current_rate['buy']}, продажа {current_rate['sell']}")
        
        # Отправляем сообщение о запуске всем подписчикам
        startup_message = "✅ Бот запущен и начал отслеживание курса!\n\n"
        startup_message += format_rate_message(current_rate)
        
        for user_id in list(subscribed_users):
            try:
                await context.bot.send_message(chat_id=user_id, text=startup_message)
            except Exception as e:
                print(f"Не удалось отправить стартовое сообщение пользователю {user_id}: {e}")
        
        return
    
    # Проверяем, изменился ли курс
    buy_changed = current_rate["buy"] != last_rate["buy"]
    sell_changed = current_rate["sell"] != last_rate["sell"]
    
    if buy_changed or sell_changed:
        print(f"Курс изменился! Старый: {last_rate}, Новый: {current_rate}")
        
        # Формируем сообщение об изменении
        message = "🔔 Курс евро изменился!\n\n"
        message += format_rate_message(current_rate)
        message += "\n\n📊 Изменения:\n"
        
        if buy_changed:
            diff = current_rate["buy"] - last_rate["buy"]
            emoji = "📈" if diff > 0 else "📉"
            message += f"{emoji} Покупка: {diff:+.4f} BYN\n"
        
        if sell_changed:
            diff = current_rate["sell"] - last_rate["sell"]
            emoji = "📈" if diff > 0 else "📉"
            message += f"{emoji} Продажа: {diff:+.4f} BYN"
        
        # Отправляем уведомления подписчикам
        for user_id in list(subscribed_users):
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                if "blocked" in str(e).lower() or "bot was blocked" in str(e).lower():
                    subscribed_users.discard(user_id)
        
        # Обновляем сохраненный курс
        last_rate = current_rate

# === Хэндлеры команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Курс евро")],
        [KeyboardButton("Подписаться"), KeyboardButton("Отписаться")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я отслеживаю курс евро в Альфа-Банке и присылаю уведомления при изменении курса.\n\n"
        "📌 Доступные команды:\n"
        "• Курс евро - узнать текущий курс\n"
        "• Подписаться - получать уведомления при изменении курса\n"
        "• Отписаться - отключить уведомления",
        reply_markup=reply_markup,
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.message.from_user.id
    
    if "евро" in text:
        rate = get_exchange_rate()
        if rate:
            await update.message.reply_text(format_rate_message(rate))
        else:
            await update.message.reply_text("Не удалось получить курс 😕")
    
    elif "подписаться" in text:
        subscribed_users.add(user_id)
        print(f"Пользователь {user_id} подписался. Всего подписчиков: {len(subscribed_users)}")
        await update.message.reply_text(
            "✅ Вы подписаны на уведомления!\n"
            "Вы будете получать сообщение каждый раз, когда курс евро изменится."
        )
    
    elif "отписаться" in text:
        if user_id in subscribed_users:
            subscribed_users.remove(user_id)
            print(f"Пользователь {user_id} отписался. Всего подписчиков: {len(subscribed_users)}")
            await update.message.reply_text("❌ Вы отписались от уведомлений")
        else:
            await update.message.reply_text("Вы и так не подписаны на уведомления")
    
    else:
        await update.message.reply_text(
            "Я понимаю команды:\n"
            "• Курс евро\n"
            "• Подписаться\n"
            "• Отписаться"
        )

# === Фоновая задача проверки курса ===
async def background_rate_checker(app_telegram):
    """Фоновая задача для проверки курса"""
    await asyncio.sleep(10)  # Ждем 10 секунд перед первой проверкой
    
    while True:
        try:
            # Создаем контекст для отправки сообщений
            context = ContextTypes.DEFAULT_TYPE(application=app_telegram)
            await check_rate_changes(context)
        except Exception as e:
            print(f"Ошибка в фоновой проверке: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)

# === Настройка Telegram-приложения ===
async def setup_bot():
    app_telegram = Application.builder().token(TOKEN).build()
    
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await app_telegram.bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook установлен: {WEBHOOK_URL}")
    print(f"Проверка курса каждые {CHECK_INTERVAL} секунд")
    
    return app_telegram

# === Flask-маршруты ===
@app.route("/")
def index():
    return f"✅ Telegram bot is running<br>Subscribers: {len(subscribed_users)}<br>Last rate: Buy {last_rate['buy']}, Sell {last_rate['sell']}"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_telegram.bot)
    # Запускаем обработку в event loop
    asyncio.run_coroutine_threadsafe(
        app_telegram.process_update(update),
        loop
    )
    return "OK", 200

# === Запуск ===
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app_telegram = loop.run_until_complete(setup_bot())
    
    # Запуск фоновой проверки курса
    asyncio.ensure_future(background_rate_checker(app_telegram), loop=loop)
    
    # Запуск Flask в отдельном потоке
    def run_flask():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Бесконечный цикл для поддержания работы
    print("✅ Бот запущен и работает!")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Остановка бота...")
