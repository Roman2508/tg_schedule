import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config import settings
from app.middlewares.user import UserMiddleware
from app.models.database import create_tables, async_session_maker
from app.services.cache import cache
from app.services.users import get_or_create_user
from app.models import UserRole

from app.handlers import start, search, schedule_view, admin

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def ensure_super_admin():
    """Create super admin record in DB on startup."""
    async with async_session_maker() as session:
        user = await get_or_create_user(session, telegram_id=settings.SUPER_ADMIN_ID)
        user.role = UserRole.ADMIN
        await session.commit()
        logger.info(f"Super admin {settings.SUPER_ADMIN_ID} role ensured.")


async def main():
    logger.info("Starting bot...")

    # Connect to Redis for FSM storage
    await cache.connect()
    storage = RedisStorage.from_url(settings.REDIS_URL)

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # Routers
    dp.include_router(start.router)
    dp.include_router(search.router)
    dp.include_router(schedule_view.router)
    dp.include_router(admin.router)

    # Init DB and super admin
    await create_tables()
    await ensure_super_admin()

    logger.info("Bot started. Polling...")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await cache.disconnect()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
