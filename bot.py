import asyncio
import logging
import os
import sys

# Ensure root package directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import setup_routers
from services.webapp_server import start_webapp_server
from services.monitoring import node_monitoring_loop

logger = logging.getLogger("remna-bot.main")

async def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN is missing! Please set it in .env file.")
        return

    logger.info("🚀 Starting Remna-Bot (Aiogram 3 + MiniApp REST Server + Node Monitoring)...")

    # Initialize Aiogram Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Include all modular feature routers
    dp.include_router(setup_routers())

    # 1. Start MiniApp REST Web Server in background
    await start_webapp_server()

    # 2. Start Node Monitoring Loop in background
    asyncio.create_task(node_monitoring_loop(bot))

    # 3. Start Telegram Bot Polling
    logger.info("🤖 Telegram Bot polling started. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Remna-Bot stopped gracefully.")
