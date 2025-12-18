from datetime import timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.conf import settings

from apps.users.models import User
from apps.payments.models import Tariff, Payment
from apps.core.models import BotSettings
from bot.keyboards import tariffs_kb, main_menu_inline_kb, payment_confirm_kb, back_kb
from bot.filters import CanManagePayments

router = Router()


# ==================== TARIF TANLASH ====================

@router.callback_query(F.data.startswith("tariff:"))
async def tariff_select_callback(callback: CallbackQuery, db_user: User = None, bot_settings: BotSettings = None):
    """Tarif tanlash"""
    parts = callback.data.split(":")
    tariff_id = int(parts[1])
    with_discount = parts[2] == "1"

    tariff = await get_tariff(tariff_id)

    if not tariff:
        await callback.answer("❌ Tarif topilmadi.", show_alert=True)
        return

    # Narxni hisoblash
    if with_discount and tariff.discounted_price:
        price = tariff.discounted_price
        discount_text = f"\n🎁 Chegirma: -{tariff.discount_percent}%"
    else:
        price = tariff.price
        discount_text = ""

    text = (
        f"💳 <b>To'lov ma'lumotlari:</b>\n\n"
        f"📦 Tarif: <b>{tariff.name}</b>\n"
        f"📅 Muddat: <b>{tariff.days} kun</b>\n"
        f"💰 Narx: <b>{price:,} so'm</b>{discount_text}\n\n"
        f"💳 Karta: <code>{bot_settings.card_number}</code>\n"
        f"👤 Egasi: <b>{bot_settings.card_holder}</b>\n\n"
        f"📸 <b>To'lovni amalga oshiring va screenshot yuboring.</b>\n\n"
        f"⚠️ Izoh: Chekda <code>{callback.from_user.id}</code> ni ko'rsating."
    )

    # State ga tarif saqlash
    await callback.message.edit_text(text, reply_markup=back_kb())

    # Tarif ma'lumotlarini saqlash (keyingi xabar uchun)
    await save_pending_payment(
        callback.from_user.id,
        tariff_id,
        price,
        with_discount
    )

    await callback.answer()


# ==================== SCREENSHOT YUBORISH ====================

@router.message(F.photo)
async def screenshot_handler(message: Message, db_user: User = None, bot: Bot = None):
    """Screenshot qabul qilish"""
    # Pending payment tekshirish
    pending = await get_pending_payment(message.from_user.id)

    if not pending:
        # Oddiy rasm - e'tibor bermaslik
        return

    tariff = await get_tariff(pending['tariff_id'])

    if not tariff:
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    # Payment yaratish
    photo = message.photo[-1]

    payment = await create_payment(
        user_id=db_user.user_id,
        tariff_id=tariff.id,
        amount=pending['amount'],
        is_discounted=pending['with_discount'],
        screenshot_file_id=photo.file_id
    )

    # Pending o'chirish
    await delete_pending_payment(message.from_user.id)

    # User ga xabar
    await message.answer(
        "✅ <b>Chek qabul qilindi!</b>\n\n"
        "⏳ Admin tekshirib, tasdiqlagandan keyin Premium aktivlashadi.\n"
        "Odatda bu 5-30 daqiqa vaqt oladi.",
        reply_markup=back_kb()
    )

    # Adminga xabar
    admin_text = (
        f"💳 <b>Yangi to'lov!</b>\n\n"
        f"👤 Foydalanuvchi: {db_user.full_name}\n"
        f"🆔 ID: <code>{db_user.user_id}</code>\n"
        f"📦 Tarif: {tariff.name} ({tariff.days} kun)\n"
        f"💰 Summa: {pending['amount']:,} so'm\n"
        f"🎁 Chegirma: {'Ha' if pending['with_discount'] else 'Yoq'}\n"
    )

    for admin_id in settings.ADMINS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=admin_text,
                reply_markup=payment_confirm_kb(payment.id)
            )
        except Exception:
            pass


# ==================== TO'LOVNI TASDIQLASH ====================

@router.callback_query(F.data.startswith("approve_payment:"), CanManagePayments())
async def approve_payment_callback(callback: CallbackQuery, bot: Bot):
    """To'lovni tasdiqlash"""
    payment_id = int(callback.data.split(":")[1])

    payment = await get_payment(payment_id)

    if not payment:
        await callback.answer("❌ To'lov topilmadi.", show_alert=True)
        return

    if payment.status != 'pending':
        await callback.answer("⚠️ Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    # Tasdiqlash
    await approve_payment(payment_id, callback.from_user.id)

    await callback.answer("✅ To'lov tasdiqlandi!")

    # Xabarni yangilash
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>TASDIQLANDI</b>",
        reply_markup=None
    )

    # User ga xabar
    user = await get_user_by_pk(payment.user_id)
    tariff = await get_tariff(payment.tariff_id)

    try:
        await bot.send_message(
            chat_id=user.user_id,
            text=(
                f"🎉 <b>Premium aktivlashtirildi!</b>\n\n"
                f"📦 Tarif: {tariff.name}\n"
                f"📅 Muddat: {tariff.days} kun\n\n"
                f"Botdan foydalaning! 🎬"
            )
        )
    except Exception:
        pass


# ==================== TO'LOVNI RAD ETISH ====================

@router.callback_query(F.data.startswith("reject_payment:"), CanManagePayments())
async def reject_payment_callback(callback: CallbackQuery, bot: Bot):
    """To'lovni rad etish"""
    payment_id = int(callback.data.split(":")[1])

    payment = await get_payment(payment_id)

    if not payment:
        await callback.answer("❌ To'lov topilmadi.", show_alert=True)
        return

    if payment.status != 'pending':
        await callback.answer("⚠️ Bu to'lov allaqachon ko'rib chiqilgan.", show_alert=True)
        return

    # Rad etish
    await reject_payment(payment_id)

    await callback.answer("❌ To'lov rad etildi!")

    # Xabarni yangilash
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>RAD ETILDI</b>",
        reply_markup=None
    )

    # User ga xabar
    user = await get_user_by_pk(payment.user_id)

    try:
        await bot.send_message(
            chat_id=user.user_id,
            text=(
                "❌ <b>To'lov rad etildi!</b>\n\n"
                "Iltimos, to'g'ri chek yuboring yoki admin bilan bog'laning."
            )
        )
    except Exception:
        pass


# ==================== HELPER FUNCTIONS ====================

# In-memory pending payments storage with auto-cleanup
_pending_payments = {}
_PENDING_PAYMENT_TIMEOUT = 1800  # 30 daqiqa


def _cleanup_old_pending_payments():
    """Eski pending to'lovlarni tozalash (30 daqiqadan eski)"""
    from datetime import datetime
    now = timezone.now()
    expired_keys = []

    for user_id, data in _pending_payments.items():
        if 'timestamp' in data:
            if (now - data['timestamp']).total_seconds() > _PENDING_PAYMENT_TIMEOUT:
                expired_keys.append(user_id)

    for key in expired_keys:
        del _pending_payments[key]


@sync_to_async
def get_tariff(tariff_id: int):
    try:
        return Tariff.objects.get(id=tariff_id)
    except Tariff.DoesNotExist:
        return None


@sync_to_async
def create_payment(user_id: int, tariff_id: int, amount: int, is_discounted: bool, screenshot_file_id: str):
    user = User.objects.get(user_id=user_id)
    return Payment.objects.create(
        user=user,
        tariff_id=tariff_id,
        amount=amount,
        is_discounted=is_discounted,
        screenshot_file_id=screenshot_file_id
    )


@sync_to_async
def get_payment(payment_id: int):
    try:
        return Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return None


@sync_to_async
def approve_payment(payment_id: int, admin_user_id: int):
    payment = Payment.objects.get(id=payment_id)
    payment.status = 'approved'
    payment.approved_at = timezone.now()

    # Admin user olish
    try:
        admin_user = User.objects.get(user_id=admin_user_id)
        payment.approved_by = admin_user
    except User.DoesNotExist:
        pass

    payment.save()

    # Premium berish
    user = payment.user
    user.is_premium = True

    if user.premium_expires and user.premium_expires > timezone.now():
        user.premium_expires += timedelta(days=payment.tariff.days)
    else:
        user.premium_expires = timezone.now() + timedelta(days=payment.tariff.days)

    user.save()


@sync_to_async
def reject_payment(payment_id: int):
    Payment.objects.filter(id=payment_id).update(status='rejected')


@sync_to_async
def get_user_by_pk(pk: int):
    """User ni Django PK bo'yicha olish (payment.user_id uchun)"""
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        return None


async def save_pending_payment(user_id: int, tariff_id: int, amount: int, with_discount: bool):
    """Pending to'lovni saqlash"""
    # Har safar saqlashdan oldin eski to'lovlarni tozalash
    _cleanup_old_pending_payments()

    _pending_payments[user_id] = {
        'tariff_id': tariff_id,
        'amount': amount,
        'with_discount': with_discount,
        'timestamp': timezone.now()
    }


async def get_pending_payment(user_id: int):
    """Pending to'lovni olish"""
    # Eski to'lovlarni tozalash
    _cleanup_old_pending_payments()

    pending = _pending_payments.get(user_id)

    # Agar 30 daqiqadan eski bo'lsa - qaytarmaslik
    if pending and 'timestamp' in pending:
        if (timezone.now() - pending['timestamp']).total_seconds() > _PENDING_PAYMENT_TIMEOUT:
            del _pending_payments[user_id]
            return None

    return pending


async def delete_pending_payment(user_id: int):
    """Pending to'lovni o'chirish"""
    if user_id in _pending_payments:
        del _pending_payments[user_id]


def get_pending_payments_count() -> int:
    """Pending to'lovlar sonini olish (debug uchun)"""
    _cleanup_old_pending_payments()
    return len(_pending_payments)
