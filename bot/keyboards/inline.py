from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_inline_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Asosiy menyu - inline"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🔍 Kino qidirish", callback_data="search"))
    builder.row(
        InlineKeyboardButton(text="🔥 Top filmlar", callback_data="top_movies"),
        InlineKeyboardButton(text="👤 Profil", callback_data="profile")
    )
    builder.row(InlineKeyboardButton(text="💎 Premium olish", callback_data="premium"))

    # Admin tugmasi
    if is_admin:
        builder.row(InlineKeyboardButton(text="👨‍💼 Admin Panel", callback_data="admin:panel"))

    return builder.as_markup()


def channels_kb(channels: list, check: bool = True) -> InlineKeyboardMarkup:
    """Majburiy kanallar - chiroyli"""
    builder = InlineKeyboardBuilder()

    for channel in channels:
        builder.row(InlineKeyboardButton(
            text=f"📢 {channel.title}",
            url=channel.invite_link
        ))

    if check:
        builder.row(InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data="check_subscription"
        ))

    return builder.as_markup()


def categories_kb(categories: list) -> InlineKeyboardMarkup:
    """Kategoriyalar - chiroyli grid"""
    builder = InlineKeyboardBuilder()

    for category in categories:
        emoji = category.emoji if category.emoji else "📁"
        builder.button(text=f"{emoji} {category.name}", callback_data=f"category:{category.id}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))

    return builder.as_markup()


def admin_categories_kb(categories: list) -> InlineKeyboardMarkup:
    """Admin uchun kategoriyalar"""
    builder = InlineKeyboardBuilder()

    for category in categories:
        emoji = category.emoji if category.emoji else "📁"
        builder.button(text=f"{emoji} {category.name}", callback_data=f"admin_category:{category.id}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="admin_category:skip"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))

    return builder.as_markup()


def movies_kb(movies: list, page: int = 1, total_pages: int = 1, category_id: int = None) -> InlineKeyboardMarkup:
    """Kinolar ro'yxati - chiroyli pagination"""
    builder = InlineKeyboardBuilder()

    for movie in movies:
        if movie.is_premium:
            prefix = "💎 "
        else:
            prefix = "🎬 "
        builder.row(InlineKeyboardButton(
            text=f"{prefix}{movie.display_title} [{movie.code}]",
            callback_data=f"movie:{movie.code}"
        ))

    # Pagination
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Oldingi",
                callback_data=f"movies_page:{category_id}:{page - 1}"
            ))

        nav_buttons.append(InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data="noop"
        ))

        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                text="Keyingi ▶️",
                callback_data=f"movies_page:{category_id}:{page + 1}"
            ))

        builder.row(*nav_buttons)

    # Orqaga tugmasi
    if category_id:
        builder.row(InlineKeyboardButton(
            text="📂 Kategoriyalar",
            callback_data="categories"
        ))

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))

    return builder.as_markup()


def tariffs_kb(tariffs: list, with_discount: bool = False) -> InlineKeyboardMarkup:
    """Tariflar - chiroyli"""
    builder = InlineKeyboardBuilder()

    for tariff in tariffs:
        if with_discount and tariff.discounted_price:
            old_price = f"<s>{tariff.price:,}</s>"
            text = f"🎁 {tariff.name} • {tariff.discounted_price:,} so'm (-{tariff.discount_percent}%)"
        else:
            text = f"💎 {tariff.name} • {tariff.price:,} so'm"

        builder.row(InlineKeyboardButton(
            text=text,
            callback_data=f"tariff:{tariff.id}:{1 if with_discount else 0}"
        ))

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))

    return builder.as_markup()


def flash_sale_tariffs_kb(tariffs: list, is_discount: bool = True) -> InlineKeyboardMarkup:
    """Flash sale tariflar - 3 daqiqa ichida chegirma, keyin 2x narx"""
    builder = InlineKeyboardBuilder()

    for tariff in tariffs:
        original_price = tariff.price

        if is_discount:
            # Chegirmali narx (hozirgi narx)
            text = f"🔥 {tariff.name} • {original_price:,} so'm"
            # Callback da is_discount=1 yuboramiz
            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"flash_tariff:{tariff.id}:1"
            ))
        else:
            # 2x narx (chegirma tugadi)
            doubled_price = original_price * 2
            text = f"💎 {tariff.name} • {doubled_price:,} so'm"
            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"flash_tariff:{tariff.id}:0"
            ))

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))

    return builder.as_markup()


def payment_confirm_kb(payment_id: int) -> InlineKeyboardMarkup:
    """To'lovni tasdiqlash - admin"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_payment:{payment_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_payment:{payment_id}")
    )

    return builder.as_markup()


def broadcast_target_kb() -> InlineKeyboardMarkup:
    """Xabar yuborish maqsadi"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="👥 Hammaga", callback_data="broadcast_target:all"))
    builder.row(
        InlineKeyboardButton(text="💎 Premium", callback_data="broadcast_target:premium"),
        InlineKeyboardButton(text="👤 Oddiy", callback_data="broadcast_target:regular")
    )
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))

    return builder.as_markup()


def broadcast_ad_kb() -> InlineKeyboardMarkup:
    """Reklama xabarmi"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Ha", callback_data="broadcast_ad:yes"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="broadcast_ad:no")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cancel"))

    return builder.as_markup()


def confirm_broadcast_kb() -> InlineKeyboardMarkup:
    """Broadcast tasdiqlash"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    )

    return builder.as_markup()


def movie_quality_kb() -> InlineKeyboardMarkup:
    """Kino sifati - chiroyli"""
    builder = InlineKeyboardBuilder()

    qualities = [
        ("📱 360p", "360p"),
        ("📺 480p", "480p"),
        ("💻 720p HD", "720p"),
        ("🖥 1080p FHD", "1080p"),
        ("📽 4K Ultra", "4k"),
    ]

    for text, data in qualities:
        builder.button(text=text, callback_data=f"quality:{data}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))

    return builder.as_markup()


def movie_language_kb() -> InlineKeyboardMarkup:
    """Kino tili - chiroyli"""
    builder = InlineKeyboardBuilder()

    languages = [
        ("🇺🇿 O'zbekcha", "uzbek"),
        ("🇷🇺 Ruscha", "rus"),
        ("🇺🇸 Inglizcha", "eng"),
        ("🇹🇷 Turkcha", "turk"),
        ("🇰🇷 Koreyscha", "korea"),
        ("🌍 Boshqa", "other"),
    ]

    for text, data in languages:
        builder.button(text=text, callback_data=f"language:{data}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))

    return builder.as_markup()


def movie_country_kb() -> InlineKeyboardMarkup:
    """Kino davlati - chiroyli"""
    builder = InlineKeyboardBuilder()

    countries = [
        ("🇺🇸 AQSH", "usa"),
        ("🇰🇷 Koreya", "korea"),
        ("🇮🇳 Hindiston", "india"),
        ("🇹🇷 Turkiya", "turkey"),
        ("🇷🇺 Rossiya", "russia"),
        ("🇺🇿 O'zbekiston", "uzbekistan"),
        ("🇬🇧 Britaniya", "uk"),
        ("🇫🇷 Fransiya", "france"),
        ("🇯🇵 Yaponiya", "japan"),
        ("🇨🇳 Xitoy", "china"),
        ("🌍 Boshqa", "other"),
    ]

    for text, data in countries:
        builder.button(text=text, callback_data=f"country:{data}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))

    return builder.as_markup()


def back_kb() -> InlineKeyboardMarkup:
    """Orqaga inline tugma"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))
    return builder.as_markup()


def movie_action_kb(movie_code: str, is_saved: bool = False) -> InlineKeyboardMarkup:
    """Kino ko'rganda action tugmalari"""
    builder = InlineKeyboardBuilder()

    if is_saved:
        builder.row(InlineKeyboardButton(text="💔 Saqlanganlardan o'chirish", callback_data=f"unsave:{movie_code}"))
    else:
        builder.row(InlineKeyboardButton(text="❤️ Saqlash", callback_data=f"save:{movie_code}"))

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))
    return builder.as_markup()


def saved_movies_kb(movies: list, page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Saqlangan kinolar ro'yxati"""
    builder = InlineKeyboardBuilder()

    for movie in movies:
        premium = "💎 " if movie.is_premium else ""
        builder.row(InlineKeyboardButton(
            text=f"{premium}🎬 {movie.display_title}",
            callback_data=f"saved_movie:{movie.code}"
        ))

    # Pagination
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Oldingi",
                callback_data=f"saved_page:{page - 1}"
            ))

        nav_buttons.append(InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data="noop"
        ))

        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                text="Keyingi ▶️",
                callback_data=f"saved_page:{page + 1}"
            ))

        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))

    return builder.as_markup()


def cancel_inline_kb() -> InlineKeyboardMarkup:
    """Bekor qilish inline"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return builder.as_markup()


def search_filter_kb() -> InlineKeyboardMarkup:
    """Qidiruv filtrlari"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="📂 Janr bo'yicha", callback_data="filter:category"))
    builder.row(InlineKeyboardButton(text="🌍 Davlat bo'yicha", callback_data="filter:country"))
    builder.row(InlineKeyboardButton(text="🌐 Til bo'yicha", callback_data="filter:language"))
    builder.row(InlineKeyboardButton(text="📅 Yil bo'yicha", callback_data="filter:year"))
    builder.row(InlineKeyboardButton(text="🎲 Tasodifiy kino", callback_data="random_movie"))
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_menu"))

    return builder.as_markup()


def filter_country_kb() -> InlineKeyboardMarkup:
    """Davlat filtri"""
    builder = InlineKeyboardBuilder()

    countries = [
        ("🇺🇸 AQSH", "usa"),
        ("🇰🇷 Koreya", "korea"),
        ("🇮🇳 Hindiston", "india"),
        ("🇹🇷 Turkiya", "turkey"),
        ("🇷🇺 Rossiya", "russia"),
        ("🇺🇿 O'zbekiston", "uzbekistan"),
        ("🇯🇵 Yaponiya", "japan"),
        ("🇨🇳 Xitoy", "china"),
    ]

    for text, data in countries:
        builder.button(text=text, callback_data=f"filter_country:{data}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search"))

    return builder.as_markup()


def filter_language_kb() -> InlineKeyboardMarkup:
    """Til filtri"""
    builder = InlineKeyboardBuilder()

    languages = [
        ("🇺🇿 O'zbekcha", "uzbek"),
        ("🇷🇺 Ruscha", "rus"),
        ("🇺🇸 Inglizcha", "eng"),
        ("🇹🇷 Turkcha", "turk"),
        ("🇰🇷 Koreyscha", "korea"),
    ]

    for text, data in languages:
        builder.button(text=text, callback_data=f"filter_language:{data}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search"))

    return builder.as_markup()


def filter_year_kb() -> InlineKeyboardMarkup:
    """Yil filtri"""
    builder = InlineKeyboardBuilder()

    years = ["2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017"]

    for year in years:
        builder.button(text=year, callback_data=f"filter_year:{year}")

    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="search"))

    return builder.as_markup()


def skip_inline_kb() -> InlineKeyboardMarkup:
    """O'tkazib yuborish inline"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="skip"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return builder.as_markup()


def admin_main_kb() -> InlineKeyboardMarkup:
    """Admin asosiy menyu inline"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats"))
    builder.row(
        InlineKeyboardButton(text="🎬 Kinolar", callback_data="admin:movies"),
        InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin:add_movie")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Kanallar", callback_data="admin:channels"),
        InlineKeyboardButton(text="👥 Userlar", callback_data="admin:users")
    )
    builder.row(
        InlineKeyboardButton(text="💳 To'lovlar", callback_data="admin:payments"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin:settings")
    )
    builder.row(InlineKeyboardButton(text="📨 Xabar yuborish", callback_data="admin:broadcast"))
    builder.row(InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_menu"))
    return builder.as_markup()


