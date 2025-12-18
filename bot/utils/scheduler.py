"""
Premium obuna tugashi haqida eslatma yuborish uchun scheduler
"""
import asyncio
import logging
from datetime import timedelta
from typing import Optional

from aiogram import Bot
from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


@sync_to_async
def get_expiring_premium_users(days: int = 1):
    """Premium obunasi tugayotgan userlarni olish"""
    from apps.users.models import User

    now = timezone.now()
    target_date = now + timedelta(days=days)

    # 1 kun ichida tugaydigan premium userlar
    users = User.objects.filter(
        is_premium=True,
        premium_expires__gte=now,
        premium_expires__lte=target_date,
        is_banned=False
    ).exclude(
        # Allaqachon eslatma yuborilganlarni o'tkazib yuborish (keyinchalik qo'shiladi)
    )

    return list(users)


@sync_to_async
def get_expired_premium_users():
    """Premium obunasi tugagan userlarni olish"""
    from apps.users.models import User

    now = timezone.now()

    # Tugagan lekin hali premium=True bo'lganlar
    users = User.objects.filter(
        is_premium=True,
        premium_expires__lt=now
    )

    return list(users)


@sync_to_async
def deactivate_expired_premium(user_id: int):
    """Tugagan premium obunani deaktiv qilish"""
    from apps.users.models import User

    try:
        user = User.objects.get(user_id=user_id)
        user.is_premium = False
        user.save(update_fields=['is_premium'])
        return True
    except User.DoesNotExist:
        return False


async def send_premium_expiry_notification(bot: Bot, user_id: int, days_left: int):
    """Premium tugashi haqida xabar yuborish"""
    try:
        if days_left == 1:
            text = (
                "⚠️ <b>Premium obunangiz tugamoqda!</b>\n\n"
                "Sizning Premium obunangiz <b>1 kun</b> ichida tugaydi.\n\n"
                "💎 Uzaytirish uchun /premium buyrug'ini yuboring yoki "
                "quyidagi tugmani bosing."
            )
        elif days_left == 0:
            text = (
                "⚠️ <b>Premium obunangiz bugun tugaydi!</b>\n\n"
                "💎 Uzaytirish uchun /premium buyrug'ini yuboring."
            )
        else:
            text = (
                f"⚠️ <b>Premium obunangiz {days_left} kun ichida tugaydi!</b>\n\n"
                "💎 Uzaytirish uchun /premium buyrug'ini yuboring."
            )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Premium uzaytirish", callback_data="premium")]
        ])

        await bot.send_message(user_id, text, reply_markup=kb)
        logger.info(f"Premium eslatma yuborildi: user_id={user_id}, days_left={days_left}")
        return True

    except Exception as e:
        logger.error(f"Premium eslatma yuborishda xato: user_id={user_id}, error={e}")
        return False


async def send_premium_expired_notification(bot: Bot, user_id: int):
    """Premium tugaganligi haqida xabar yuborish"""
    try:
        text = (
            "❌ <b>Premium obunangiz tugadi!</b>\n\n"
            "Endi Premium kinolarni ko'ra olmaysiz.\n\n"
            "💎 Qayta sotib olish uchun /premium buyrug'ini yuboring."
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Premium sotib olish", callback_data="premium")]
        ])

        await bot.send_message(user_id, text, reply_markup=kb)
        logger.info(f"Premium tugadi xabari yuborildi: user_id={user_id}")
        return True

    except Exception as e:
        logger.error(f"Premium tugadi xabarini yuborishda xato: user_id={user_id}, error={e}")
        return False


async def check_premium_expiry(bot: Bot):
    """Premium obunalarni tekshirish va eslatma yuborish"""
    logger.info("Premium obunalarni tekshirish boshlandi...")

    # 1 kun qolgan userlar
    expiring_users = await get_expiring_premium_users(days=1)
    logger.info(f"1 kun qolgan userlar: {len(expiring_users)} ta")

    for user in expiring_users:
        days_left = max(0, (user.premium_expires - timezone.now()).days)
        await send_premium_expiry_notification(bot, user.user_id, days_left)
        await asyncio.sleep(0.1)  # Rate limit uchun

    # Tugagan userlar
    expired_users = await get_expired_premium_users()
    logger.info(f"Tugagan userlar: {len(expired_users)} ta")

    for user in expired_users:
        await send_premium_expired_notification(bot, user.user_id)
        await deactivate_expired_premium(user.user_id)
        await asyncio.sleep(0.1)

    logger.info("Premium tekshirish yakunlandi")


async def start_scheduler(bot: Bot, check_interval: int = 3600):
    """
    Scheduler ni ishga tushirish

    Args:
        bot: Bot instance
        check_interval: Tekshirish oralig'i (sekundda), default 1 soat
    """
    logger.info(f"Premium scheduler ishga tushdi. Interval: {check_interval} sekund")

    while True:
        try:
            await check_premium_expiry(bot)
        except Exception as e:
            logger.error(f"Scheduler xatosi: {e}")

        await asyncio.sleep(check_interval)
