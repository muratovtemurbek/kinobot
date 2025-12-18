import random
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from asgiref.sync import sync_to_async
from cachetools import TTLCache
from django.conf import settings

from apps.users.models import User, Admin
from apps.movies.models import Movie, Category
from apps.channels.models import Channel
from apps.payments.models import Tariff
from bot.keyboards import (
    main_menu_inline_kb, channels_kb, categories_kb, movies_kb,
    tariffs_kb, back_kb, movie_action_kb, saved_movies_kb,
    search_filter_kb, filter_country_kb, filter_language_kb, filter_year_kb,
    flash_sale_tariffs_kb
)
from bot.utils import get_or_create_user, format_number, format_date, update_user_joined_channel


async def is_user_admin(user_id: int) -> bool:
    """Foydalanuvchi adminmi tekshirish"""
    # 1. settings.ADMINS ro'yxatini tekshirish
    if user_id in settings.ADMINS:
        return True

    # 2. Database'dagi Admin modelini tekshirish
    @sync_to_async
    def check_db():
        return Admin.objects.filter(user__user_id=user_id).exists()

    return await check_db()

router = Router()

# Cache
_movies_cache = TTLCache(maxsize=100, ttl=120)
_categories_cache = TTLCache(maxsize=1, ttl=300)


# ==================== START ====================

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Start buyrug'i"""
    user = message.from_user

    referral_code = None
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]

    db_user = await get_or_create_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        referral_code=referral_code
    )

    not_subscribed = await check_subscription(bot, user.id)

    # Admin tekshirish
    is_admin = await is_user_admin(user.id)

    if not_subscribed and not is_admin:
        await message.answer(
            f"👋 Salom, <b>{user.full_name}</b>!\n\n"
            "📢 Botdan foydalanish uchun kanallarga obuna bo'ling:\n\n"
            "✅ <b>Tekshirish</b> tugmasini bosing.",
            reply_markup=channels_kb(not_subscribed)
        )
        return

    status = ""
    if db_user.is_premium_active:
        status = "💎 Premium\n\n"
    elif db_user.is_trial_active:
        status = "🎁 Trial\n\n"

    await message.answer(
        f"👋 Salom, <b>{user.full_name}</b>!\n\n"
        f"{status}"
        "🎬 Kino kodini yuboring yoki menyu tugmalaridan foydalaning:",
        reply_markup=main_menu_inline_kb(is_admin=is_admin)
    )


# ==================== OBUNA TEKSHIRISH ====================

@router.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: CallbackQuery, bot: Bot):
    """Obunani tekshirish"""
    from bot.middlewares.subscription import clear_subscription_cache

    user = callback.from_user

    # Cache ni tozalash - yangi tekshirish uchun
    clear_subscription_cache(user.id)

    not_subscribed = await check_subscription(bot, user.id)

    if not_subscribed:
        await callback.answer("❌ Barcha kanallarga obuna bo'ling!", show_alert=True)
        # Kanallar ro'yxatini yangilash
        try:
            await callback.message.edit_text(
                "📢 <b>Kanallarga obuna bo'ling:</b>\n\n"
                "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing.",
                reply_markup=channels_kb(not_subscribed)
            )
        except TelegramBadRequest:
            pass  # Xabar o'zgartirilmagan
        return

    await callback.answer("✅ Tasdiqlandi!")

    # Birinchi marta obuna bo'lgan kanal statistikasi uchun
    all_channels = await get_active_channels()
    if all_channels:
        # Birinchi kanalni saqlaymiz
        await update_user_joined_channel(user.id, all_channels[0].id)

    is_admin = await is_user_admin(user.id)

    try:
        await callback.message.edit_text(
            f"✅ Obuna tasdiqlandi!\n\n"
            "🎬 Kino kodini yuboring:",
            reply_markup=main_menu_inline_kb(is_admin=is_admin)
        )
    except TelegramBadRequest:
        pass  # Xabar o'zgartirilmagan


# ==================== BACK TO MENU ====================

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery):
    """Menyuga qaytish"""
    is_admin = await is_user_admin(callback.from_user.id)

    try:
        await callback.message.edit_text(
            "🏠 <b>Asosiy menyu</b>\n\n"
            "🎬 Kino kodini yuboring yoki menyu tugmalaridan foydalaning:",
            reply_markup=main_menu_inline_kb(is_admin=is_admin)
        )
    except TelegramBadRequest:
        # Video/rasm xabarini edit qilib bo'lmaydi - yangi xabar yuborish
        await callback.message.answer(
            "🏠 <b>Asosiy menyu</b>\n\n"
            "🎬 Kino kodini yuboring yoki menyu tugmalaridan foydalaning:",
            reply_markup=main_menu_inline_kb(is_admin=is_admin)
        )
    await callback.answer()


# ==================== KINO OLISH ====================

@router.message(F.text.regexp(r'^\d+$'), StateFilter(None))
async def get_movie_by_code(message: Message, db_user: User = None, bot: Bot = None):
    """Kod bo'yicha kino olish"""
    from bot.middlewares.subscription import clear_subscription_cache
    import logging
    logger = logging.getLogger(__name__)

    # Obunani tekshirish (middleware dan tashqari qo'shimcha tekshiruv)
    user_id = message.from_user.id

    logger.info(f"Kino kod so'rovi: user_id={user_id}, is_admin={user_id in settings.ADMINS}")

    # Admin bo'lmasa tekshirish
    if user_id not in settings.ADMINS:
        # Premium bo'lmasa tekshirish
        is_premium = db_user and db_user.is_premium_active
        logger.info(f"Premium tekshiruv: db_user={db_user}, is_premium={is_premium}")

        if not is_premium:
            clear_subscription_cache(user_id)
            not_subscribed = await check_subscription(bot, user_id)

            logger.info(f"Obuna tekshiruv: not_subscribed={len(not_subscribed) if not_subscribed else 0} ta kanal")

            if not_subscribed:
                await message.answer(
                    "📢 <b>Kino ko'rish uchun kanallarga obuna bo'ling:</b>\n\n"
                    "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing.",
                    reply_markup=channels_kb(not_subscribed)
                )
                return
    else:
        logger.info(f"Admin - obuna tekshirilmaydi")

    code = message.text.strip()

    movie = await get_movie_by_code_db(code)

    if not movie:
        await message.answer(
            f"❌ <code>{code}</code> kodli kino topilmadi.\n\n"
            "🔍 Kodni tekshirib qaytadan yuboring.",
            reply_markup=back_kb()
        )
        return

    if not movie.is_active:
        await message.answer(
            "❌ Bu kino hozircha mavjud emas.",
            reply_markup=back_kb()
        )
        return

    # Premium check
    if movie.is_premium and db_user and not db_user.is_premium_active and not db_user.is_trial_active:
        is_admin = await is_user_admin(message.from_user.id)
        await message.answer(
            f"💎 <b>{movie.display_title}</b>\n\n"
            "Bu kino faqat Premium foydalanuvchilar uchun.\n\n"
            "Premium olish uchun 💎 Premium tugmasini bosing.",
            reply_markup=main_menu_inline_kb(is_admin=is_admin)
        )
        return

    # Send movie
    try:
        bot_info = await bot.me()
        bot_link = f"https://t.me/{bot_info.username}"

        desc = f"\n\n📖 {movie.description}" if movie.description else ""
        year_text = f"📅 Yil: {movie.year}\n" if movie.year else ""
        country_text = f"🌍 Davlat: {movie.get_country_display()}\n" if hasattr(movie, 'get_country_display') else ""

        caption = (
            f"🎬 <b>{movie.display_title}</b>{desc}\n\n"
            f"📝 Kod: <code>{movie.code}</code>\n"
            f"{year_text}"
            f"{country_text}"
            f"📺 Sifat: {movie.get_quality_display()}\n"
            f"🌐 Til: {movie.get_language_display()}\n"
            f"👁 Ko'rishlar: {format_number(movie.views)}\n\n"
            f"🤖 <b>Bot:</b> {bot_link}"
        )

        # Saqlangan yoki yo'qligini tekshirish
        is_saved = await check_movie_saved(message.from_user.id, movie.code) if db_user else False

        await message.answer_video(
            video=movie.file_id,
            caption=caption,
            reply_markup=movie_action_kb(movie.code, is_saved)
        )

        # Update stats
        await increment_movie_views(movie.id)
        if db_user:
            await increment_user_movies(db_user.user_id)

    except TelegramBadRequest:
        await message.answer("❌ Kino faylida xatolik.", reply_markup=back_kb())


# ==================== QIDIRISH ====================

@router.callback_query(F.data == "search")
async def search_callback(callback: CallbackQuery):
    """Qidirish"""
    await callback.message.edit_text(
        "🔍 <b>Kino qidirish</b>\n\n"
        "Kino kodini yuboring yoki filter tanlang:\n"
        "Masalan: <code>123</code>",
        reply_markup=search_filter_kb()
    )
    await callback.answer()


# ==================== FILTRLAR ====================

@router.callback_query(F.data == "filter:category")
async def filter_category_callback(callback: CallbackQuery):
    """Janr bo'yicha filter"""
    categories = await get_categories()

    if not categories:
        await callback.answer("📭 Kategoriyalar yo'q", show_alert=True)
        return

    await callback.message.edit_text(
        "📂 <b>Janr tanlang:</b>",
        reply_markup=categories_kb(categories)
    )
    await callback.answer()


@router.callback_query(F.data == "filter:country")
async def filter_country_callback(callback: CallbackQuery):
    """Davlat bo'yicha filter"""
    await callback.message.edit_text(
        "🌍 <b>Davlat tanlang:</b>",
        reply_markup=filter_country_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "filter:language")
async def filter_language_callback(callback: CallbackQuery):
    """Til bo'yicha filter"""
    await callback.message.edit_text(
        "🌐 <b>Til tanlang:</b>",
        reply_markup=filter_language_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "filter:year")
async def filter_year_callback(callback: CallbackQuery):
    """Yil bo'yicha filter"""
    await callback.message.edit_text(
        "📅 <b>Yil tanlang:</b>",
        reply_markup=filter_year_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_country:"))
async def filter_country_result_callback(callback: CallbackQuery):
    """Davlat bo'yicha natijalar"""
    country = callback.data.split(":")[1]
    movies, total_pages = await get_movies_by_filter(country=country, page=1)

    country_names = {
        'usa': '🇺🇸 AQSH', 'korea': '🇰🇷 Koreya', 'india': '🇮🇳 Hindiston',
        'turkey': '🇹🇷 Turkiya', 'russia': '🇷🇺 Rossiya', 'uzbekistan': '🇺🇿 O\'zbekiston',
        'japan': '🇯🇵 Yaponiya', 'china': '🇨🇳 Xitoy'
    }
    country_name = country_names.get(country, country)

    if not movies:
        await callback.answer(f"📭 {country_name} kinolari topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        f"🌍 <b>{country_name} kinolari:</b>\n\n"
        f"Jami: {len(movies)} ta",
        reply_markup=movies_kb(movies, page=1, total_pages=total_pages)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_language:"))
async def filter_language_result_callback(callback: CallbackQuery):
    """Til bo'yicha natijalar"""
    language = callback.data.split(":")[1]
    movies, total_pages = await get_movies_by_filter(language=language, page=1)

    lang_names = {
        'uzbek': "🇺🇿 O'zbekcha", 'rus': '🇷🇺 Ruscha', 'eng': '🇺🇸 Inglizcha',
        'turk': '🇹🇷 Turkcha', 'korea': '🇰🇷 Koreyscha'
    }
    lang_name = lang_names.get(language, language)

    if not movies:
        await callback.answer(f"📭 {lang_name} kinolar topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        f"🌐 <b>{lang_name} kinolar:</b>\n\n"
        f"Jami: {len(movies)} ta",
        reply_markup=movies_kb(movies, page=1, total_pages=total_pages)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_year:"))
async def filter_year_result_callback(callback: CallbackQuery):
    """Yil bo'yicha natijalar"""
    year = int(callback.data.split(":")[1])
    movies, total_pages = await get_movies_by_filter(year=year, page=1)

    if not movies:
        await callback.answer(f"📭 {year}-yil kinolari topilmadi", show_alert=True)
        return

    await callback.message.edit_text(
        f"📅 <b>{year}-yil kinolari:</b>\n\n"
        f"Jami: {len(movies)} ta",
        reply_markup=movies_kb(movies, page=1, total_pages=total_pages)
    )
    await callback.answer()


# ==================== TOP KINOLAR ====================

@router.callback_query(F.data == "top_movies")
async def top_movies_callback(callback: CallbackQuery):
    """Top kinolar"""
    movies = await get_top_movies(10)

    if not movies:
        await callback.answer("📭 Kinolar topilmadi.", show_alert=True)
        return

    text = "🔥 <b>Top 10 kinolar:</b>\n\n"
    for i, movie in enumerate(movies, 1):
        text += f"{i}. 🎬 <b>{movie.display_title}</b>\n"
        text += f"    📝 Kod: <code>{movie.code}</code> • 👁 {format_number(movie.views)}\n\n"

    text += "📥 Kino olish uchun kodini yuboring."

    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()


@router.message(Command("top"))
async def top_movies_handler(message: Message):
    """Top kinolar command"""
    movies = await get_top_movies(10)

    if not movies:
        await message.answer("📭 Kinolar topilmadi.")
        return

    text = "🔥 <b>Top 10 kinolar:</b>\n\n"
    for i, movie in enumerate(movies, 1):
        text += f"{i}. 🎬 <b>{movie.display_title}</b>\n"
        text += f"    📝 Kod: <code>{movie.code}</code> • 👁 {format_number(movie.views)}\n\n"

    text += "📥 Kino olish uchun kodini yuboring."

    await message.answer(text, reply_markup=back_kb())


# ==================== YANGI KINOLAR ====================

@router.callback_query(F.data == "new_movies")
async def new_movies_callback(callback: CallbackQuery):
    """Yangi kinolar"""
    movies = await get_last_movies(10)

    if not movies:
        await callback.answer("📭 Kinolar topilmadi.", show_alert=True)
        return

    text = "🆕 <b>Yangi kinolar:</b>\n\n"
    for movie in movies:
        premium = "💎 " if movie.is_premium else ""
        text += f"{premium}🎬 <b>{movie.display_title}</b>\n"
        text += f"    📝 Kod: <code>{movie.code}</code>\n\n"

    text += "📥 Kino olish uchun kodini yuboring."

    await callback.message.edit_text(text, reply_markup=back_kb())
    await callback.answer()


@router.message(Command("last"))
async def last_movies_handler(message: Message):
    """Yangi kinolar command"""
    movies = await get_last_movies(10)

    if not movies:
        await message.answer("📭 Kinolar topilmadi.")
        return

    text = "🆕 <b>Yangi kinolar:</b>\n\n"
    for movie in movies:
        premium = "💎 " if movie.is_premium else ""
        text += f"{premium}🎬 <b>{movie.display_title}</b>\n"
        text += f"    📝 Kod: <code>{movie.code}</code>\n\n"

    text += "📥 Kino olish uchun kodini yuboring."

    await message.answer(text, reply_markup=back_kb())


# ==================== RANDOM KINO ====================

@router.message(Command("rand"))
async def random_movie_handler(message: Message, db_user: User = None, bot: Bot = None):
    """Random kino"""
    from bot.middlewares.subscription import clear_subscription_cache

    user_id = message.from_user.id

    # Obunani tekshirish
    if user_id not in settings.ADMINS:
        if not db_user or not db_user.is_premium_active:
            clear_subscription_cache(user_id)
            not_subscribed = await check_subscription(bot, user_id)

            if not_subscribed:
                await message.answer(
                    "📢 <b>Kino ko'rish uchun kanallarga obuna bo'ling:</b>\n\n"
                    "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing.",
                    reply_markup=channels_kb(not_subscribed)
                )
                return

    movie = await get_random_movie()

    if not movie:
        await message.answer("📭 Kinolar topilmadi.", reply_markup=back_kb())
        return

    if movie.is_premium and db_user and not db_user.is_premium_active:
        is_admin = await is_user_admin(message.from_user.id)
        await message.answer(
            f"💎 <b>{movie.display_title}</b>\n\n"
            "Premium kino tushdi! Premium olish uchun 💎 Premium tugmasini bosing.",
            reply_markup=main_menu_inline_kb(is_admin=is_admin)
        )
        return

    try:
        bot_info = await bot.me()
        bot_link = f"https://t.me/{bot_info.username}"

        desc = f"\n📖 {movie.description}" if movie.description else ""
        year_text = f" • 📅 {movie.year}" if movie.year else ""

        await message.answer_video(
            video=movie.file_id,
            caption=(
                f"🎲 <b>Random kino:</b>\n\n"
                f"🎬 <b>{movie.display_title}</b>{desc}\n\n"
                f"📝 Kod: <code>{movie.code}</code>\n"
                f"📺 {movie.get_quality_display()} • 🌐 {movie.get_language_display()}{year_text}\n\n"
                f"🤖 <b>Bot:</b> {bot_link}"
            ),
            reply_markup=back_kb()
        )
        await increment_movie_views(movie.id)
    except TelegramBadRequest:
        await message.answer("❌ Xatolik yuz berdi.", reply_markup=back_kb())


# ==================== BARCHA KINOLAR ====================

@router.callback_query(F.data == "all_movies")
async def all_movies_callback(callback: CallbackQuery):
    """Barcha kinolar"""
    movies, total_pages = await get_all_movies(page=1)

    if not movies:
        await callback.answer("📭 Kinolar topilmadi.", show_alert=True)
        return

    await callback.message.edit_text(
        "🎬 <b>Barcha kinolar</b>\n\nTanlang:",
        reply_markup=movies_kb(movies, page=1, total_pages=total_pages)
    )
    await callback.answer()


@router.message(Command("movies"))
async def all_movies_handler(message: Message):
    """Barcha kinolar command"""
    movies, total_pages = await get_all_movies(page=1)

    if not movies:
        await message.answer("📭 Kinolar topilmadi.")
        return

    await message.answer(
        "🎬 <b>Barcha kinolar</b>\n\nTanlang:",
        reply_markup=movies_kb(movies, page=1, total_pages=total_pages)
    )


# ==================== KATEGORIYALAR ====================

@router.callback_query(F.data == "categories")
async def categories_callback(callback: CallbackQuery):
    """Kategoriyalar"""
    categories = await get_categories()

    if not categories:
        await callback.answer("📭 Kategoriyalar topilmadi.", show_alert=True)
        return

    await callback.message.edit_text(
        "📂 <b>Kategoriyalar</b>\n\nTanlang:",
        reply_markup=categories_kb(categories)
    )
    await callback.answer()


@router.message(Command("categories"))
async def categories_handler(message: Message):
    """Kategoriyalar command"""
    categories = await get_categories()

    if not categories:
        await message.answer("📭 Kategoriyalar topilmadi.")
        return

    await message.answer(
        "📂 <b>Kategoriyalar</b>\n\nTanlang:",
        reply_markup=categories_kb(categories)
    )


# ==================== KATEGORIYA BO'YICHA ====================

@router.callback_query(F.data.startswith("category:"))
async def category_movies_callback(callback: CallbackQuery):
    """Kategoriya bo'yicha kinolar"""
    category_id = int(callback.data.split(":")[1])

    movies, total_pages, category_name = await get_movies_by_category(category_id, page=1)

    if not movies:
        await callback.answer("📭 Bu kategoriyada kinolar yo'q.", show_alert=True)
        return

    await callback.message.edit_text(
        f"📂 <b>{category_name}</b>\n\nTanlang:",
        reply_markup=movies_kb(movies, page=1, total_pages=total_pages, category_id=category_id)
    )
    await callback.answer()


# ==================== PAGINATION ====================

@router.callback_query(F.data.startswith("movies_page:"))
async def movies_page_callback(callback: CallbackQuery):
    """Kinolar pagination"""
    parts = callback.data.split(":")
    category_id = int(parts[1]) if parts[1] != 'None' else None
    page = int(parts[2])

    if category_id:
        movies, total_pages, category_name = await get_movies_by_category(category_id, page=page)
        title = f"📂 <b>{category_name}</b>"
    else:
        movies, total_pages = await get_all_movies(page=page)
        title = "🎬 <b>Barcha kinolar</b>"

    await callback.message.edit_text(
        f"{title}\n\nTanlang:",
        reply_markup=movies_kb(movies, page=page, total_pages=total_pages, category_id=category_id)
    )
    await callback.answer()


# ==================== KINO TANLASH ====================

@router.callback_query(F.data.startswith("movie:"))
async def movie_callback(callback: CallbackQuery, db_user: User = None, bot: Bot = None):
    """Kinoni tanlash"""
    from bot.middlewares.subscription import clear_subscription_cache

    user_id = callback.from_user.id

    # Obunani tekshirish (admin va premium dan tashqari)
    if user_id not in settings.ADMINS:
        if not db_user or not db_user.is_premium_active:
            clear_subscription_cache(user_id)
            not_subscribed = await check_subscription(bot, user_id)

            if not_subscribed:
                await callback.answer("❌ Avval kanallarga obuna bo'ling!", show_alert=True)
                await callback.message.answer(
                    "📢 <b>Kino ko'rish uchun kanallarga obuna bo'ling:</b>\n\n"
                    "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing.",
                    reply_markup=channels_kb(not_subscribed)
                )
                return

    code = callback.data.split(":")[1]

    movie = await get_movie_by_code_db(code)

    if not movie:
        await callback.answer("❌ Kino topilmadi.", show_alert=True)
        return

    if movie.is_premium and db_user and not db_user.is_premium_active:
        await callback.answer("💎 Bu Premium kino!", show_alert=True)
        return

    await callback.answer()

    try:
        bot_info = await bot.me()
        bot_link = f"https://t.me/{bot_info.username}"

        desc = f"\n📖 {movie.description}" if movie.description else ""
        year_text = f" • 📅 {movie.year}" if movie.year else ""

        await callback.message.answer_video(
            video=movie.file_id,
            caption=(
                f"🎬 <b>{movie.display_title}</b>{desc}\n\n"
                f"📝 Kod: <code>{movie.code}</code>\n"
                f"📺 {movie.get_quality_display()} • 🌐 {movie.get_language_display()}{year_text}\n"
                f"👁 {format_number(movie.views)}\n\n"
                f"🤖 <b>Bot:</b> {bot_link}"
            ),
            reply_markup=back_kb()
        )
        await increment_movie_views(movie.id)
        if db_user:
            await increment_user_movies(db_user.user_id)
    except TelegramBadRequest:
        await callback.message.answer("❌ Xatolik.", reply_markup=back_kb())


# ==================== PREMIUM ====================

@router.callback_query(F.data == "premium")
async def premium_callback(callback: CallbackQuery, db_user: User = None):
    """Premium"""
    if db_user and db_user.is_premium_active:
        await callback.message.edit_text(
            f"💎 <b>Sizda Premium mavjud!</b>\n\n"
            f"📅 Amal qilish muddati: {db_user.premium_expires.strftime('%d.%m.%Y')}\n"
            f"⏳ Qolgan kunlar: {db_user.days_left}",
            reply_markup=back_kb()
        )
        await callback.answer()
        return

    tariffs = await get_tariffs()

    if not tariffs:
        await callback.answer("📭 Tariflar mavjud emas.", show_alert=True)
        return

    # Flash sale - 3 daqiqa ichida chegirma
    is_flash_sale = True
    seconds_left = 180

    if db_user:
        # Birinchi ko'rishni qayd qilish
        if not db_user.premium_first_view:
            await set_premium_first_view(db_user.user_id)
            is_flash_sale = True
            seconds_left = 180
        else:
            is_flash_sale = db_user.is_flash_sale_active
            seconds_left = db_user.flash_sale_seconds_left

    if is_flash_sale:
        minutes = seconds_left // 60
        secs = seconds_left % 60
        timer_text = f"⏰ <b>CHEGIRMA!</b> Vaqt: {minutes}:{secs:02d}\n\n"
        text = (
            f"🔥 <b>FLASH SALE!</b> 🔥\n\n"
            f"{timer_text}"
            "💎 <b>Premium afzalliklari:</b>\n\n"
            "✅ Barcha kinolarga kirish\n"
            "✅ Reklamasiz foydalanish\n"
            "✅ Tezkor yuklash\n\n"
            "⚡ <b>3 daqiqa ichida chegirmali narxda oling!</b>\n\n"
            "📦 Tarifni tanlang:"
        )
        await callback.message.edit_text(text, reply_markup=flash_sale_tariffs_kb(tariffs, is_discount=True))
    else:
        text = (
            "💎 <b>Premium afzalliklari:</b>\n\n"
            "✅ Barcha kinolarga kirish\n"
            "✅ Reklamasiz foydalanish\n"
            "✅ Tezkor yuklash\n\n"
            "📦 Tarifni tanlang:"
        )
        await callback.message.edit_text(text, reply_markup=flash_sale_tariffs_kb(tariffs, is_discount=False))

    await callback.answer()


@router.message(Command("premium"))
async def premium_handler(message: Message, db_user: User = None):
    """Premium command"""
    if db_user and db_user.is_premium_active:
        await message.answer(
            f"💎 <b>Sizda Premium mavjud!</b>\n\n"
            f"📅 Amal qilish muddati: {db_user.premium_expires.strftime('%d.%m.%Y')}\n"
            f"⏳ Qolgan kunlar: {db_user.days_left}",
            reply_markup=back_kb()
        )
        return

    tariffs = await get_tariffs()

    if not tariffs:
        await message.answer("📭 Tariflar mavjud emas.")
        return

    # Flash sale
    is_flash_sale = True
    seconds_left = 180

    if db_user:
        if not db_user.premium_first_view:
            await set_premium_first_view(db_user.user_id)
        else:
            is_flash_sale = db_user.is_flash_sale_active
            seconds_left = db_user.flash_sale_seconds_left

    if is_flash_sale:
        minutes = seconds_left // 60
        secs = seconds_left % 60
        await message.answer(
            f"🔥 <b>FLASH SALE!</b> 🔥\n\n"
            f"⏰ <b>CHEGIRMA!</b> Vaqt: {minutes}:{secs:02d}\n\n"
            "💎 <b>Premium afzalliklari:</b>\n\n"
            "✅ Barcha kinolarga kirish\n"
            "✅ Reklamasiz foydalanish\n"
            "✅ Tezkor yuklash\n\n"
            "⚡ <b>3 daqiqa ichida chegirmali narxda oling!</b>\n\n"
            "📦 Tarifni tanlang:",
            reply_markup=flash_sale_tariffs_kb(tariffs, is_discount=True)
        )
    else:
        await message.answer(
            "💎 <b>Premium afzalliklari:</b>\n\n"
            "✅ Barcha kinolarga kirish\n"
            "✅ Reklamasiz foydalanish\n"
            "✅ Tezkor yuklash\n\n"
            "📦 Tarifni tanlang:",
            reply_markup=flash_sale_tariffs_kb(tariffs, is_discount=False)
        )


@router.callback_query(F.data.startswith("flash_tariff:"))
async def flash_tariff_callback(callback: CallbackQuery, db_user: User = None):
    """Flash sale tarif tanlash"""
    parts = callback.data.split(":")
    tariff_id = int(parts[1])
    is_discount = parts[2] == "1"

    tariff = await get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("❌ Tarif topilmadi!", show_alert=True)
        return

    # Narxni hisoblash
    if is_discount and db_user and db_user.is_flash_sale_active:
        # Chegirmali narx (hozirgi narx)
        price = tariff.price
        price_text = f"{price:,} so'm (chegirmali!)"
    else:
        # 2x narx
        price = tariff.price * 2
        price_text = f"{price:,} so'm"

    # Karta ma'lumotlarini olish
    from apps.core.models import BotSettings
    settings = await get_bot_settings()

    await callback.message.edit_text(
        f"💳 <b>To'lov</b>\n\n"
        f"📦 Tarif: {tariff.name}\n"
        f"⏳ Muddat: {tariff.days} kun\n"
        f"💰 Narxi: <b>{price_text}</b>\n\n"
        f"📋 <b>Karta ma'lumotlari:</b>\n"
        f"💳 {settings.card_number if settings else '8600 1234 5678 9012'}\n"
        f"👤 {settings.card_holder if settings else 'CARDHOLDER NAME'}\n\n"
        f"✅ To'lovni amalga oshiring va chekni yuboring:",
        reply_markup=back_kb()
    )
    await callback.answer()


# ==================== PROFIL ====================

@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery, db_user: User = None):
    """Profil"""
    if not db_user:
        await callback.answer("❌ Xatolik.", show_alert=True)
        return

    if db_user.is_premium_active:
        status = f"💎 Premium ({db_user.days_left} kun)"
    elif db_user.is_trial_active:
        status = f"🎁 Trial ({db_user.days_left} kun)"
    else:
        status = "👤 Oddiy"

    referrals_count = await get_referrals_count(db_user.user_id)
    bot_username = (await callback.bot.me()).username

    await callback.message.edit_text(
        f"👤 <b>Profil</b>\n\n"
        f"🆔 ID: <code>{db_user.user_id}</code>\n"
        f"👤 Ism: {db_user.full_name}\n"
        f"📊 Status: {status}\n"
        f"🎬 Ko'rilgan: {format_number(db_user.movies_watched)}\n\n"
        f"🔗 <b>Referal:</b>\n"
        f"Kod: <code>{db_user.referral_code}</code>\n"
        f"Taklif qilganlar: {referrals_count} ta\n\n"
        f"📎 Havolangiz:\n"
        f"https://t.me/{bot_username}?start={db_user.referral_code}",
        reply_markup=back_kb()
    )
    await callback.answer()


@router.message(Command("profile"))
async def profile_handler(message: Message, db_user: User = None):
    """Profil command"""
    if not db_user:
        await message.answer("❌ Xatolik.")
        return

    if db_user.is_premium_active:
        status = f"💎 Premium ({db_user.days_left} kun)"
    elif db_user.is_trial_active:
        status = f"🎁 Trial ({db_user.days_left} kun)"
    else:
        status = "👤 Oddiy"

    referrals_count = await get_referrals_count(db_user.user_id)
    bot_username = (await message.bot.me()).username

    await message.answer(
        f"👤 <b>Profil</b>\n\n"
        f"🆔 ID: <code>{db_user.user_id}</code>\n"
        f"👤 Ism: {db_user.full_name}\n"
        f"📊 Status: {status}\n"
        f"🎬 Ko'rilgan: {format_number(db_user.movies_watched)}\n\n"
        f"🔗 <b>Referal:</b>\n"
        f"Kod: <code>{db_user.referral_code}</code>\n"
        f"Taklif qilganlar: {referrals_count} ta\n\n"
        f"📎 Havolangiz:\n"
        f"https://t.me/{bot_username}?start={db_user.referral_code}",
        reply_markup=back_kb()
    )


# ==================== NOOP ====================

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """No operation"""
    await callback.answer()


# ==================== SAQLANGAN KINOLAR ====================

@router.callback_query(F.data == "saved_movies")
async def saved_movies_callback(callback: CallbackQuery, db_user: User = None):
    """Saqlangan kinolar"""
    if not db_user:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    movies, total_pages = await get_saved_movies(db_user.user_id, page=1)

    if not movies:
        await callback.message.edit_text(
            "❤️ <b>Saqlangan kinolar</b>\n\n"
            "📭 Sizda hali saqlangan kinolar yo'q.\n\n"
            "Kino ko'rganingizda ❤️ Saqlash tugmasini bosing.",
            reply_markup=back_kb()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"❤️ <b>Saqlangan kinolar</b>\n\n"
        f"Jami: {len(movies)} ta kino\n"
        "Tanlang:",
        reply_markup=saved_movies_kb(movies, page=1, total_pages=total_pages)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("saved_page:"))
async def saved_movies_page_callback(callback: CallbackQuery, db_user: User = None):
    """Saqlangan kinolar pagination"""
    if not db_user:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    page = int(callback.data.split(":")[1])
    movies, total_pages = await get_saved_movies(db_user.user_id, page=page)

    await callback.message.edit_text(
        f"❤️ <b>Saqlangan kinolar</b>\n\n"
        "Tanlang:",
        reply_markup=saved_movies_kb(movies, page=page, total_pages=total_pages)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("save:"))
async def save_movie_callback(callback: CallbackQuery, db_user: User = None):
    """Kinoni saqlash"""
    if not db_user:
        await callback.answer("❌ Avval ro'yxatdan o'ting!", show_alert=True)
        return

    movie_code = callback.data.split(":")[1]
    result = await save_movie_to_favorites(db_user.user_id, movie_code)

    if result:
        await callback.answer("❤️ Kino saqlandi!", show_alert=True)
        # Tugmani yangilash
        try:
            # Xabar turini aniqlash va qayta yuborish
            await callback.message.edit_reply_markup(
                reply_markup=movie_action_kb(movie_code, is_saved=True)
            )
        except:
            pass
    else:
        await callback.answer("❌ Xatolik yoki allaqachon saqlangan!", show_alert=True)


@router.callback_query(F.data.startswith("unsave:"))
async def unsave_movie_callback(callback: CallbackQuery, db_user: User = None):
    """Kinoni saqlanganlardan o'chirish"""
    if not db_user:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return

    movie_code = callback.data.split(":")[1]
    result = await remove_movie_from_favorites(db_user.user_id, movie_code)

    if result:
        await callback.answer("💔 Saqlanganlardan o'chirildi!", show_alert=True)
        # Tugmani yangilash
        try:
            await callback.message.edit_reply_markup(
                reply_markup=movie_action_kb(movie_code, is_saved=False)
            )
        except:
            pass
    else:
        await callback.answer("❌ Xatolik!", show_alert=True)


@router.callback_query(F.data.startswith("saved_movie:"))
async def saved_movie_callback(callback: CallbackQuery, db_user: User = None, bot: Bot = None):
    """Saqlangan kinoni ko'rish"""
    code = callback.data.split(":")[1]
    movie = await get_movie_by_code_db(code)

    if not movie:
        await callback.answer("❌ Kino topilmadi!", show_alert=True)
        return

    # Premium check
    if movie.is_premium and db_user and not db_user.is_premium_active:
        await callback.answer("💎 Bu Premium kino!", show_alert=True)
        return

    await callback.answer()

    try:
        bot_info = await bot.me()
        bot_link = f"https://t.me/{bot_info.username}"

        desc = f"\n📖 {movie.description}" if movie.description else ""
        year_text = f" • 📅 {movie.year}" if movie.year else ""

        await callback.message.answer_video(
            video=movie.file_id,
            caption=(
                f"❤️ <b>Saqlangan kino:</b>\n\n"
                f"🎬 <b>{movie.display_title}</b>{desc}\n\n"
                f"📝 Kod: <code>{movie.code}</code>\n"
                f"📺 {movie.get_quality_display()} • 🌐 {movie.get_language_display()}{year_text}\n"
                f"👁 {format_number(movie.views)}\n\n"
                f"🤖 <b>Bot:</b> {bot_link}"
            ),
            reply_markup=movie_action_kb(movie.code, is_saved=True)
        )
        await increment_movie_views(movie.id)
    except TelegramBadRequest:
        await callback.message.answer("❌ Xatolik.", reply_markup=back_kb())


@router.callback_query(F.data == "random_movie")
async def random_movie_callback(callback: CallbackQuery, db_user: User = None, bot: Bot = None):
    """Random kino callback"""
    from bot.middlewares.subscription import clear_subscription_cache

    user_id = callback.from_user.id

    # Obunani tekshirish
    if user_id not in settings.ADMINS:
        if not db_user or not db_user.is_premium_active:
            clear_subscription_cache(user_id)
            not_subscribed = await check_subscription(bot, user_id)

            if not_subscribed:
                await callback.answer("❌ Avval kanallarga obuna bo'ling!", show_alert=True)
                return

    movie = await get_random_movie()

    if not movie:
        await callback.answer("📭 Kinolar topilmadi.", show_alert=True)
        return

    if movie.is_premium and db_user and not db_user.is_premium_active:
        await callback.answer("💎 Premium kino tushdi! Premium oling.", show_alert=True)
        return

    await callback.answer()

    try:
        bot_info = await bot.me()
        bot_link = f"https://t.me/{bot_info.username}"

        desc = f"\n📖 {movie.description}" if movie.description else ""
        year_text = f" • 📅 {movie.year}" if movie.year else ""
        is_saved = await check_movie_saved(user_id, movie.code) if db_user else False

        await callback.message.answer_video(
            video=movie.file_id,
            caption=(
                f"🎲 <b>Random kino:</b>\n\n"
                f"🎬 <b>{movie.display_title}</b>{desc}\n\n"
                f"📝 Kod: <code>{movie.code}</code>\n"
                f"📺 {movie.get_quality_display()} • 🌐 {movie.get_language_display()}{year_text}\n\n"
                f"🤖 <b>Bot:</b> {bot_link}"
            ),
            reply_markup=movie_action_kb(movie.code, is_saved)
        )
        await increment_movie_views(movie.id)
    except TelegramBadRequest:
        await callback.message.answer("❌ Xatolik.", reply_markup=back_kb())


# ==================== HELP ====================

@router.message(Command("help"))
async def help_handler(message: Message):
    """Yordam"""
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start - Boshlash\n"
        "/top - Top kinolar\n"
        "/last - Yangilar\n"
        "/rand - Random\n"
        "/categories - Kategoriyalar\n"
        "/premium - Premium\n"
        "/profile - Profil\n\n"
        "🎬 Kino olish uchun kodini yuboring.",
        reply_markup=back_kb()
    )


# ==================== DATABASE FUNCTIONS ====================

async def check_subscription(bot: Bot, user_id: int) -> list:
    """Kanalga obunani tekshirish"""
    import logging
    logger = logging.getLogger(__name__)

    channels = await get_active_channels()
    not_subscribed = []

    logger.info(f"Tekshiriladigan kanallar: {len(channels)} ta")

    for channel in channels:
        logger.info(f"Kanal: {channel.title}, ID: {channel.channel_id}, is_checkable: {channel.is_checkable}")

        if not channel.is_checkable:
            logger.info(f"  -> O'tkazib yuborildi (is_checkable=False)")
            continue

        try:
            member = await bot.get_chat_member(channel.channel_id, user_id)
            logger.info(f"  -> Member status: {member.status}")

            if member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
                logger.info(f"  -> Obuna emas!")
            else:
                logger.info(f"  -> Obuna bo'lgan")

        except TelegramBadRequest as e:
            # Bot kanalda admin emas yoki kanal topilmadi - obuna emas deb hisoblaymiz
            logger.error(f"  -> XATOLIK: {e}")
            not_subscribed.append(channel)

        except Exception as e:
            logger.error(f"  -> Kutilmagan xatolik: {e}")
            not_subscribed.append(channel)

    return not_subscribed


@sync_to_async
def get_active_channels():
    return list(Channel.objects.filter(is_active=True, channel_id__isnull=False))


@sync_to_async
def get_user_db(user_id):
    try:
        return User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        return None


@sync_to_async
def get_movie_by_code_db(code):
    try:
        return Movie.objects.select_related('category').get(code=code)
    except Movie.DoesNotExist:
        return None


@sync_to_async
def get_top_movies(limit=10):
    return list(Movie.objects.filter(is_active=True).order_by('-views')[:limit])


@sync_to_async
def get_last_movies(limit=10):
    return list(Movie.objects.filter(is_active=True).order_by('-created_at')[:limit])


@sync_to_async
def get_random_movie():
    movies = Movie.objects.filter(is_active=True)
    count = movies.count()
    if count == 0:
        return None
    return movies[random.randint(0, count - 1)]


@sync_to_async
def get_all_movies(page=1, per_page=8):
    movies = Movie.objects.filter(is_active=True).order_by('-created_at')
    total = movies.count()
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    return list(movies[start:start + per_page]), total_pages


@sync_to_async
def get_categories():
    cache_key = 'categories'
    if cache_key in _categories_cache:
        return _categories_cache[cache_key]

    categories = list(Category.objects.filter(is_active=True).order_by('order'))
    _categories_cache[cache_key] = categories
    return categories


@sync_to_async
def get_movies_by_category(category_id, page=1, per_page=8):
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return [], 0, ""

    movies = Movie.objects.filter(is_active=True, category_id=category_id).order_by('-created_at')
    total = movies.count()
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    return list(movies[start:start + per_page]), total_pages, category.name


@sync_to_async
def get_movies_by_filter(country: str = None, language: str = None, year: int = None, page: int = 1, per_page: int = 8):
    """Filtr bo'yicha kinolar"""
    movies = Movie.objects.filter(is_active=True)

    if country:
        movies = movies.filter(country=country)
    if language:
        movies = movies.filter(language=language)
    if year:
        movies = movies.filter(year=year)

    movies = movies.order_by('-created_at')
    total = movies.count()
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page

    return list(movies[start:start + per_page]), total_pages


@sync_to_async
def get_tariffs():
    return list(Tariff.objects.filter(is_active=True).order_by('order'))


@sync_to_async
def increment_movie_views(movie_id):
    from django.db.models import F
    Movie.objects.filter(id=movie_id).update(views=F('views') + 1)


@sync_to_async
def increment_user_movies(user_id):
    from django.db.models import F
    User.objects.filter(user_id=user_id).update(movies_watched=F('movies_watched') + 1)


@sync_to_async
def get_referrals_count(user_id):
    try:
        user = User.objects.get(user_id=user_id)
        return user.referrals.count()
    except User.DoesNotExist:
        return 0


# ==================== SAQLANGAN KINOLAR DB FUNKSIYALARI ====================

@sync_to_async
def check_movie_saved(user_id: int, movie_code: str) -> bool:
    """Kino saqlanganmi tekshirish"""
    from apps.movies.models import SavedMovie
    try:
        user = User.objects.get(user_id=user_id)
        movie = Movie.objects.get(code=movie_code)
        return SavedMovie.objects.filter(user=user, movie=movie).exists()
    except (User.DoesNotExist, Movie.DoesNotExist):
        return False


@sync_to_async
def save_movie_to_favorites(user_id: int, movie_code: str) -> bool:
    """Kinoni saqlangan ro'yxatga qo'shish"""
    from apps.movies.models import SavedMovie
    try:
        user = User.objects.get(user_id=user_id)
        movie = Movie.objects.get(code=movie_code)

        # Allaqachon saqlangan bo'lsa False qaytarish
        if SavedMovie.objects.filter(user=user, movie=movie).exists():
            return False

        SavedMovie.objects.create(user=user, movie=movie)
        return True
    except (User.DoesNotExist, Movie.DoesNotExist):
        return False


@sync_to_async
def remove_movie_from_favorites(user_id: int, movie_code: str) -> bool:
    """Kinoni saqlanganlardan o'chirish"""
    from apps.movies.models import SavedMovie
    try:
        user = User.objects.get(user_id=user_id)
        movie = Movie.objects.get(code=movie_code)
        deleted, _ = SavedMovie.objects.filter(user=user, movie=movie).delete()
        return deleted > 0
    except (User.DoesNotExist, Movie.DoesNotExist):
        return False


@sync_to_async
def get_saved_movies(user_id: int, page: int = 1, per_page: int = 8):
    """Foydalanuvchining saqlangan kinolarini olish"""
    from apps.movies.models import SavedMovie
    try:
        user = User.objects.get(user_id=user_id)
        saved = SavedMovie.objects.filter(user=user).select_related('movie').order_by('-created_at')
        total = saved.count()
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page

        # Movie obyektlarini olish
        movies = [s.movie for s in saved[start:start + per_page]]
        return movies, total_pages
    except User.DoesNotExist:
        return [], 0


# ==================== FLASH SALE FUNKSIYALARI ====================

@sync_to_async
def set_premium_first_view(user_id: int):
    """Foydalanuvchi premium sahifani birinchi marta ko'rganini belgilash"""
    from django.utils import timezone
    try:
        user = User.objects.get(user_id=user_id)
        if not user.premium_first_view:
            user.premium_first_view = timezone.now()
            user.save(update_fields=['premium_first_view'])
        return True
    except User.DoesNotExist:
        return False


@sync_to_async
def get_tariff_by_id(tariff_id: int):
    """Tarif olish"""
    try:
        return Tariff.objects.get(id=tariff_id)
    except Tariff.DoesNotExist:
        return None


@sync_to_async
def get_bot_settings():
    """Bot sozlamalarini olish"""
    from apps.core.models import BotSettings
    return BotSettings.get_settings()
