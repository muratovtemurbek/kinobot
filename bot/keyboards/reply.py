from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Asosiy menyu - chiroyli ko'rinish"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Kino qidirish")],
            [KeyboardButton(text="📂 Kategoriyalar"), KeyboardButton(text="🎬 Barcha kinolar")],
            [KeyboardButton(text="🔥 Top 10"), KeyboardButton(text="🆕 Yangilar")],
            [KeyboardButton(text="💎 Premium"), KeyboardButton(text="👤 Profil")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Kino kodini kiriting..."
    )


def admin_menu_kb() -> ReplyKeyboardMarkup:
    """Admin menyu - chiroyli ko'rinish"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🎬 Kinolar"), KeyboardButton(text="➕ Kino qo'shish")],
            [KeyboardButton(text="📢 Kanallar"), KeyboardButton(text="👥 Userlar")],
            [KeyboardButton(text="💳 To'lovlar"), KeyboardButton(text="⚙️ Sozlamalar")],
            [KeyboardButton(text="📨 Xabar yuborish")],
            [KeyboardButton(text="🏠 Asosiy menyu")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin panel"
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    """Bekor qilish"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


def back_kb() -> ReplyKeyboardMarkup:
    """Orqaga"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    """Tasdiqlash"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Tasdiqlash"), KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


def skip_kb() -> ReplyKeyboardMarkup:
    """O'tkazib yuborish"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


def contact_kb() -> ReplyKeyboardMarkup:
    """Kontakt so'rash"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
