import requests
import time
import threading
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Bot
import os

# === Настройки окружения ===
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = Bot(token=TOKEN)

# === Flask-сервер, чтобы Render не "усыпил" ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"


def run_flask():
    """Запускает мини-сервер на Render."""
    app.run(host="0.0.0.0", port=10000)


def ping_self():
    """Регулярно пингует сам себя, чтобы Render не уснул."""
    while True:
        try:
            if RENDER_EXTERNAL_URL:
                requests.get(RENDER_EXTERNAL_URL)
        except Exception:
            pass
        time.sleep(300)  # каждые 5 минут


# === Основная логика бота ===
def get_euro_rate():
    """Парсит курс евро с сайта Альфа-Банка."""
    url = "https://www.alfabank.by/exchange/digital/"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Ищем строку с EUR
        row = soup.find("div", {"class": "rate-tabs__content"})
        euro_row = row.find("div", string=lambda text: text and "EUR" in text)
        if not euro_row:
            return None

        # Находим соседний элемент с курсом покупки
        rate_element = euro_row.find_next("span", {"class": "index-rate"})
        if not rate_element:
            return None

        rate = float(rate_element.text.replace(",", "."))
        return rate
    except Exception as e:
        print("Ошибка при получении курса:", e)
        return None


def send_message(text):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print("Ошибка при отправке сообщения:", e)


def main():
    """Основной цикл проверки курса."""
    last_rate = None
    send_message("Бот запущен ✅\nПроверяю курс евро...")

    while True:
        rate = get_euro_rate()
        if rate is not None:
            if last_rate is None:
                send_message(f"Текущий курс евро: {rate} BYN")
            elif rate != last_rate:
                send_message(f"Курс евро изменился!\nБыло: {last_rate} → Стало: {rate} BYN")
            last_rate = rate
        time.sleep(300)  # проверка каждые 5 минут


# === Запуск всех потоков ===
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=ping_self).start()
    main()
