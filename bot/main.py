import asyncio
import logging
import sys
import os

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from django.conf import settings

from bot.loader import bot, dp
from bot.handlers import router
from bot.middlewares import DatabaseMiddleware, SubscriptionMiddleware, ThrottlingMiddleware

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def set_bot_commands():
    """Bot buyruqlarini sozlash"""
    # Oddiy foydalanuvchilar uchun
    user_commands = [
        BotCommand(command="start", description="🏠 Boshlash"),
        BotCommand(command="help", description="❓ Yordam"),
        BotCommand(command="top", description="🔥 Top kinolar"),
        BotCommand(command="last", description="🆕 Yangi kinolar"),
        BotCommand(command="rand", description="🎲 Random kino"),
        BotCommand(command="categories", description="📂 Kategoriyalar"),
        BotCommand(command="premium", description="💎 Premium"),
        BotCommand(command="profile", description="👤 Profil"),
    ]

    # Admin buyruqlari
    admin_commands = user_commands + [
        BotCommand(command="admin", description="👨‍💼 Admin panel"),
        BotCommand(command="addmovie", description="➕ Kino qo'shish"),
        BotCommand(command="user", description="👤 User ma'lumoti"),
        BotCommand(command="ban", description="⛔ Bloklash"),
        BotCommand(command="unban", description="✅ Blokdan chiqarish"),
    ]

    # Barcha foydalanuvchilar uchun
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Har bir admin uchun alohida
    for admin_id in settings.ADMINS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            logger.info(f"Admin buyruqlari o'rnatildi: {admin_id}")
        except Exception as e:
            logger.error(f"Admin buyruqlarini o'rnatishda xato ({admin_id}): {e}")


async def on_startup():
    """Bot ishga tushganda"""
    logger.info("Bot ishga tushdi!")

    # Webhookni o'chirish
    await bot.delete_webhook(drop_pending_updates=True)

    # Bot buyruqlarini o'rnatish
    await set_bot_commands()
    logger.info("Bot buyruqlari o'rnatildi!")

    # Premium scheduler ni ishga tushirish (background task)
    from bot.utils.scheduler import start_scheduler
    asyncio.create_task(start_scheduler(bot, check_interval=3600))  # Har 1 soatda tekshirish
    logger.info("Premium scheduler ishga tushdi!")


async def on_shutdown():
    """Bot to'xtaganda"""
    logger.info("Bot to'xtadi!")
    await bot.session.close()


async def main():
    """Asosiy funksiya"""
    # Middlewarelar
    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(DatabaseMiddleware())
    dp.message.middleware(SubscriptionMiddleware())

    dp.callback_query.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # Routerlar
    dp.include_router(router)

    # Startup/Shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Polling
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
