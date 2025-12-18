from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.core.cache import cache
from cachetools import TTLCache

# Local cache for faster access
_user_cache = TTLCache(maxsize=1000, ttl=60)
_settings_cache = TTLCache(maxsize=1, ttl=300)


class DatabaseMiddleware(BaseMiddleware):
    """Database middleware - optimized for speed"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            # Fast settings check from cache
            settings = await self._get_settings_cached()

            if not settings.is_active:
                msg = settings.maintenance_message or "Bot texnik ishlar sababli to'xtatilgan."
                if isinstance(event, Message):
                    await event.answer(msg)
                elif isinstance(event, CallbackQuery):
                    await event.answer(msg, show_alert=True)
                return

            # Fast user check from cache
            db_user = await self._get_user_cached(user.id)

            if db_user:
                if db_user.is_banned:
                    ban_text = "⛔️ Siz botda bloklangansiz."
                    if db_user.ban_reason:
                        ban_text += f"\nSabab: {db_user.ban_reason}"
                    if isinstance(event, Message):
                        await event.answer(ban_text)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(ban_text, show_alert=True)
                    return

                data['db_user'] = db_user

            data['bot_settings'] = settings

        return await handler(event, data)

    async def _get_user_cached(self, user_id: int):
        """Get user with local cache"""
        if user_id in _user_cache:
            return _user_cache[user_id]

        user = await self._get_user_db(user_id)
        if user:
            _user_cache[user_id] = user
        return user

    async def _get_settings_cached(self):
        """Get settings with local cache"""
        if 'settings' in _settings_cache:
            return _settings_cache['settings']

        settings = await self._get_settings_db()
        _settings_cache['settings'] = settings
        return settings

    @sync_to_async
    def _get_user_db(self, user_id: int):
        from apps.users.models import User
        try:
            return User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return None

    @sync_to_async
    def _get_settings_db(self):
        from apps.core.models import BotSettings
        return BotSettings.get_settings()


def clear_user_cache(user_id: int = None):
    """Clear user cache"""
    if user_id:
        _user_cache.pop(user_id, None)
    else:
        _user_cache.clear()


def clear_settings_cache():
    """Clear settings cache"""
    _settings_cache.clear()
