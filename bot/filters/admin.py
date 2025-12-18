from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Union
from asgiref.sync import sync_to_async
from django.conf import settings

from apps.users.models import Admin


class IsAdmin(BaseFilter):
    """Admin filterı - Message va CallbackQuery uchun"""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user_id = event.from_user.id

        # 1. Avval settings.ADMINS ro'yxatini tekshirish (superadmin)
        if user_id in settings.ADMINS:
            return True

        # 2. Database'dagi Admin modelini tekshirish
        @sync_to_async
        def check_admin():
            return Admin.objects.filter(user__user_id=user_id).exists()

        return await check_admin()


class CanAddMovies(BaseFilter):
    """Kino qo'sha oladigan adminmi"""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user_id = event.from_user.id

        # Superadmin - hamma narsa mumkin
        if user_id in settings.ADMINS:
            return True

        @sync_to_async
        def check_permission():
            try:
                admin = Admin.objects.get(user__user_id=user_id)
                return admin.can_add_movies or admin.role in ['superadmin', 'admin']
            except Admin.DoesNotExist:
                return False

        return await check_permission()


class CanBroadcast(BaseFilter):
    """Xabar yuborish ruxsati bormi"""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user_id = event.from_user.id

        if user_id in settings.ADMINS:
            return True

        @sync_to_async
        def check_permission():
            try:
                admin = Admin.objects.get(user__user_id=user_id)
                return admin.can_broadcast or admin.role in ['superadmin', 'admin']
            except Admin.DoesNotExist:
                return False

        return await check_permission()


class CanManageUsers(BaseFilter):
    """Foydalanuvchilarni boshqarish ruxsati"""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user_id = event.from_user.id

        if user_id in settings.ADMINS:
            return True

        @sync_to_async
        def check_permission():
            try:
                admin = Admin.objects.get(user__user_id=user_id)
                return admin.can_manage_users or admin.role in ['superadmin', 'admin']
            except Admin.DoesNotExist:
                return False

        return await check_permission()


class CanManagePayments(BaseFilter):
    """To'lovlarni boshqarish ruxsati"""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user_id = event.from_user.id

        if user_id in settings.ADMINS:
            return True

        @sync_to_async
        def check_permission():
            try:
                admin = Admin.objects.get(user__user_id=user_id)
                return admin.can_manage_payments or admin.role in ['superadmin', 'admin']
            except Admin.DoesNotExist:
                return False

        return await check_permission()


class IsSuperAdmin(BaseFilter):
    """Faqat superadmin"""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user_id = event.from_user.id

        # settings.ADMINS - superadminlar
        if user_id in settings.ADMINS:
            return True

        @sync_to_async
        def check_superadmin():
            try:
                admin = Admin.objects.get(user__user_id=user_id)
                return admin.role == 'superadmin'
            except Admin.DoesNotExist:
                return False

        return await check_superadmin()
