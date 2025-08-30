import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import user_handlers, admin_handlers
from database import Database
from config import TOKEN, DB_PATH

# Инициализация логирования
logger = logging.getLogger(__name__)

async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    db = Database()

    # Initialize database
    await db.init()

    # Register middlewares
    dp.message.middleware.register(user_handlers.SaveUserMiddleware())

    # Include routers
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)