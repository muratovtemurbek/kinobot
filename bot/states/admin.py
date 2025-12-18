from aiogram.fsm.state import State, StatesGroup


class AddMovieState(StatesGroup):
    """Kino qo'shish holatlari"""
    code = State()
    title = State()
    video = State()
    category = State()
    year = State()
    country = State()
    quality = State()
    language = State()
    description = State()
    is_premium = State()
    confirm = State()  # Tasdiqlash


class BroadcastState(StatesGroup):
    """Xabar yuborish holatlari"""
    target = State()
    is_ad = State()
    content = State()
    confirm = State()


class AddChannelState(StatesGroup):
    """Kanal qo'shish holatlari"""
    channel_input = State()
    title = State()


class EditSettingsState(StatesGroup):
    """Sozlamalarni tahrirlash"""
    card_number = State()
    card_holder = State()
    trial_days = State()
    referral_bonus = State()
