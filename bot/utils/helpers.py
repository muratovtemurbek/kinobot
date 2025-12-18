from datetime import datetime
from typing import Optional
from apps.users.models import User
from apps.channels.models import Channel
from asgiref.sync import sync_to_async


@sync_to_async
def get_or_create_user(user_id: int, username: Optional[str], full_name: str, referral_code: Optional[str] = None) -> User:
    """Foydalanuvchini olish yoki yaratish"""
    from apps.core.models import BotSettings
    from django.utils import timezone
    from datetime import timedelta

    user, created = User.objects.get_or_create(
        user_id=user_id,
        defaults={
            'username': username,
            'full_name': full_name,
        }
    )

    if not created:
        user.username = username
        user.full_name = full_name
        user.save(update_fields=['username', 'full_name', 'last_active'])
    elif referral_code and created:
        # Referal - faqat bog'lash, bonus VAQTINCHA O'CHIRILGAN
        try:
            referrer = User.objects.get(referral_code=referral_code)
            if referrer.user_id != user_id:
                user.referred_by = referrer
                user.save(update_fields=['referred_by'])

                # VAQTINCHA O'CHIRILGAN - Referrer'ga bonus berilmaydi
                # settings = BotSettings.get_settings()
                # if settings.referral_active and settings.referral_bonus > 0:
                #     bonus_days = settings.referral_bonus
                #     if referrer.free_trial_expires:
                #         if referrer.free_trial_expires > timezone.now():
                #             referrer.free_trial_expires += timedelta(days=bonus_days)
                #         else:
                #             referrer.free_trial_expires = timezone.now() + timedelta(days=bonus_days)
                #     else:
                #         referrer.free_trial_expires = timezone.now() + timedelta(days=bonus_days)
                #     referrer.save(update_fields=['free_trial_expires'])

        except User.DoesNotExist:
            pass

    return user


@sync_to_async
def get_user(user_id: int) -> Optional[User]:
    """Foydalanuvchini olish"""
    try:
        return User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        return None


@sync_to_async
def update_user_activity(user_id: int):
    """Foydalanuvchi faolligini yangilash"""
    User.objects.filter(user_id=user_id).update(last_active=datetime.now())


@sync_to_async
def get_active_channels():
    """Aktiv kanallarni olish"""
    return list(Channel.objects.filter(is_active=True).order_by('order'))


@sync_to_async
def get_checkable_channels():
    """Tekshirish mumkin bo'lgan kanallarni olish"""
    return list(Channel.objects.filter(
        is_active=True
    ).exclude(channel_type='external').exclude(channel_id__isnull=True).order_by('order'))


def format_number(num: int) -> str:
    """Raqamni formatlash"""
    return f"{num:,}".replace(",", " ")


def format_datetime(dt: datetime) -> str:
    """Sanani formatlash"""
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt: datetime) -> str:
    """Sanani formatlash (faqat kun)"""
    return dt.strftime("%d.%m.%Y")


@sync_to_async
def update_user_joined_channel(user_id: int, channel_id: int):
    """Foydalanuvchi qaysi kanal orqali kelganini yangilash"""
    try:
        user = User.objects.get(user_id=user_id)
        # Faqat birinchi marta yozish
        if not user.joined_from_channel_id:
            user.joined_from_channel_id = channel_id
            user.save(update_fields=['joined_from_channel_id'])
    except User.DoesNotExist:
        pass
