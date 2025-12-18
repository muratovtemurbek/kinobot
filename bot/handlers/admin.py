from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import Count, Sum

from apps.users.models import User, Admin
from apps.movies.models import Movie, Category
from apps.payments.models import Payment
from apps.core.models import Broadcast
from bot.filters import IsAdmin, CanAddMovies, CanBroadcast, CanManageUsers, CanManagePayments, IsSuperAdmin
from bot.states import AddMovieState, BroadcastState, AddChannelState, EditSettingsState
from bot.keyboards import (
    admin_categories_kb, movie_quality_kb, movie_language_kb, movie_country_kb,
    broadcast_target_kb, broadcast_ad_kb, confirm_broadcast_kb,
    cancel_inline_kb, admin_main_kb, skip_inline_kb,
    main_menu_inline_kb, back_kb
)
from apps.channels.models import Channel
from bot.utils import format_number

router = Router()


# ==================== ADMIN PANEL ====================

@router.message(Command("admin"), IsAdmin())
async def admin_panel(message: Message, state: FSMContext):
    """Admin panel"""
    await state.clear()

    stats = await get_stats()

    text = (
        "👨‍💼 <b>Admin Panel</b>\n\n"
        f"👥 Userlar: {format_number(stats['total_users'])}\n"
        f"🆕 Bugun: +{format_number(stats['today_users'])}\n"
        f"💎 Premium: {format_number(stats['premium_users'])}\n"
        f"🎬 Kinolar: {format_number(stats['total_movies'])}\n"
        f"💳 Kutilmoqda: {format_number(stats['pending_payments'])}"
    )

    await message.answer(text, reply_markup=admin_main_kb())


@router.callback_query(F.data == "admin:panel", IsAdmin())
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    """Admin panel callback"""
    await state.clear()

    stats = await get_stats()

    text = (
        "👨‍💼 <b>Admin Panel</b>\n\n"
        f"👥 Userlar: {format_number(stats['total_users'])}\n"
        f"🆕 Bugun: +{format_number(stats['today_users'])}\n"
        f"💎 Premium: {format_number(stats['premium_users'])}\n"
        f"🎬 Kinolar: {format_number(stats['total_movies'])}\n"
        f"💳 Kutilmoqda: {format_number(stats['pending_payments'])}"
    )

    await callback.message.edit_text(text, reply_markup=admin_main_kb())
    await callback.answer()


# ==================== STATISTIKA ====================

@router.callback_query(F.data == "admin:stats", IsAdmin())
async def stats_handler(callback: CallbackQuery):
    """Batafsil statistika"""
    stats = await get_detailed_stats()

    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 <b>Userlar:</b>\n"
        f"├ Jami: {format_number(stats['total_users'])}\n"
        f"├ Bugun: +{format_number(stats['today_users'])}\n"
        f"├ Hafta: +{format_number(stats['week_users'])}\n"
        f"└ Oy: +{format_number(stats['month_users'])}\n\n"
        f"💎 <b>Premium:</b>\n"
        f"├ Premium: {format_number(stats['premium_users'])}\n"
        f"└ Trial: {format_number(stats['trial_users'])}\n\n"
        f"🎬 <b>Kinolar:</b>\n"
        f"├ Jami: {format_number(stats['total_movies'])}\n"
        f"├ Premium: {format_number(stats['premium_movies'])}\n"
        f"└ Ko'rishlar: {format_number(stats['total_views'])}\n\n"
        f"💳 <b>To'lovlar:</b>\n"
        f"├ Kutilmoqda: {format_number(stats['pending_payments'])}\n"
        f"└ Tasdiqlangan: {format_number(stats['approved_payments'])}"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:panel")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ==================== KINOLAR ====================

@router.callback_query(F.data == "admin:movies", IsAdmin())
async def movies_menu(callback: CallbackQuery):
    """Kinolar menyusi"""
    stats = await get_movie_stats()

    text = (
        "🎬 <b>Kinolar</b>\n\n"
        f"📊 Jami: {format_number(stats['total'])}\n"
        f"✅ Aktiv: {format_number(stats['active'])}\n"
        f"💎 Premium: {format_number(stats['premium'])}"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="admin:add_movie")],
        [InlineKeyboardButton(text="📋 Barcha kinolar", callback_data="admin:movies_list:1")],
        [InlineKeyboardButton(text="💎 Premium kinolar", callback_data="admin:premium_movies:1")],
        [InlineKeyboardButton(text="📊 Kinolar statistikasi", callback_data="admin:movies_stats")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:panel")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:movies_list:"), IsAdmin())
async def admin_movies_list(callback: CallbackQuery):
    """Barcha kinolar ro'yxati"""
    page = int(callback.data.split(":")[2])
    movies, total_pages = await get_admin_movies(page=page)

    if not movies:
        await callback.answer("📭 Kinolar yo'q", show_alert=True)
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    for movie in movies:
        prefix = "💎 " if movie.is_premium else "🎬 "
        builder.row(InlineKeyboardButton(
            text=f"{prefix}{movie.display_title} [{movie.code}]",
            callback_data=f"admin:movie_view:{movie.code}"
        ))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:movies_list:{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:movies_list:{page + 1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:movies"))

    await callback.message.edit_text(
        f"📋 <b>Barcha kinolar</b>\n\nSahifa: {page}/{total_pages}",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:premium_movies:"), IsAdmin())
async def admin_premium_movies(callback: CallbackQuery):
    """Premium kinolar ro'yxati"""
    page = int(callback.data.split(":")[2])
    movies, total_pages = await get_admin_movies(page=page, premium_only=True)

    if not movies:
        await callback.answer("📭 Premium kinolar yo'q", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    for movie in movies:
        builder.row(InlineKeyboardButton(
            text=f"💎 {movie.display_title} [{movie.code}]",
            callback_data=f"admin:movie_view:{movie.code}"
        ))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:premium_movies:{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:premium_movies:{page + 1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:movies"))

    await callback.message.edit_text(
        f"💎 <b>Premium kinolar</b>\n\nSahifa: {page}/{total_pages}",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:movie_view:"), IsAdmin())
async def admin_movie_view(callback: CallbackQuery):
    """Kino ma'lumotlari"""
    code = callback.data.split(":")[2]
    movie = await get_movie_by_code(code)

    if not movie:
        await callback.answer("❌ Kino topilmadi", show_alert=True)
        return

    category_name = movie.category.name if movie.category else "Yo'q"
    year_text = str(movie.year) if movie.year else "Yo'q"
    country_text = movie.get_country_display() if hasattr(movie, 'get_country_display') else "Yo'q"

    text = (
        f"🎬 <b>{movie.display_title}</b>\n\n"
        f"📝 Kod: <code>{movie.code}</code>\n"
        f"🎭 Janr: {category_name}\n"
        f"📅 Yil: {year_text}\n"
        f"🌍 Davlat: {country_text}\n"
        f"📺 Sifat: {movie.get_quality_display()}\n"
        f"🌐 Til: {movie.get_language_display()}\n"
        f"💎 Premium: {'Ha' if movie.is_premium else 'Yo`q'}\n"
        f"👁 Ko'rishlar: {format_number(movie.views)}\n"
        f"✅ Aktiv: {'Ha' if movie.is_active else 'Yo`q'}"
    )

    toggle_text = "❌ Deaktiv" if movie.is_active else "✅ Aktiv"
    premium_text = "🆓 Oddiy qilish" if movie.is_premium else "💎 Premium qilish"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:movie_toggle:{movie.code}")],
        [InlineKeyboardButton(text=premium_text, callback_data=f"admin:movie_premium:{movie.code}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:movie_delete:{movie.code}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:movies_list:1")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:movie_toggle:"), IsAdmin())
async def admin_movie_toggle(callback: CallbackQuery):
    """Kino aktiv/deaktiv"""
    code = callback.data.split(":")[2]
    new_status = await toggle_movie_status(code)
    status_text = "aktiv" if new_status else "deaktiv"
    await callback.answer(f"✅ Kino {status_text} qilindi!", show_alert=True)


@router.callback_query(F.data.startswith("admin:movie_premium:"), IsAdmin())
async def admin_movie_premium(callback: CallbackQuery):
    """Kino premium/oddiy"""
    code = callback.data.split(":")[2]
    new_status = await toggle_movie_premium(code)
    status_text = "Premium" if new_status else "Oddiy"
    await callback.answer(f"✅ Kino {status_text} qilindi!", show_alert=True)


@router.callback_query(F.data.startswith("admin:movie_delete:"), IsAdmin())
async def admin_movie_delete(callback: CallbackQuery):
    """Kinoni o'chirish - tasdiqlash"""
    code = callback.data.split(":")[2]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"admin:movie_delete_confirm:{code}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data=f"admin:movie_view:{code}")
        ]
    ])

    await callback.message.edit_text(
        f"⚠️ <b>{code}</b> kodli kinoni o'chirishni tasdiqlaysizmi?\n\n"
        "Bu amalni qaytarib bo'lmaydi!",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:movie_delete_confirm:"), IsAdmin())
async def admin_movie_delete_confirm(callback: CallbackQuery):
    """Kinoni o'chirish - tasdiqlangan"""
    code = callback.data.split(":")[2]
    result = await delete_movie(code)

    if result:
        await callback.answer("✅ Kino o'chirildi!", show_alert=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Kinolar ro'yxati", callback_data="admin:movies_list:1")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:movies")]
        ])
        await callback.message.edit_text("✅ Kino muvaffaqiyatli o'chirildi!", reply_markup=kb)
    else:
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(F.data == "admin:movies_stats", IsAdmin())
async def admin_movies_stats_handler(callback: CallbackQuery):
    """Kinolar statistikasi"""
    stats = await get_detailed_movie_stats()

    text = (
        "📊 <b>Kinolar statistikasi</b>\n\n"
        f"📈 Jami kinolar: {format_number(stats['total'])}\n"
        f"✅ Aktiv: {format_number(stats['active'])}\n"
        f"❌ Deaktiv: {format_number(stats['inactive'])}\n"
        f"💎 Premium: {format_number(stats['premium'])}\n"
        f"🆓 Oddiy: {format_number(stats['regular'])}\n\n"
        f"👁 Jami ko'rishlar: {format_number(stats['total_views'])}\n"
        f"📊 O'rtacha ko'rish: {stats['avg_views']}\n\n"
        f"🔝 <b>Eng ko'p ko'rilgan:</b>\n"
    )

    for i, movie in enumerate(stats['top_movies'], 1):
        text += f"{i}. {movie['title']} - {format_number(movie['views'])}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:movies")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.message(Command("addmovie"), CanAddMovies())
async def add_movie_start(message: Message, state: FSMContext):
    """Kino qo'shishni boshlash"""
    await state.set_state(AddMovieState.code)
    await message.answer(
        "🎬 <b>Kino qo'shish</b>\n\n"
        "1️⃣ Kino kodini kiriting:\n"
        "<i>Masalan: 123</i>",
        reply_markup=cancel_inline_kb()
    )


@router.callback_query(F.data == "admin:add_movie", CanAddMovies())
async def add_movie_start_callback(callback: CallbackQuery, state: FSMContext):
    """Kino qo'shishni boshlash callback"""
    await state.set_state(AddMovieState.code)
    await callback.message.edit_text(
        "🎬 <b>Kino qo'shish</b>\n\n"
        "1️⃣ Kino kodini kiriting:\n"
        "<i>Masalan: 123</i>",
        reply_markup=cancel_inline_kb()
    )
    await callback.answer()


@router.message(AddMovieState.code, F.text)
async def add_movie_code(message: Message, state: FSMContext):
    """Kino kodi"""
    code = message.text.strip()

    # Faqat raqam bo'lishi kerak
    if not code.isdigit():
        await message.answer(
            "❌ Kod faqat raqam bo'lishi kerak!\n\n"
            "<i>Masalan: 123</i>",
            reply_markup=cancel_inline_kb()
        )
        return

    # Tekshirish
    exists = await check_movie_exists(code)
    if exists:
        await message.answer(
            f"❌ <code>{code}</code> kodi band.\n\n"
            "Boshqa kod kiriting:",
            reply_markup=cancel_inline_kb()
        )
        return

    await state.update_data(code=code)
    await state.set_state(AddMovieState.title)
    await message.answer(
        f"✅ Kod: <code>{code}</code>\n\n"
        "2️⃣ Kino nomini kiriting:",
        reply_markup=cancel_inline_kb()
    )


@router.message(AddMovieState.title, F.text)
async def add_movie_title(message: Message, state: FSMContext):
    """Kino nomi"""
    data = await state.get_data()
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovieState.video)
    await message.answer(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {message.text.strip()}\n\n"
        "3️⃣ Video faylni yuboring:",
        reply_markup=cancel_inline_kb()
    )


@router.message(AddMovieState.video, F.video | F.document)
async def add_movie_video(message: Message, state: FSMContext):
    """Video fayl"""
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        if message.document.mime_type and message.document.mime_type.startswith('video/'):
            file_id = message.document.file_id
        else:
            await message.answer("❌ Faqat video fayl!", reply_markup=cancel_inline_kb())
            return
    else:
        return

    data = await state.get_data()
    await state.update_data(file_id=file_id)
    await state.set_state(AddMovieState.category)

    categories = await get_categories()

    if categories:
        await message.answer(
            f"✅ Kod: <code>{data.get('code')}</code>\n"
            f"✅ Nom: {data.get('title')}\n"
            "✅ Video qabul qilindi\n\n"
            "4️⃣ Janrni tanlang:",
            reply_markup=admin_categories_kb(categories)
        )
    else:
        await state.update_data(category_id=None)
        await state.set_state(AddMovieState.quality)
        await message.answer(
            f"✅ Kod: <code>{data.get('code')}</code>\n"
            f"✅ Nom: {data.get('title')}\n"
            "✅ Video qabul qilindi\n\n"
            "4️⃣ Sifatni tanlang:",
            reply_markup=movie_quality_kb()
        )


@router.callback_query(AddMovieState.category, F.data.startswith("admin_category:"))
async def add_movie_category(callback: CallbackQuery, state: FSMContext):
    """Janr tanlash"""
    cat_data = callback.data.split(":")[1]
    data = await state.get_data()

    if cat_data == "skip":
        category_id = None
        cat_text = "O'tkazildi"
    else:
        category_id = int(cat_data)
        category = await get_category_by_id(category_id)
        cat_text = category.name if category else "Tanlandi"

    await state.update_data(category_id=category_id)
    await state.set_state(AddMovieState.year)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="year:skip")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Janr: {cat_text}\n\n"
        "5️⃣ Kino yilini kiriting:\n"
        "<i>Masalan: 2024</i>",
        reply_markup=kb
    )
    await callback.answer()


@router.message(AddMovieState.year, F.text)
async def add_movie_year(message: Message, state: FSMContext):
    """Kino yili"""
    year_text = message.text.strip()

    if not year_text.isdigit() or len(year_text) != 4:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="year:skip")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
        ])
        await message.answer(
            "❌ Noto'g'ri format! 4 xonali yil kiriting.\n"
            "<i>Masalan: 2024</i>",
            reply_markup=kb
        )
        return

    year = int(year_text)
    if year < 1900 or year > 2030:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="year:skip")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
        ])
        await message.answer(
            "❌ Yil 1900-2030 oralig'ida bo'lishi kerak!",
            reply_markup=kb
        )
        return

    data = await state.get_data()
    await state.update_data(year=year)
    await state.set_state(AddMovieState.country)

    await message.answer(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Yil: {year}\n\n"
        "6️⃣ Davlatni tanlang:",
        reply_markup=movie_country_kb()
    )


@router.callback_query(AddMovieState.year, F.data == "year:skip")
async def add_movie_year_skip(callback: CallbackQuery, state: FSMContext):
    """Yilni o'tkazib yuborish"""
    data = await state.get_data()
    await state.update_data(year=None)
    await state.set_state(AddMovieState.country)

    await callback.message.edit_text(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Yil: O'tkazildi\n\n"
        "6️⃣ Davlatni tanlang:",
        reply_markup=movie_country_kb()
    )
    await callback.answer()


@router.callback_query(AddMovieState.country, F.data.startswith("country:"))
async def add_movie_country(callback: CallbackQuery, state: FSMContext):
    """Davlat tanlash"""
    country = callback.data.split(":")[1]
    data = await state.get_data()
    await state.update_data(country=country)
    await state.set_state(AddMovieState.quality)

    country_display = {
        'usa': '🇺🇸 AQSH', 'korea': '🇰🇷 Koreya', 'india': '🇮🇳 Hindiston',
        'turkey': '🇹🇷 Turkiya', 'russia': '🇷🇺 Rossiya', 'uzbekistan': '🇺🇿 O\'zbekiston',
        'uk': '🇬🇧 Britaniya', 'france': '🇫🇷 Fransiya', 'japan': '🇯🇵 Yaponiya',
        'china': '🇨🇳 Xitoy', 'other': '🌍 Boshqa'
    }.get(country, country)

    await callback.message.edit_text(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Davlat: {country_display}\n\n"
        "7️⃣ Sifatni tanlang:",
        reply_markup=movie_quality_kb()
    )
    await callback.answer()


@router.callback_query(AddMovieState.quality, F.data.startswith("quality:"))
async def add_movie_quality(callback: CallbackQuery, state: FSMContext):
    """Sifat tanlash"""
    quality = callback.data.split(":")[1]
    data = await state.get_data()
    await state.update_data(quality=quality)
    await state.set_state(AddMovieState.language)

    await callback.message.edit_text(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Sifat: {quality}\n\n"
        "6️⃣ Tilni tanlang:",
        reply_markup=movie_language_kb()
    )
    await callback.answer()


@router.callback_query(AddMovieState.language, F.data.startswith("language:"))
async def add_movie_language(callback: CallbackQuery, state: FSMContext):
    """Til tanlash - tavsif bosqichiga o'tish"""
    language = callback.data.split(":")[1]
    data = await state.get_data()
    await state.update_data(language=language)
    await state.set_state(AddMovieState.description)

    language_display = {
        'uzbek': "🇺🇿 O'zbek", 'rus': "🇷🇺 Rus", 'eng': "🇺🇸 English",
        'turk': "🇹🇷 Turk", 'korea': "🇰🇷 Koreys", 'other': "🌍 Boshqa"
    }.get(language, language)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="description:skip")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Til: {language_display}\n\n"
        "9️⃣ Qisqa tavsif kiriting:\n"
        "<i>Kino haqida 1-2 jumla</i>",
        reply_markup=kb
    )
    await callback.answer()


@router.message(AddMovieState.description, F.text)
async def add_movie_description(message: Message, state: FSMContext):
    """Tavsif kiritish"""
    description = message.text.strip()

    if len(description) > 500:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="description:skip")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
        ])
        await message.answer(
            "❌ Tavsif 500 belgidan oshmasligi kerak!\n"
            "Qisqaroq tavsif kiriting:",
            reply_markup=kb
        )
        return

    data = await state.get_data()
    await state.update_data(description=description)
    await state.set_state(AddMovieState.is_premium)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Premium kino", callback_data="is_premium:yes")],
        [InlineKeyboardButton(text="🆓 Oddiy kino", callback_data="is_premium:no")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await message.answer(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Tavsif: {description[:50]}...\n\n"
        "🔟 Kino turini tanlang:",
        reply_markup=kb
    )


@router.callback_query(AddMovieState.description, F.data == "description:skip")
async def add_movie_description_skip(callback: CallbackQuery, state: FSMContext):
    """Tavsifni o'tkazib yuborish"""
    data = await state.get_data()
    await state.update_data(description="")
    await state.set_state(AddMovieState.is_premium)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Premium kino", callback_data="is_premium:yes")],
        [InlineKeyboardButton(text="🆓 Oddiy kino", callback_data="is_premium:no")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        f"✅ Kod: <code>{data.get('code')}</code>\n"
        f"✅ Nom: {data.get('title')}\n"
        f"✅ Tavsif: O'tkazildi\n\n"
        "🔟 Kino turini tanlang:",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(AddMovieState.is_premium, F.data.startswith("is_premium:"))
async def add_movie_is_premium(callback: CallbackQuery, state: FSMContext):
    """Premium tanlash - tasdiqlash bosqichi"""
    is_premium = callback.data.split(":")[1] == "yes"
    data = await state.get_data()
    await state.update_data(is_premium=is_premium)
    await state.set_state(AddMovieState.confirm)

    # Ma'lumotlarni tayyorlash
    category_name = "Yo'q"
    if data.get('category_id'):
        category = await get_category_by_id(data['category_id'])
        if category:
            category_name = category.name

    year_text = str(data.get('year')) if data.get('year') else "Yo'q"

    country_display = {
        'usa': '🇺🇸 AQSH', 'korea': '🇰🇷 Koreya', 'india': '🇮🇳 Hindiston',
        'turkey': '🇹🇷 Turkiya', 'russia': '🇷🇺 Rossiya', 'uzbekistan': '🇺🇿 O\'zbekiston',
        'uk': '🇬🇧 Britaniya', 'france': '🇫🇷 Fransiya', 'japan': '🇯🇵 Yaponiya',
        'china': '🇨🇳 Xitoy', 'other': '🌍 Boshqa'
    }.get(data.get('country', 'other'), 'Boshqa')

    quality_display = {
        '360p': '360p', '480p': '480p', '720p': '720p HD',
        '1080p': '1080p FHD', '4k': '4K Ultra'
    }.get(data.get('quality', '720p'), data.get('quality'))

    language_display = {
        'uzbek': "🇺🇿 O'zbek", 'rus': "🇷🇺 Rus", 'eng': "🇺🇸 English",
        'turk': "🇹🇷 Turk", 'korea': "🇰🇷 Koreys", 'other': "🌍 Boshqa"
    }.get(data.get('language', 'uzbek'), data.get('language'))

    desc_text = data.get('description', '')[:100] + "..." if len(data.get('description', '')) > 100 else (data.get('description') or "Yo'q")
    premium_text = "💎 Premium" if is_premium else "🆓 Oddiy"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_movie")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        f"📋 <b>Kino ma'lumotlarini tasdiqlang:</b>\n\n"
        f"📝 Kod: <code>{data.get('code')}</code>\n"
        f"🎬 Nom: <b>{data.get('title')}</b>\n"
        f"🎭 Janr: {category_name}\n"
        f"📅 Yil: {year_text}\n"
        f"🌍 Davlat: {country_display}\n"
        f"📺 Sifat: {quality_display}\n"
        f"🌐 Til: {language_display}\n"
        f"📖 Tavsif: {desc_text}\n"
        f"💎 Turi: {premium_text}\n"
        f"🎥 Video: ✅ Yuklangan\n\n"
        f"<i>Hammasi to'g'rimi?</i>",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(AddMovieState.confirm, F.data == "confirm_movie")
async def add_movie_confirm(callback: CallbackQuery, state: FSMContext, db_user: User = None):
    """Kinoni tasdiqlash va saqlash"""
    data = await state.get_data()
    await state.clear()

    # Kino yaratish
    movie = await create_movie(
        code=data['code'],
        title=data['title'],
        file_id=data['file_id'],
        category_id=data.get('category_id'),
        year=data.get('year'),
        country=data.get('country', 'usa'),
        quality=data.get('quality', '720p'),
        language=data.get('language', 'uzbek'),
        description=data.get('description', ''),
        is_premium=data.get('is_premium', False),
        added_by_id=db_user.user_id if db_user else None
    )

    # Kategoriya nomini olish
    category_name = "Yo'q"
    if data.get('category_id'):
        category = await get_category_by_id(data['category_id'])
        if category:
            category_name = category.name

    premium_text = "💎 Premium" if movie.is_premium else "🆓 Oddiy"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yana qo'shish", callback_data="admin:add_movie")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin:panel")]
    ])

    await callback.message.edit_text(
        f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📝 Kod: <code>{movie.code}</code>\n"
        f"🎬 Nom: {movie.title}\n"
        f"🎭 Janr: {category_name}\n"
        f"📅 Yil: {movie.year or 'Yo`q'}\n"
        f"🌍 Davlat: {movie.get_country_display()}\n"
        f"📺 Sifat: {movie.get_quality_display()}\n"
        f"🌐 Til: {movie.get_language_display()}\n"
        f"💎 Turi: {premium_text}",
        reply_markup=kb
    )
    await callback.answer("✅ Kino qo'shildi!")


@router.callback_query(F.data == "cancel", IsAdmin())
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Bekor qilish"""
    await state.clear()

    await callback.message.edit_text(
        "❌ Bekor qilindi.",
        reply_markup=admin_main_kb()
    )
    await callback.answer()


@router.message(F.text == "❌ Bekor qilish", IsAdmin())
async def cancel_message_handler(message: Message, state: FSMContext):
    """Bekor qilish message"""
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_inline_kb(is_admin=True))


@router.callback_query(F.data == "cancel_old")
async def cancel_handler_old(event, state: FSMContext):
    """Bekor qilish old"""
    await state.clear()

    if isinstance(event, CallbackQuery):
        await event.message.edit_text("❌ Bekor qilindi.", reply_markup=admin_main_kb())
        await event.answer()


# ==================== XABAR YUBORISH ====================

@router.callback_query(F.data == "admin:broadcast", CanBroadcast())
async def broadcast_start_callback(callback: CallbackQuery, state: FSMContext):
    """Broadcast boshlash inline"""
    await state.set_state(BroadcastState.target)
    await callback.message.edit_text(
        "📨 <b>Xabar yuborish</b>\n\n"
        "Kimga yubormoqchisiz?",
        reply_markup=broadcast_target_kb()
    )
    await callback.answer()


@router.callback_query(BroadcastState.target, F.data.startswith("broadcast_target:"))
async def broadcast_target(callback: CallbackQuery, state: FSMContext):
    """Target tanlash"""
    target = callback.data.split(":")[1]
    await state.update_data(target=target)
    await state.set_state(BroadcastState.is_ad)

    target_text = {"all": "Hammaga", "premium": "Premium", "regular": "Oddiy"}

    await callback.message.edit_text(
        f"✅ Tanlandi: {target_text[target]}\n\n"
        "Bu reklama xabarimi?\n"
        "(Reklama xabari premium foydalanuvchilarga yuborilmaydi)",
        reply_markup=broadcast_ad_kb()
    )


@router.callback_query(BroadcastState.is_ad, F.data.startswith("broadcast_ad:"))
async def broadcast_is_ad(callback: CallbackQuery, state: FSMContext):
    """Reklama tanash"""
    is_ad = callback.data.split(":")[1] == "yes"
    await state.update_data(is_ad=is_ad)
    await state.set_state(BroadcastState.content)

    await callback.message.edit_text(
        "✅ Tanlandi.\n\n"
        "📝 Endi xabarni yuboring (matn, rasm, video yoki fayl):\n\n"
        "<i>Bekor qilish uchun /cancel buyrug'ini yuboring</i>"
    )
    await callback.answer()


@router.message(Command("cancel"), IsAdmin())
async def cancel_broadcast_cmd(message: Message, state: FSMContext):
    """Broadcast bekor qilish"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_main_kb())
    else:
        await message.answer("Bekor qilinadigan amal yo'q.")


@router.message(BroadcastState.content)
async def broadcast_content(message: Message, state: FSMContext):
    """Xabar kontenti"""
    data = await state.get_data()

    # Kontent turini aniqlash
    content_type = "text"
    file_id = ""
    text = ""

    if message.text:
        content_type = "text"
        text = message.text
    elif message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id
        text = message.caption or ""
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
        text = message.caption or ""
    elif message.document:
        content_type = "document"
        file_id = message.document.file_id
        text = message.caption or ""

    await state.update_data(
        content_type=content_type,
        file_id=file_id,
        text=text
    )
    await state.set_state(BroadcastState.confirm)

    # Preview ko'rsatish
    target_text = {"all": "Hammaga", "premium": "Premium", "regular": "Oddiy"}

    preview_text = (
        "📨 <b>Xabar preview:</b>\n\n"
        f"📍 Kimga: {target_text[data['target']]}\n"
        f"📢 Reklama: {'Ha' if data['is_ad'] else 'Yoq'}\n"
        f"📝 Tur: {content_type}\n\n"
        "Yuborishni tasdiqlaysizmi?"
    )

    await message.answer(preview_text, reply_markup=confirm_broadcast_kb())


@router.callback_query(BroadcastState.confirm, F.data == "confirm_broadcast")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, db_user: User = None, bot: Bot = None):
    """Broadcast tasdiqlash va yuborish"""
    data = await state.get_data()
    await state.clear()

    await callback.message.edit_text("📨 Xabar yuborilmoqda...")

    # Broadcast yaratish
    broadcast = await create_broadcast(
        target=data['target'],
        content_type=data['content_type'],
        text=data['text'],
        file_id=data['file_id'],
        is_ad=data['is_ad'],
        sent_by_id=db_user.user_id if db_user else None
    )

    # Foydalanuvchilarni olish
    users = await get_broadcast_users(data['target'], data['is_ad'])

    await update_broadcast_total(broadcast.id, len(users))

    # Yuborish
    sent = 0
    failed = 0

    for user in users:
        try:
            if data['content_type'] == 'text':
                await bot.send_message(user.user_id, data['text'])
            elif data['content_type'] == 'photo':
                await bot.send_photo(user.user_id, data['file_id'], caption=data['text'])
            elif data['content_type'] == 'video':
                await bot.send_video(user.user_id, data['file_id'], caption=data['text'])
            elif data['content_type'] == 'document':
                await bot.send_document(user.user_id, data['file_id'], caption=data['text'])
            sent += 1
        except Exception:
            failed += 1

        # Har 20 ta xabardan keyin progress
        if (sent + failed) % 20 == 0:
            await callback.message.edit_text(
                f"📨 Yuborilmoqda... {sent + failed}/{len(users)}"
            )

    # Yakunlash
    await complete_broadcast(broadcast.id, sent, failed)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin:panel")]
    ])

    await callback.message.edit_text(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"📊 Jami: {len(users)}\n"
        f"✅ Yuborildi: {sent}\n"
        f"❌ Xato: {failed}",
        reply_markup=kb
    )


# ==================== TO'LOVLAR ====================

@router.callback_query(F.data == "admin:payments", CanManagePayments())
async def payments_menu(callback: CallbackQuery):
    """To'lovlar"""
    pending = await get_pending_payments()

    if not pending:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:panel")]
        ])
        await callback.message.edit_text("📭 Kutilayotgan to'lovlar yo'q.", reply_markup=kb)
        await callback.answer()
        return

    await callback.message.edit_text(f"💳 Kutilayotgan: {len(pending)}")
    await callback.answer()

    for payment in pending[:10]:
        text = (
            f"💳 <b>To'lov #{payment.id}</b>\n\n"
            f"👤 {payment.user.full_name}\n"
            f"🆔 <code>{payment.user.user_id}</code>\n"
            f"💰 {payment.amount:,} so'm\n"
            f"📅 {payment.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

        from bot.keyboards import payment_confirm_kb
        await callback.message.answer_photo(
            photo=payment.screenshot_file_id,
            caption=text,
            reply_markup=payment_confirm_kb(payment.id)
        )


# ==================== KANALLAR ====================

@router.callback_query(F.data == "admin:channels", IsAdmin())
async def channels_menu(callback: CallbackQuery):
    """Kanallar"""
    channels = await get_channels()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    type_icons = {
        'telegram_channel': '📢',
        'telegram_group': '👥',
        'telegram_bot': '🤖',
        'instagram': '📸',
        'external': '🔗',
        'public': '📢',
        'private': '🔒',
        'group': '👥',
    }

    if channels:
        for channel in channels:
            status = "✅" if channel.is_active else "❌"
            icon = type_icons.get(channel.channel_type, '📢')
            builder.row(InlineKeyboardButton(
                text=f"{status} {icon} {channel.title}",
                callback_data=f"ch:view:{channel.id}"
            ))

    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="ch:add"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:panel"))

    text = "📢 <b>Majburiy obuna kanallari</b>\n\n"
    if channels:
        text += f"Jami: {len(channels)} ta\n"
        text += "Kanalni bosib tahrirlang."
    else:
        text += "📭 Hozircha kanallar yo'q.\n➕ Kanal qo'shish tugmasini bosing."

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "ch:add", IsAdmin())
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    """Kanal qo'shishni boshlash - tur tanlash"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Telegram kanal", callback_data="ch:type:telegram_channel")],
        [InlineKeyboardButton(text="👥 Telegram guruh", callback_data="ch:type:telegram_group")],
        [InlineKeyboardButton(text="🤖 Telegram bot", callback_data="ch:type:telegram_bot")],
        [InlineKeyboardButton(text="📸 Instagram", callback_data="ch:type:instagram")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:channels")]
    ])

    await callback.message.edit_text(
        "📢 <b>Kanal qo'shish</b>\n\n"
        "Kanal turini tanlang:",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch:type:"), IsAdmin())
async def add_channel_type(callback: CallbackQuery, state: FSMContext):
    """Kanal turini tanlash"""
    channel_type = callback.data.split(":")[2]
    await state.update_data(channel_type=channel_type)
    await state.set_state(AddChannelState.channel_input)

    if channel_type == "instagram":
        await callback.message.edit_text(
            "📸 <b>Instagram qo'shish</b>\n\n"
            "Instagram profilingiz havolasini kiriting:\n\n"
            "Masalan:\n"
            "• <code>https://instagram.com/username</code>\n"
            "• <code>https://www.instagram.com/username</code>",
            reply_markup=cancel_inline_kb()
        )
    elif channel_type == "telegram_bot":
        await callback.message.edit_text(
            "🤖 <b>Bot qo'shish</b>\n\n"
            "Bot username yoki havolasini kiriting:\n\n"
            "Masalan:\n"
            "• <code>@bot_username</code>\n"
            "• <code>https://t.me/bot_username</code>",
            reply_markup=cancel_inline_kb()
        )
    else:
        await callback.message.edit_text(
            "📢 <b>Kanal/Guruh qo'shish</b>\n\n"
            "Kanalni forward qiling yoki kanal username/ID kiriting:\n\n"
            "Masalan:\n"
            "• <code>@channel_username</code>\n"
            "• <code>-1001234567890</code>\n"
            "• Yoki kanaldan xabar forward qiling",
            reply_markup=cancel_inline_kb()
        )
    await callback.answer()


@router.message(AddChannelState.channel_input, IsAdmin())
async def add_channel_input(message: Message, state: FSMContext, bot: Bot):
    """Kanal ma'lumotlarini olish"""
    data = await state.get_data()
    channel_type = data.get('channel_type', 'telegram_channel')

    channel_id = None
    username = ""
    title = ""
    invite_link = ""

    # Instagram uchun
    if channel_type == "instagram":
        text = message.text.strip() if message.text else ""
        if "instagram.com" in text:
            # Instagram username olish
            parts = text.rstrip("/").split("/")
            username = parts[-1] if parts else ""
            title = f"Instagram: @{username}"
            invite_link = text if text.startswith("http") else f"https://instagram.com/{username}"

            await save_channel_with_type(None, username, title, invite_link, "instagram")
            await state.clear()

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanallar", callback_data="admin:channels")],
                [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin:panel")]
            ])

            await message.answer(
                f"✅ <b>Instagram qo'shildi!</b>\n\n"
                f"📸 {title}\n"
                f"🔗 {invite_link}",
                reply_markup=kb
            )
            return
        else:
            await message.answer(
                "❌ Noto'g'ri format. Instagram havolasini kiriting:\n"
                "<code>https://instagram.com/username</code>",
                reply_markup=cancel_inline_kb()
            )
            return

    # Telegram bot uchun
    if channel_type == "telegram_bot":
        text = message.text.strip() if message.text else ""
        if text.startswith("@"):
            username = text[1:]
        elif "t.me/" in text:
            username = text.split("t.me/")[-1].rstrip("/")
        else:
            username = text

        title = f"Bot: @{username}"
        invite_link = f"https://t.me/{username}"

        await save_channel_with_type(None, username, title, invite_link, "telegram_bot")
        await state.clear()

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanallar", callback_data="admin:channels")],
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin:panel")]
        ])

        await message.answer(
            f"✅ <b>Bot qo'shildi!</b>\n\n"
            f"🤖 {title}\n"
            f"🔗 {invite_link}",
            reply_markup=kb
        )
        return

    # Telegram kanal/guruh uchun
    # Forward qilingan xabar
    if message.forward_from_chat:
        chat = message.forward_from_chat
        channel_id = chat.id
        username = chat.username or ""
        title = chat.title or ""
        if username:
            invite_link = f"https://t.me/{username}"
    # Username kiritilgan
    elif message.text:
        text = message.text.strip()
        if text.startswith("@"):
            username = text[1:]
            try:
                chat = await bot.get_chat(f"@{username}")
                channel_id = chat.id
                title = chat.title or username
                invite_link = f"https://t.me/{username}"
            except Exception:
                await message.answer(
                    "❌ Kanal topilmadi. Username to'g'ri ekanligini tekshiring.\n"
                    "Bot kanalda admin bo'lishi kerak!",
                    reply_markup=cancel_inline_kb()
                )
                return
        # ID kiritilgan
        elif text.lstrip("-").isdigit():
            try:
                chat = await bot.get_chat(int(text))
                channel_id = chat.id
                username = chat.username or ""
                title = chat.title or ""
                if username:
                    invite_link = f"https://t.me/{username}"
                else:
                    try:
                        invite_link = await bot.export_chat_invite_link(channel_id)
                    except Exception:
                        invite_link = ""
            except Exception:
                await message.answer(
                    "❌ Kanal topilmadi. ID to'g'ri ekanligini tekshiring.\n"
                    "Bot kanalda admin bo'lishi kerak!",
                    reply_markup=cancel_inline_kb()
                )
                return
        else:
            await message.answer(
                "❌ Noto'g'ri format. Qaytadan urinib ko'ring.",
                reply_markup=cancel_inline_kb()
            )
            return

    if not channel_id:
        await message.answer(
            "❌ Kanal ma'lumotlarini olib bo'lmadi.",
            reply_markup=cancel_inline_kb()
        )
        return

    # Mavjudligini tekshirish
    exists = await check_channel_exists(channel_id)
    if exists:
        await message.answer(
            "❌ Bu kanal allaqachon qo'shilgan!",
            reply_markup=cancel_inline_kb()
        )
        await state.clear()
        return

    await state.update_data(
        channel_id=channel_id,
        username=username,
        title=title,
        invite_link=invite_link
    )

    if not invite_link:
        await state.set_state(AddChannelState.title)
        await message.answer(
            f"✅ Kanal topildi: <b>{title}</b>\n\n"
            "Kanal uchun havola kiriting (https://t.me/...):",
            reply_markup=cancel_inline_kb()
        )
    else:
        # Saqlash
        await save_channel_with_type(channel_id, username, title, invite_link, channel_type)
        await state.clear()

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanallar", callback_data="admin:channels")],
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin:panel")]
        ])

        await message.answer(
            f"✅ <b>Kanal qo'shildi!</b>\n\n"
            f"📢 {title}\n"
            f"🆔 <code>{channel_id}</code>\n"
            f"🔗 {invite_link}",
            reply_markup=kb
        )


@router.message(AddChannelState.title, IsAdmin())
async def add_channel_link(message: Message, state: FSMContext):
    """Kanal havolasini olish"""
    invite_link = message.text.strip()

    if not invite_link.startswith("http"):
        await message.answer(
            "❌ Noto'g'ri havola. https://t.me/... formatida kiriting:",
            reply_markup=cancel_inline_kb()
        )
        return

    data = await state.get_data()
    channel_type = data.get('channel_type', 'telegram_channel')

    await save_channel_with_type(
        data['channel_id'],
        data['username'],
        data['title'],
        invite_link,
        channel_type
    )
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanallar", callback_data="admin:channels")],
        [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin:panel")]
    ])

    await message.answer(
        f"✅ <b>Kanal qo'shildi!</b>\n\n"
        f"📢 {data['title']}\n"
        f"🆔 <code>{data['channel_id']}</code>\n"
        f"🔗 {invite_link}",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("ch:view:"), IsAdmin())
async def view_channel(callback: CallbackQuery):
    """Kanal ma'lumotlari"""
    channel_id = int(callback.data.split(":")[2])
    channel = await get_channel_by_id(channel_id)

    if not channel:
        await callback.answer("❌ Kanal topilmadi", show_alert=True)
        return

    # Kanal orqali kelgan userlar sonini olish
    joined_users_count = await get_channel_joined_users_count(channel_id)

    status = "✅ Aktiv" if channel.is_active else "❌ O'chirilgan"
    checkable = "✅ Ha" if channel.is_checkable else "❌ Yo'q"

    type_names = {
        'telegram_channel': '📢 Telegram kanal',
        'telegram_group': '👥 Telegram guruh',
        'telegram_bot': '🤖 Telegram bot',
        'instagram': '📸 Instagram',
        'external': '🔗 Tashqi',
        'public': '📢 Ochiq kanal',
        'private': '🔒 Yopiq kanal',
        'group': '👥 Guruh',
    }
    type_text = type_names.get(channel.channel_type, channel.channel_type)

    text = (
        f"📢 <b>{channel.title}</b>\n\n"
        f"📋 Turi: {type_text}\n"
        f"🆔 ID: <code>{channel.channel_id or 'yo`q'}</code>\n"
        f"👤 Username: @{channel.username or 'yo`q'}\n"
        f"🔗 Havola: {channel.invite_link}\n"
        f"📊 Holat: {status}\n"
        f"✅ Tekshirish: {checkable}\n\n"
        f"📈 <b>Statistika:</b>\n"
        f"👥 Bu kanal orqali kelgan: <b>{joined_users_count}</b> ta user"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    toggle_text = "❌ O'chirish" if channel.is_active else "✅ Yoqish"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"ch:toggle:{channel.id}")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"ch:delete:{channel.id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:channels")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("ch:toggle:"), IsAdmin())
async def toggle_channel(callback: CallbackQuery):
    """Kanal holatini o'zgartirish"""
    channel_id = int(callback.data.split(":")[2])
    result = await toggle_channel_status(channel_id)

    if result:
        await callback.answer("✅ Holat o'zgartirildi!")
        # Qayta ko'rsatish
        await view_channel(callback)
    else:
        await callback.answer("❌ Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("ch:delete:"), IsAdmin())
async def delete_channel_confirm(callback: CallbackQuery):
    """Kanalni o'chirishni tasdiqlash"""
    channel_id = int(callback.data.split(":")[2])

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"ch:delete_yes:{channel_id}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data=f"ch:view:{channel_id}")
        ]
    ])

    await callback.message.edit_text(
        "⚠️ <b>Kanalni o'chirishni tasdiqlaysizmi?</b>\n\n"
        "Bu amalni qaytarib bo'lmaydi!",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch:delete_yes:"), IsAdmin())
async def delete_channel_yes(callback: CallbackQuery):
    """Kanalni o'chirish"""
    channel_id = int(callback.data.split(":")[2])
    result = await delete_channel(channel_id)

    if result:
        await callback.answer("✅ Kanal o'chirildi!")
        # Kanallar ro'yxatiga qaytish
        await channels_menu(callback)
    else:
        await callback.answer("❌ Xatolik", show_alert=True)


# ==================== FOYDALANUVCHILAR ====================

@router.callback_query(F.data == "admin:users", CanManageUsers())
async def users_menu(callback: CallbackQuery):
    """Userlar"""
    stats = await get_user_stats()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:panel")]
    ])

    text = (
        "👥 <b>Userlar</b>\n\n"
        f"├ Jami: {format_number(stats['total'])}\n"
        f"├ Aktiv: {format_number(stats['active_24h'])}\n"
        f"├ Premium: {format_number(stats['premium'])}\n"
        f"├ Trial: {format_number(stats['trial'])}\n"
        f"└ Ban: {format_number(stats['banned'])}\n\n"
        "<b>Buyruqlar:</b>\n"
        "<code>/user 123456</code> - Ma'lumot\n"
        "<code>/ban 123456</code> - Bloklash\n"
        "<code>/unban 123456</code> - Ochish"
    )

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.message(Command("user"), CanManageUsers())
async def user_info_cmd(message: Message):
    """Foydalanuvchi ma'lumotlari"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Foydalanish: /user [user_id]")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri user_id")
        return

    user = await get_user_by_telegram_id(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi")
        return

    status = "⭐️ Premium" if user.is_premium_active else ("🎁 Trial" if user.is_trial_active else "👤 Oddiy")
    banned = "⛔️ Ha" if user.is_banned else "✅ Yo'q"

    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"👤 Ism: {user.full_name}\n"
        f"📛 Username: @{user.username or 'yo`q'}\n"
        f"📊 Status: {status}\n"
        f"⛔️ Bloklangan: {banned}\n"
        f"🎬 Ko'rilgan kinolar: {user.movies_watched}\n"
        f"📅 Ro'yxatdan o'tgan: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"🕐 Oxirgi faollik: {user.last_active.strftime('%d.%m.%Y %H:%M')}"
    )

    await message.answer(text)


@router.message(Command("ban"), CanManageUsers())
async def ban_user_cmd(message: Message):
    """Foydalanuvchini bloklash"""
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("❌ Foydalanish: /ban [user_id] [sabab]")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri user_id")
        return

    reason = args[2] if len(args) > 2 else None
    result = await ban_user(user_id, reason)

    if result:
        await message.answer(f"✅ Foydalanuvchi <code>{user_id}</code> bloklandi.")
    else:
        await message.answer("❌ Foydalanuvchi topilmadi.")


@router.message(Command("unban"), CanManageUsers())
async def unban_user_cmd(message: Message):
    """Foydalanuvchini blokdan chiqarish"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Foydalanish: /unban [user_id]")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri user_id")
        return

    result = await unban_user(user_id)

    if result:
        await message.answer(f"✅ Foydalanuvchi <code>{user_id}</code> blokdan chiqarildi.")
    else:
        await message.answer("❌ Foydalanuvchi topilmadi.")


# ==================== SOZLAMALAR ====================

@router.callback_query(F.data == "admin:settings", IsSuperAdmin())
async def settings_menu_callback(callback: CallbackQuery):
    """Bot sozlamalari inline"""
    settings = await get_bot_settings()

    status = "✅ Aktiv" if settings.is_active else "❌ O'chirilgan"
    discount = f"✅ {settings.discount_percent}%" if settings.discount_active else "❌ O'chirilgan"
    referral = f"✅ +{settings.referral_bonus} kun" if settings.referral_active else "❌ O'chirilgan"

    text = (
        "⚙️ <b>Bot sozlamalari</b>\n\n"
        f"🤖 Bot holati: {status}\n"
        f"🎁 Bepul muddat: {settings.free_trial_days} kun\n"
        f"💰 Chegirma: {discount}\n"
        f"🔗 Referal bonus: {referral}\n\n"
        f"💳 <b>To'lov ma'lumotlari:</b>\n"
        f"Karta: <code>{settings.card_number}</code>\n"
        f"Egasi: {settings.card_holder}"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta raqami", callback_data="settings:card_number"),
         InlineKeyboardButton(text="👤 Karta egasi", callback_data="settings:card_holder")],
        [InlineKeyboardButton(text="🎁 Trial kunlar", callback_data="settings:trial_days"),
         InlineKeyboardButton(text="🔗 Referal bonus", callback_data="settings:referral_bonus")],
        [InlineKeyboardButton(text="🤖 Bot on/off", callback_data="settings:toggle_bot"),
         InlineKeyboardButton(text="💰 Chegirma on/off", callback_data="settings:toggle_discount")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:panel")]
    ])

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ==================== SOZLAMALARNI TAHRIRLASH ====================

@router.callback_query(F.data == "settings:card_number", IsSuperAdmin())
async def edit_card_number_start(callback: CallbackQuery, state: FSMContext):
    """Karta raqamini o'zgartirish"""
    await state.set_state(EditSettingsState.card_number)
    await callback.message.edit_text(
        "💳 <b>Karta raqamini kiriting:</b>\n\n"
        "Masalan: <code>8600 1234 5678 9012</code>",
        reply_markup=cancel_inline_kb()
    )
    await callback.answer()


@router.message(EditSettingsState.card_number, F.text, IsSuperAdmin())
async def edit_card_number_save(message: Message, state: FSMContext):
    """Karta raqamini saqlash"""
    card_number = message.text.strip()

    # Validatsiya - faqat raqam va bo'sh joy
    clean_number = card_number.replace(" ", "")
    if not clean_number.isdigit() or len(clean_number) < 14:
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "Karta raqami faqat raqamlardan iborat bo'lishi kerak.\n"
            "Masalan: <code>8600 1234 5678 9012</code>",
            reply_markup=cancel_inline_kb()
        )
        return

    await update_bot_setting('card_number', card_number)
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin:settings")]
    ])

    await message.answer(
        f"✅ <b>Karta raqami yangilandi!</b>\n\n"
        f"Yangi raqam: <code>{card_number}</code>",
        reply_markup=kb
    )


@router.callback_query(F.data == "settings:card_holder", IsSuperAdmin())
async def edit_card_holder_start(callback: CallbackQuery, state: FSMContext):
    """Karta egasini o'zgartirish"""
    await state.set_state(EditSettingsState.card_holder)
    await callback.message.edit_text(
        "👤 <b>Karta egasining ismini kiriting:</b>\n\n"
        "Masalan: <code>ABDULLAYEV ABDULLA</code>",
        reply_markup=cancel_inline_kb()
    )
    await callback.answer()


@router.message(EditSettingsState.card_holder, F.text, IsSuperAdmin())
async def edit_card_holder_save(message: Message, state: FSMContext):
    """Karta egasini saqlash"""
    card_holder = message.text.strip().upper()

    if len(card_holder) < 3:
        await message.answer(
            "❌ Ism juda qisqa!\n\n"
            "Masalan: <code>ABDULLAYEV ABDULLA</code>",
            reply_markup=cancel_inline_kb()
        )
        return

    await update_bot_setting('card_holder', card_holder)
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin:settings")]
    ])

    await message.answer(
        f"✅ <b>Karta egasi yangilandi!</b>\n\n"
        f"Yangi egasi: <code>{card_holder}</code>",
        reply_markup=kb
    )


@router.callback_query(F.data == "settings:trial_days", IsSuperAdmin())
async def edit_trial_days_start(callback: CallbackQuery, state: FSMContext):
    """Trial kunlarni o'zgartirish"""
    await state.set_state(EditSettingsState.trial_days)
    await callback.message.edit_text(
        "🎁 <b>Bepul kunlar sonini kiriting:</b>\n\n"
        "Masalan: <code>7</code> (kunlar soni)",
        reply_markup=cancel_inline_kb()
    )
    await callback.answer()


@router.message(EditSettingsState.trial_days, F.text, IsSuperAdmin())
async def edit_trial_days_save(message: Message, state: FSMContext):
    """Trial kunlarni saqlash"""
    try:
        days = int(message.text.strip())
        if days < 0 or days > 365:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri son!\n\n"
            "0 dan 365 gacha raqam kiriting.",
            reply_markup=cancel_inline_kb()
        )
        return

    await update_bot_setting('free_trial_days', days)
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin:settings")]
    ])

    await message.answer(
        f"✅ <b>Bepul muddat yangilandi!</b>\n\n"
        f"Yangi muddat: <code>{days}</code> kun",
        reply_markup=kb
    )


@router.callback_query(F.data == "settings:referral_bonus", IsSuperAdmin())
async def edit_referral_bonus_start(callback: CallbackQuery, state: FSMContext):
    """Referal bonusni o'zgartirish"""
    await state.set_state(EditSettingsState.referral_bonus)

    await callback.message.edit_text(
        "🔗 <b>Referal bonus kunlarini kiriting:</b>\n\n"
        "Har bir referal uchun beriladigan bonus kunlar.\n"
        "Masalan: <code>3</code> (kunlar soni)",
        reply_markup=cancel_inline_kb()
    )
    await callback.answer()


@router.message(EditSettingsState.referral_bonus, F.text, IsSuperAdmin())
async def edit_referral_bonus_save(message: Message, state: FSMContext):
    """Referal bonusni saqlash"""
    try:
        days = int(message.text.strip())
        if days < 0 or days > 30:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri son!\n\n"
            "0 dan 30 gacha raqam kiriting.",
            reply_markup=cancel_inline_kb()
        )
        return

    await update_bot_setting('referral_bonus', days)
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin:settings")]
    ])

    await message.answer(
        f"✅ <b>Referal bonus yangilandi!</b>\n\n"
        f"Yangi bonus: <code>{days}</code> kun",
        reply_markup=kb
    )


@router.callback_query(F.data == "settings:toggle_bot", IsSuperAdmin())
async def toggle_bot_status(callback: CallbackQuery):
    """Bot holatini o'zgartirish"""
    settings = await get_bot_settings()
    new_status = not settings.is_active
    await update_bot_setting('is_active', new_status)

    status_text = "yoqildi ✅" if new_status else "o'chirildi ❌"
    await callback.answer(f"Bot {status_text}", show_alert=True)

    # Sozlamalarni qayta ko'rsatish
    await settings_menu_callback(callback)


@router.callback_query(F.data == "settings:toggle_discount", IsSuperAdmin())
async def toggle_discount_status(callback: CallbackQuery):
    """Chegirma holatini o'zgartirish"""
    settings = await get_bot_settings()
    new_status = not settings.discount_active
    await update_bot_setting('discount_active', new_status)

    status_text = "yoqildi ✅" if new_status else "o'chirildi ❌"
    await callback.answer(f"Chegirma {status_text}", show_alert=True)

    # Sozlamalarni qayta ko'rsatish
    await settings_menu_callback(callback)


# ==================== CHIQISH ====================

@router.message(F.text.in_({"🔙 Chiqish", "🏠 Asosiy menyu"}), IsAdmin())
async def exit_admin(message: Message, state: FSMContext):
    """Admin paneldan chiqish"""
    await state.clear()
    await message.answer("🏠 Asosiy menyu:", reply_markup=main_menu_inline_kb(is_admin=True))


# ==================== HELPER FUNCTIONS ====================

@sync_to_async
def get_category_by_id(category_id: int):
    """Kategoriyani ID bo'yicha olish"""
    try:
        return Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return None


@sync_to_async
def get_stats():
    from django.utils import timezone
    today = timezone.now().date()

    return {
        'total_users': User.objects.count(),
        'today_users': User.objects.filter(created_at__date=today).count(),
        'premium_users': User.objects.filter(is_premium=True, premium_expires__gt=timezone.now()).count(),
        'total_movies': Movie.objects.count(),
        'pending_payments': Payment.objects.filter(status='pending').count(),
    }


@sync_to_async
def get_detailed_stats():
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    return {
        'total_users': User.objects.count(),
        'today_users': User.objects.filter(created_at__date=today).count(),
        'week_users': User.objects.filter(created_at__gte=week_ago).count(),
        'month_users': User.objects.filter(created_at__gte=month_ago).count(),
        'premium_users': User.objects.filter(is_premium=True, premium_expires__gt=now).count(),
        'trial_users': User.objects.filter(free_trial_expires__gt=now, is_premium=False).count(),
        'total_movies': Movie.objects.count(),
        'premium_movies': Movie.objects.filter(is_premium=True).count(),
        'total_views': Movie.objects.aggregate(total=Sum('views'))['total'] or 0,
        'pending_payments': Payment.objects.filter(status='pending').count(),
        'approved_payments': Payment.objects.filter(status='approved').count(),
    }


@sync_to_async
def get_movie_stats():
    return {
        'total': Movie.objects.count(),
        'active': Movie.objects.filter(is_active=True).count(),
        'premium': Movie.objects.filter(is_premium=True).count(),
    }


@sync_to_async
def check_movie_exists(code: str):
    return Movie.objects.filter(code=code).exists()


@sync_to_async
def get_categories():
    return list(Category.objects.filter(is_active=True).order_by('order'))


@sync_to_async
def create_movie(code, title, file_id, category_id, year, country, quality, language, description, is_premium, added_by_id):
    added_by = None
    if added_by_id:
        try:
            added_by = User.objects.get(user_id=added_by_id)
        except User.DoesNotExist:
            pass

    return Movie.objects.create(
        code=code,
        title=title,
        file_id=file_id,
        category_id=category_id,
        year=year,
        country=country,
        quality=quality,
        language=language,
        description=description,
        is_premium=is_premium,
        added_by=added_by
    )


@sync_to_async
def create_broadcast(target, content_type, text, file_id, is_ad, sent_by_id):
    sent_by = None
    if sent_by_id:
        try:
            sent_by = User.objects.get(user_id=sent_by_id)
        except User.DoesNotExist:
            pass

    return Broadcast.objects.create(
        target=target,
        content_type=content_type,
        text=text,
        file_id=file_id,
        is_advertisement=is_ad,
        sent_by=sent_by
    )


@sync_to_async
def get_broadcast_users(target, is_ad):
    from django.utils import timezone

    qs = User.objects.filter(is_banned=False)

    if target == 'premium':
        qs = qs.filter(is_premium=True, premium_expires__gt=timezone.now())
    elif target == 'regular':
        qs = qs.exclude(is_premium=True, premium_expires__gt=timezone.now())

    if is_ad:
        # Reklama xabari premium ga bormaydi
        qs = qs.exclude(is_premium=True, premium_expires__gt=timezone.now())

    return list(qs)


@sync_to_async
def update_broadcast_total(broadcast_id, total):
    Broadcast.objects.filter(id=broadcast_id).update(total_users=total)


@sync_to_async
def complete_broadcast(broadcast_id, sent, failed):
    Broadcast.objects.filter(id=broadcast_id).update(
        sent_count=sent,
        failed_count=failed,
        is_completed=True,
        completed_at=timezone.now()
    )


@sync_to_async
def get_pending_payments():
    return list(Payment.objects.filter(status='pending').select_related('user', 'tariff').order_by('-created_at')[:10])


@sync_to_async
def get_channels():
    from apps.channels.models import Channel
    return list(Channel.objects.all().order_by('order'))


@sync_to_async
def get_user_stats():
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    day_ago = now - timedelta(hours=24)

    return {
        'total': User.objects.count(),
        'active_24h': User.objects.filter(last_active__gte=day_ago).count(),
        'premium': User.objects.filter(is_premium=True, premium_expires__gt=now).count(),
        'trial': User.objects.filter(free_trial_expires__gt=now, is_premium=False).count(),
        'banned': User.objects.filter(is_banned=True).count(),
    }


@sync_to_async
def get_user_by_telegram_id(user_id: int):
    try:
        return User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        return None


@sync_to_async
def ban_user(user_id: int, reason: str = None) -> bool:
    try:
        user = User.objects.get(user_id=user_id)
        user.is_banned = True
        user.ban_reason = reason
        user.save(update_fields=['is_banned', 'ban_reason'])
        return True
    except User.DoesNotExist:
        return False


@sync_to_async
def unban_user(user_id: int) -> bool:
    try:
        user = User.objects.get(user_id=user_id)
        user.is_banned = False
        user.ban_reason = None
        user.save(update_fields=['is_banned', 'ban_reason'])
        return True
    except User.DoesNotExist:
        return False


@sync_to_async
def get_bot_settings():
    from apps.core.models import BotSettings
    return BotSettings.get_settings()


@sync_to_async
def update_bot_setting(field: str, value):
    """Bot sozlamasini yangilash"""
    from apps.core.models import BotSettings
    from django.core.cache import cache
    from bot.middlewares.database import clear_settings_cache

    settings = BotSettings.get_settings()
    setattr(settings, field, value)
    settings.save(update_fields=[field])

    # Cache tozalash
    cache.delete('bot_settings')
    clear_settings_cache()

    return settings


@sync_to_async
def check_channel_exists(channel_id: int) -> bool:
    """Kanal mavjudligini tekshirish"""
    from apps.channels.models import Channel
    return Channel.objects.filter(channel_id=channel_id).exists()


@sync_to_async
def save_channel(channel_id: int, username: str, title: str, invite_link: str):
    """Yangi kanal saqlash"""
    from apps.channels.models import Channel
    return Channel.objects.create(
        channel_id=channel_id,
        username=username,
        title=title,
        invite_link=invite_link,
        channel_type='telegram_channel' if username else 'telegram_channel'
    )


@sync_to_async
def save_channel_with_type(channel_id: int, username: str, title: str, invite_link: str, channel_type: str):
    """Yangi kanal saqlash (tur bilan)"""
    from apps.channels.models import Channel
    return Channel.objects.create(
        channel_id=channel_id,
        username=username,
        title=title,
        invite_link=invite_link,
        channel_type=channel_type
    )


@sync_to_async
def get_channel_by_id(pk: int):
    """Kanal olish (Django PK bo'yicha)"""
    from apps.channels.models import Channel
    try:
        return Channel.objects.get(id=pk)
    except Channel.DoesNotExist:
        return None


@sync_to_async
def get_channel_joined_users_count(channel_pk: int) -> int:
    """Kanal orqali kelgan userlar sonini olish"""
    return User.objects.filter(joined_from_channel_id=channel_pk).count()


@sync_to_async
def get_admin_movies(page: int = 1, per_page: int = 8, premium_only: bool = False):
    """Admin uchun kinolar ro'yxati"""
    movies = Movie.objects.all().order_by('-created_at')
    if premium_only:
        movies = movies.filter(is_premium=True)

    total = movies.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page

    return list(movies[start:start + per_page]), total_pages


@sync_to_async
def get_movie_by_code(code: str):
    """Kodni bo'yicha kino olish"""
    try:
        return Movie.objects.select_related('category').get(code=code)
    except Movie.DoesNotExist:
        return None


@sync_to_async
def toggle_movie_status(code: str) -> bool:
    """Kino aktiv/deaktiv"""
    try:
        movie = Movie.objects.get(code=code)
        movie.is_active = not movie.is_active
        movie.save(update_fields=['is_active'])
        return movie.is_active
    except Movie.DoesNotExist:
        return False


@sync_to_async
def toggle_movie_premium(code: str) -> bool:
    """Kino premium/oddiy"""
    try:
        movie = Movie.objects.get(code=code)
        movie.is_premium = not movie.is_premium
        movie.save(update_fields=['is_premium'])
        return movie.is_premium
    except Movie.DoesNotExist:
        return False


@sync_to_async
def delete_movie(code: str) -> bool:
    """Kinoni o'chirish"""
    try:
        movie = Movie.objects.get(code=code)
        movie.delete()
        return True
    except Movie.DoesNotExist:
        return False


@sync_to_async
def get_detailed_movie_stats():
    """Batafsil kino statistikasi"""
    from django.db.models import Sum, Avg

    total = Movie.objects.count()
    active = Movie.objects.filter(is_active=True).count()
    inactive = total - active
    premium = Movie.objects.filter(is_premium=True).count()
    regular = total - premium

    agg = Movie.objects.aggregate(
        total_views=Sum('views'),
        avg_views=Avg('views')
    )

    top_movies = list(Movie.objects.filter(is_active=True).order_by('-views')[:5].values('title', 'views'))

    return {
        'total': total,
        'active': active,
        'inactive': inactive,
        'premium': premium,
        'regular': regular,
        'total_views': agg['total_views'] or 0,
        'avg_views': int(agg['avg_views'] or 0),
        'top_movies': top_movies
    }


@sync_to_async
def toggle_channel_status(pk: int) -> bool:
    """Kanal holatini o'zgartirish"""
    from apps.channels.models import Channel
    try:
        channel = Channel.objects.get(id=pk)
        channel.is_active = not channel.is_active
        channel.save(update_fields=['is_active'])
        return True
    except Channel.DoesNotExist:
        return False


@sync_to_async
def delete_channel(pk: int) -> bool:
    """Kanalni o'chirish"""
    from apps.channels.models import Channel
    try:
        channel = Channel.objects.get(id=pk)
        channel.delete()
        return True
    except Channel.DoesNotExist:
        return False
