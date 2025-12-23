"""
Test configuration and fixtures for KinoBot
"""
import os
import sys
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone
from django.conf import settings

# Mark all tests to use database
pytestmark = pytest.mark.django_db


# ==================== MODEL FIXTURES ====================

@pytest.fixture
def user_model():
    from apps.users.models import User
    return User


@pytest.fixture
def movie_model():
    from apps.movies.models import Movie
    return Movie


@pytest.fixture
def category_model():
    from apps.movies.models import Category
    return Category


@pytest.fixture
def channel_model():
    from apps.channels.models import Channel
    return Channel


@pytest.fixture
def payment_model():
    from apps.payments.models import Payment
    return Payment


@pytest.fixture
def tariff_model():
    from apps.payments.models import Tariff
    return Tariff


@pytest.fixture
def bot_settings_model():
    from apps.core.models import BotSettings
    return BotSettings


# ==================== DATABASE FIXTURES ====================

@pytest.fixture
def db_user(user_model):
    """Create test user"""
    user, _ = user_model.objects.get_or_create(
        user_id=123456789,
        defaults={
            'username': 'test_user',
            'full_name': 'Test User',
            'is_premium': False,
        }
    )
    yield user
    user_model.objects.filter(user_id=123456789).delete()


@pytest.fixture
def db_premium_user(user_model):
    """Create premium test user"""
    user, _ = user_model.objects.get_or_create(
        user_id=987654321,
        defaults={
            'username': 'premium_user',
            'full_name': 'Premium User',
            'is_premium': True,
            'premium_expires': timezone.now() + timedelta(days=30),
        }
    )
    yield user
    user_model.objects.filter(user_id=987654321).delete()


@pytest.fixture
def db_admin_user(user_model):
    """Create admin test user"""
    admin_id = settings.ADMINS[0] if settings.ADMINS else 6770531778
    user, _ = user_model.objects.get_or_create(
        user_id=admin_id,
        defaults={
            'username': 'admin_user',
            'full_name': 'Admin User',
            'is_premium': True,
        }
    )
    yield user
    user_model.objects.filter(user_id=admin_id).delete()


@pytest.fixture
def db_category(category_model):
    """Create test category"""
    category, _ = category_model.objects.get_or_create(
        slug='test-category',
        defaults={
            'name': 'Test Category',
            'emoji': '🎬',
            'is_active': True,
        }
    )
    yield category
    category_model.objects.filter(slug='test-category').delete()


@pytest.fixture
def db_movie(movie_model, db_category):
    """Create test movie"""
    movie, _ = movie_model.objects.get_or_create(
        code=99999,
        defaults={
            'title': 'Test Movie',
            'file_id': 'test_file_id',
            'category': db_category,
            'is_active': True,
            'is_premium': False,
        }
    )
    yield movie
    movie_model.objects.filter(code=99999).delete()


@pytest.fixture
def db_premium_movie(movie_model, db_category):
    """Create premium test movie"""
    movie, _ = movie_model.objects.get_or_create(
        code=88888,
        defaults={
            'title': 'Premium Movie',
            'file_id': 'premium_file_id',
            'category': db_category,
            'is_active': True,
            'is_premium': True,
        }
    )
    yield movie
    movie_model.objects.filter(code=88888).delete()


@pytest.fixture
def db_channel(channel_model):
    """Create test channel"""
    channel_model.objects.filter(channel_id=-1001234567890).delete()
    channel = channel_model.objects.create(
        channel_id=-1001234567890,
        username='test_channel',
        title='Test Channel',
        channel_type='channel',
        is_active=True,
    )
    yield channel
    channel_model.objects.filter(channel_id=-1001234567890).delete()


@pytest.fixture
def db_tariff(tariff_model):
    """Create test tariff"""
    tariff, _ = tariff_model.objects.get_or_create(
        name='Test Tariff',
        defaults={
            'days': 30,
            'price': 10000,
            'discounted_price': 5000,
            'is_active': True,
        }
    )
    yield tariff
    tariff_model.objects.filter(name='Test Tariff').delete()


# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_bot():
    """Mock aiogram Bot"""
    bot = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_video = AsyncMock()
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
    return message


@pytest.fixture
def mock_callback():
    """Mock aiogram CallbackQuery"""
    callback = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.data = 'test_callback'
    callback.answer = AsyncMock()
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
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
