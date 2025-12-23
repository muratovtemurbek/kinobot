"""
Test configuration and fixtures for KinoBot
"""
import os
import sys
import pytest
import django
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.conf import settings

# Enable database access for all tests
pytestmark = pytest.mark.django_db


# ==================== DJANGO MODEL FIXTURES ====================

@pytest.fixture
def user_model():
    """Get User model"""
    from apps.users.models import User
    return User


@pytest.fixture
def movie_model():
    """Get Movie model"""
    from apps.movies.models import Movie
    return Movie


@pytest.fixture
def category_model():
    """Get Category model"""
    from apps.movies.models import Category
    return Category


@pytest.fixture
def channel_model():
    """Get Channel model"""
    from apps.channels.models import Channel
    return Channel


@pytest.fixture
def payment_model():
    """Get Payment model"""
    from apps.payments.models import Payment
    return Payment


@pytest.fixture
def tariff_model():
    """Get Tariff model"""
    from apps.payments.models import Tariff
    return Tariff


@pytest.fixture
def bot_settings_model():
    """Get BotSettings model"""
    from apps.core.models import BotSettings
    return BotSettings


# ==================== TEST DATA FIXTURES ====================

@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        'user_id': 123456789,
        'username': 'test_user',
        'full_name': 'Test User',
        'is_premium': False,
    }


@pytest.fixture
def test_admin_data():
    """Test admin data"""
    return {
        'user_id': settings.ADMINS[0] if settings.ADMINS else 6770531778,
        'username': 'test_admin',
        'full_name': 'Test Admin',
        'is_premium': True,
    }


@pytest.fixture
def test_movie_data():
    """Test movie data"""
    return {
        'code': 99999,
        'title': 'Test Movie',
        'file_id': 'test_file_id_123',
        'year': 2024,
        'quality': '1080p',
        'language': 'uzbek',
        'country': 'uzbekistan',
        'description': 'Test movie description',
        'is_premium': False,
        'is_active': True,
    }


@pytest.fixture
def test_category_data():
    """Test category data"""
    return {
        'name': 'Test Category',
        'emoji': '🎬',
        'slug': 'test-category',
        'is_active': True,
    }


@pytest.fixture
def test_channel_data():
    """Test channel data"""
    return {
        'channel_id': -1001234567890,
        'username': 'test_channel',
        'title': 'Test Channel',
        'channel_type': 'channel',
        'is_active': True,
    }


@pytest.fixture
def test_tariff_data():
    """Test tariff data"""
    return {
        'name': '30 kun',
        'days': 30,
        'price': 10000,
        'discounted_price': 5000,
        'is_active': True,
    }


# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_bot():
    """Mock aiogram Bot"""
    bot = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_video = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_document = AsyncMock()
    bot.delete_webhook = AsyncMock()
    bot.set_my_commands = AsyncMock()
    return bot


@pytest.fixture
def mock_message():
    """Mock aiogram Message"""
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.username = 'test_user'
    message.from_user.full_name = 'Test User'
    message.text = '/start'
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.edit_text = AsyncMock()
    message.delete = AsyncMock()
    message.photo = None
    message.video = None
    message.document = None
    return message


@pytest.fixture
def mock_callback():
    """Mock aiogram CallbackQuery"""
    callback = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.from_user.username = 'test_user'
    callback.from_user.full_name = 'Test User'
    callback.data = 'test_callback'
    callback.answer = AsyncMock()
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.message.delete = AsyncMock()
    return callback


@pytest.fixture
def mock_state():
    """Mock FSMContext"""
    state = AsyncMock()
    state.get_state = AsyncMock(return_value=None)
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    return state


# ==================== DATABASE FIXTURES ====================

@pytest.fixture
def db_user(user_model, test_user_data):
    """Create test user in database"""
    user, created = user_model.objects.get_or_create(
        user_id=test_user_data['user_id'],
        defaults=test_user_data
    )
    yield user
    # Cleanup
    user_model.objects.filter(user_id=test_user_data['user_id']).delete()


@pytest.fixture
def db_admin_user(user_model, test_admin_data):
    """Create test admin user in database"""
    user, created = user_model.objects.get_or_create(
        user_id=test_admin_data['user_id'],
        defaults=test_admin_data
    )
    yield user
    # Cleanup
    user_model.objects.filter(user_id=test_admin_data['user_id']).delete()


@pytest.fixture
def db_premium_user(user_model):
    """Create premium user in database"""
    data = {
        'user_id': 987654321,
        'username': 'premium_user',
        'full_name': 'Premium User',
        'is_premium': True,
        'premium_expires': timezone.now() + timedelta(days=30),
    }
    user, created = user_model.objects.get_or_create(
        user_id=data['user_id'],
        defaults=data
    )
    yield user
    user_model.objects.filter(user_id=data['user_id']).delete()


@pytest.fixture
def db_category(category_model, test_category_data):
    """Create test category in database"""
    category, created = category_model.objects.get_or_create(
        slug=test_category_data['slug'],
        defaults=test_category_data
    )
    yield category
    category_model.objects.filter(slug=test_category_data['slug']).delete()


@pytest.fixture
def db_movie(movie_model, test_movie_data, db_category):
    """Create test movie in database"""
    test_movie_data['category'] = db_category
    movie, created = movie_model.objects.get_or_create(
        code=test_movie_data['code'],
        defaults=test_movie_data
    )
    yield movie
    movie_model.objects.filter(code=test_movie_data['code']).delete()


@pytest.fixture
def db_premium_movie(movie_model, db_category):
    """Create premium test movie in database"""
    data = {
        'code': 88888,
        'title': 'Premium Test Movie',
        'file_id': 'premium_file_id_123',
        'category': db_category,
        'is_premium': True,
        'is_active': True,
    }
    movie, created = movie_model.objects.get_or_create(
        code=data['code'],
        defaults=data
    )
    yield movie
    movie_model.objects.filter(code=data['code']).delete()


@pytest.fixture
def db_channel(channel_model, test_channel_data):
    """Create test channel in database"""
    # Delete existing if any
    channel_model.objects.filter(channel_id=test_channel_data['channel_id']).delete()

    channel = channel_model.objects.create(**test_channel_data)
    yield channel
    # Cleanup
    try:
        channel_model.objects.filter(channel_id=test_channel_data['channel_id']).delete()
    except:
        pass


@pytest.fixture
def db_tariff(tariff_model, test_tariff_data):
    """Create test tariff in database"""
    tariff, created = tariff_model.objects.get_or_create(
        name=test_tariff_data['name'],
        defaults=test_tariff_data
    )
    yield tariff
    tariff_model.objects.filter(name=test_tariff_data['name']).delete()


# ==================== HELPER FUNCTIONS ====================

def create_mock_chat_member(status='member'):
    """Create mock chat member with given status"""
    member = MagicMock()
    member.status = status
    return member
