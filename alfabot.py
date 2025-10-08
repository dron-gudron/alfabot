import asyncio
import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import os

# === НАСТРОЙКИ ===
TOKEN = os.getenv("TOKEN") or "ВАШ_TELEGRAM_TOKEN"
CHAT_ID = os.getenv("CHAT_ID") or "ВАШ_CHAT_ID"
CHECK_INTERVAL = 600  # проверка курса (секунд)
PING_INTERVAL = 300   # пинг (секунд)
URL = "https://www.alfabank.by/exchange/digital/"

bot = Bot(token=TOKEN)
dp = Dispatcher()
last_buy, last_sell = None, None


async def get_eur_rate():
    """Парсит курс евро с сайта Альфа-Банка"""
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html, "lxml")

    eur_block = soup.find("div", {"data-currency": "EUR"})
    if not eur_block:
        return None, None

    buy_span = eur_block.find("span", class_="rate__value--buy")
    sell_span = eur_block.find("span", class_="rate__value--sell")
    if not buy_span or not sell_span:
        return None, None

    buy = float(buy_span.text.strip().replace(",", "."))
    sell = float(sell_span.text.strip().replace(",", "."))
    return buy, sell


async def check_rate():
    """Проверяет курс и уведомляет при изменениях"""
    global last_buy, last_sell
    while True:
        try:
            buy, sell = await get_eur_rate()
            if buy and sell:
                if last_buy is not None and (buy != last_buy or sell != last_sell):
                    text = (
                        f"💶 Курс евро изменился!\n\n"
                        f"Покупка: {buy:.4f}\nПродажа: {sell:.4f}"
                    )
                    await bot.send_message(CHAT_ID, text)
                last_buy, last_sell = buy, sell
            else:
                print("⚠️ Не удалось получить курс евро")
        except Exception as e:
            print("Ошибка при проверке:", e)
        await asyncio.sleep(CHECK_INTERVAL)


async def ping_self():
    """Пингует сам себя, чтобы Render не "усыпил""""
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        print("⚠️ Переменная RENDER_EXTERNAL_URL не задана (ping отключен)")
        return

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                await session.get(url)
                print("✅ Пинг отправлен Render")
        except Exception as e:
            print("Ошибка пинга:", e)
        await asyncio.sleep(PING_INTERVAL)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start — приветствие + показ текущего курса"""
    buy, sell = await get_eur_rate()
    if buy and sell:
        text = (
            f"✅ Бот запущен и отслеживает курс евро на сайте Альфа-Банка.\n\n"
            f"💶 Текущий курс:\n"
            f"Покупка: {buy:.4f}\nПродажа: {sell:.4f}"
        )
    else:
        text = "⚠️ Не удалось получить курс евро, попробуй позже."

    await message.answer(text)
    asyncio.create_task(check_rate())


async def on_startup():
    """Запуск фоновых задач"""
    asyncio.create_task(ping_self())
    print("🚀 Бот запущен!")


async def main():
    await on_startup()
    await dp.start_polling(bot)


# === HTTP-сервер для Render ===
# (Render требует открытый порт, иначе процесс “уснёт”)
async def handle(request):
    return web.Response(text="Bot is alive")

async def run_webserver():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()
    print("🌐 Веб-сервер запущен на порту", os.getenv("PORT", 10000))

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_webserver())
    loop.run_until_complete(main())
