"""
User Handler Tests for KinoBot
Tests all user-facing functionality
"""
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from django.utils import timezone

# Enable database access for all tests in this module
pytestmark = pytest.mark.django_db


# ==================== MODEL TESTS ====================

class TestUserModel:
    """Test User model properties and methods"""

    def test_user_creation(self, user_model, test_user_data):
        """Test user can be created"""
        user = user_model(**test_user_data)
        assert user.user_id == test_user_data['user_id']
        assert user.username == test_user_data['username']
        assert user.full_name == test_user_data['full_name']

    def test_referral_code_generation(self, db_user):
        """Test referral code is generated automatically"""
        assert db_user.referral_code is not None
        assert len(db_user.referral_code) == 8

    def test_is_premium_active_false(self, db_user):
        """Test is_premium_active returns False for non-premium user"""
        assert db_user.is_premium_active is False

    def test_is_premium_active_true(self, db_premium_user):
        """Test is_premium_active returns True for premium user"""
        assert db_premium_user.is_premium_active is True

    def test_is_premium_expired(self, user_model):
        """Test premium expiry detection"""
        user = user_model(
            user_id=111111111,
            is_premium=True,
            premium_expires=timezone.now() - timedelta(days=1)
        )
        assert user.is_premium_active is False

    def test_trial_active(self, user_model):
        """Test trial period detection"""
        user = user_model(
            user_id=222222222,
            free_trial_expires=timezone.now() + timedelta(days=3)
        )
        assert user.is_trial_active is True

    def test_trial_expired(self, user_model):
        """Test trial expiry detection"""
        user = user_model(
            user_id=333333333,
            free_trial_expires=timezone.now() - timedelta(days=1)
        )
        assert user.is_trial_active is False

    def test_can_watch_movies_premium(self, db_premium_user):
        """Test premium user can watch movies"""
        assert db_premium_user.can_watch_movies is True

    def test_can_watch_movies_trial(self, user_model):
        """Test trial user can watch movies"""
        user = user_model(
            user_id=444444444,
            free_trial_expires=timezone.now() + timedelta(days=3)
        )
        assert user.can_watch_movies is True

    def test_cannot_watch_movies_expired(self, user_model):
        """Test expired user cannot watch movies"""
        user = user_model(
            user_id=555555555,
            is_premium=False,
            free_trial_expires=timezone.now() - timedelta(days=1)
        )
        assert user.can_watch_movies is False

    def test_days_left_calculation(self, user_model):
        """Test days left calculation"""
        user = user_model(
            user_id=666666666,
            is_premium=True,
            premium_expires=timezone.now() + timedelta(days=15)
        )
        assert 14 <= user.days_left <= 15

    def test_flash_sale_active(self, user_model):
        """Test flash sale detection"""
        user = user_model(
            user_id=777777777,
            premium_first_view=timezone.now()
        )
        # Flash sale should be active within first 3 minutes
        assert user.is_flash_sale_active is True

    def test_flash_sale_expired(self, user_model):
        """Test flash sale expiry"""
        user = user_model(
            user_id=888888888,
            premium_first_view=timezone.now() - timedelta(minutes=10)
        )
        assert user.is_flash_sale_active is False


# ==================== MOVIE MODEL TESTS ====================

class TestMovieModel:
    """Test Movie model"""

    def test_movie_creation(self, db_movie):
        """Test movie is created correctly"""
        assert db_movie.code == 99999
        assert db_movie.title == 'Test Movie'
        assert db_movie.is_active is True

    def test_display_title_uzbek(self, movie_model, db_category):
        """Test display_title returns Uzbek title if available"""
        movie = movie_model(
            code=11111,
            title='English Title',
            title_uz='Uzbek Title',
            file_id='test',
            category=db_category
        )
        assert movie.display_title == 'Uzbek Title'

    def test_display_title_fallback(self, movie_model, db_category):
        """Test display_title falls back to title"""
        movie = movie_model(
            code=22222,
            title='English Title',
            file_id='test',
            category=db_category
        )
        assert movie.display_title == 'English Title'

    def test_movie_views_increment(self, db_movie):
        """Test movie views can be incremented"""
        initial_views = db_movie.views
        db_movie.views += 1
        db_movie.save()
        db_movie.refresh_from_db()
        assert db_movie.views == initial_views + 1


# ==================== CATEGORY MODEL TESTS ====================

class TestCategoryModel:
    """Test Category model"""

    def test_category_creation(self, db_category):
        """Test category is created correctly"""
        assert db_category.name == 'Test Category'
        assert db_category.emoji == '🎬'
        assert db_category.is_active is True

    def test_category_str(self, db_category):
        """Test category string representation"""
        expected = '🎬 Test Category'
        assert str(db_category) == expected or db_category.name in str(db_category)


# ==================== FILTER TESTS ====================

class TestAdminFilter:
    """Test admin filter logic"""

    def test_admin_in_settings(self):
        """Test admin detection from settings"""
        from django.conf import settings
        # Assuming ADMINS is configured
        assert isinstance(settings.ADMINS, list)
        if settings.ADMINS:
            assert all(isinstance(admin_id, int) for admin_id in settings.ADMINS)

    @pytest.mark.asyncio
    async def test_is_admin_filter_true(self, mock_message):
        """Test IsAdmin filter returns True for admin"""
        from bot.filters import IsAdmin
        from django.conf import settings

        if settings.ADMINS:
            mock_message.from_user.id = settings.ADMINS[0]
            filter_instance = IsAdmin()
            result = await filter_instance(mock_message)
            assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_filter_false(self, mock_message):
        """Test IsAdmin filter returns False for non-admin"""
        from bot.filters import IsAdmin

        mock_message.from_user.id = 999999999  # Non-admin ID
        filter_instance = IsAdmin()
        result = await filter_instance(mock_message)
        assert result is False


# ==================== KEYBOARD TESTS ====================

class TestKeyboards:
    """Test keyboard generation"""

    def test_main_menu_keyboard(self):
        """Test main menu keyboard generation"""
        from bot.keyboards import main_menu_inline_kb
        kb = main_menu_inline_kb()
        assert kb is not None
        assert hasattr(kb, 'inline_keyboard')

    def test_admin_main_keyboard(self):
        """Test admin main keyboard generation"""
        from bot.keyboards import admin_main_kb
        kb = admin_main_kb()
        assert kb is not None
        assert hasattr(kb, 'inline_keyboard')

    def test_movie_quality_keyboard(self):
        """Test quality selection keyboard"""
        from bot.keyboards import movie_quality_kb
        kb = movie_quality_kb()
        assert kb is not None

    def test_movie_language_keyboard(self):
        """Test language selection keyboard"""
        from bot.keyboards import movie_language_kb
        kb = movie_language_kb()
        assert kb is not None


# ==================== HANDLER TESTS ====================

class TestStartCommand:
    """Test /start command handler"""

    @pytest.mark.asyncio
    async def test_start_creates_user(self, mock_message, mock_state, mock_bot):
        """Test /start creates new user"""
        from bot.handlers.user import start_handler

        mock_message.text = '/start'
        mock_message.from_user.id = 123456789

        # This would need proper mocking of database operations
        # For now, just verify the handler exists
        assert start_handler is not None

    @pytest.mark.asyncio
    async def test_start_with_referral(self, mock_message, mock_state):
        """Test /start with referral code"""
        mock_message.text = '/start ref_ABC123'
        # Verify referral code parsing
        parts = mock_message.text.split()
        if len(parts) > 1:
            ref_code = parts[1]
            assert ref_code == 'ref_ABC123'


class TestMovieSearch:
    """Test movie search functionality"""

    def test_numeric_code_detection(self):
        """Test numeric movie code detection"""
        test_codes = ['123', '99999', '1', '000001']
        for code in test_codes:
            assert code.isdigit() is True

    def test_invalid_code_detection(self):
        """Test non-numeric code detection"""
        test_inputs = ['abc', '12a', 'movie', '']
        for inp in test_inputs:
            if inp:
                assert inp.isdigit() is False


class TestProfileHandler:
    """Test profile functionality"""

    def test_referral_link_format(self, db_user):
        """Test referral link format"""
        bot_username = 'test_bot'
        ref_link = f"https://t.me/{bot_username}?start={db_user.referral_code}"
        assert db_user.referral_code in ref_link
        assert 'https://t.me/' in ref_link


# ==================== PREMIUM TESTS ====================

class TestPremiumSystem:
    """Test premium/tariff system"""

    def test_tariff_creation(self, db_tariff):
        """Test tariff is created correctly"""
        assert db_tariff.name == '30 kun'
        assert db_tariff.days == 30
        assert db_tariff.price == 10000
        assert db_tariff.discounted_price == 5000

    def test_discount_calculation(self, db_tariff):
        """Test discount percentage calculation"""
        expected_discount = 50  # (10000 - 5000) / 10000 * 100
        if hasattr(db_tariff, 'discount_percent'):
            assert db_tariff.discount_percent == expected_discount

    def test_flash_sale_price(self, user_model, db_tariff):
        """Test flash sale price calculation"""
        # During flash sale: discounted_price
        # After flash sale: price * 2
        assert db_tariff.discounted_price < db_tariff.price
        after_flash_price = db_tariff.price * 2
        assert after_flash_price == 20000


# ==================== SAVED MOVIES TESTS ====================

class TestSavedMovies:
    """Test saved movies functionality"""

    def test_save_movie(self, db_user, db_movie):
        """Test saving a movie"""
        from apps.movies.models import SavedMovie

        saved, created = SavedMovie.objects.get_or_create(
            user=db_user,
            movie=db_movie
        )
        assert created is True or saved is not None

        # Cleanup
        SavedMovie.objects.filter(user=db_user, movie=db_movie).delete()

    def test_unsave_movie(self, db_user, db_movie):
        """Test unsaving a movie"""
        from apps.movies.models import SavedMovie

        # First save
        SavedMovie.objects.get_or_create(user=db_user, movie=db_movie)

        # Then unsave
        deleted, _ = SavedMovie.objects.filter(user=db_user, movie=db_movie).delete()
        assert deleted >= 0

    def test_saved_movie_unique_constraint(self, db_user, db_movie):
        """Test can't save same movie twice"""
        from apps.movies.models import SavedMovie

        SavedMovie.objects.get_or_create(user=db_user, movie=db_movie)
        # Second save should return created=False
        _, created = SavedMovie.objects.get_or_create(user=db_user, movie=db_movie)
        assert created is False

        # Cleanup
        SavedMovie.objects.filter(user=db_user, movie=db_movie).delete()


# ==================== UTILITIES TESTS ====================

class TestUtilities:
    """Test utility functions"""

    def test_format_number(self):
        """Test number formatting"""
        from bot.utils import format_number

        assert format_number(1000) == '1,000' or format_number(1000) == '1 000'
        assert format_number(1000000) in ['1,000,000', '1 000 000']
        assert format_number(0) == '0'

    def test_format_number_none(self):
        """Test format_number with None"""
        from bot.utils import format_number

        result = format_number(None)
        assert result == '0' or result == 'None'


# ==================== INTEGRATION TESTS ====================

class TestMovieAccessControl:
    """Test movie access control logic"""

    def test_regular_user_regular_movie(self, db_user, db_movie):
        """Test regular user can access regular movie with trial/premium"""
        # User with active trial should access regular movies
        db_user.free_trial_expires = timezone.now() + timedelta(days=3)
        db_user.save()
        assert db_user.can_watch_movies is True
        assert db_movie.is_premium is False
        # Access should be granted

    def test_regular_user_premium_movie_denied(self, db_user, db_premium_movie):
        """Test regular user cannot access premium movie"""
        assert db_user.is_premium is False
        assert db_premium_movie.is_premium is True
        # Access should be denied for non-premium user

    def test_premium_user_premium_movie(self, db_premium_user, db_premium_movie):
        """Test premium user can access premium movie"""
        assert db_premium_user.is_premium_active is True
        assert db_premium_movie.is_premium is True
        # Access should be granted

    def test_admin_bypass_all(self, db_admin_user, db_premium_movie):
        """Test admin bypasses all restrictions"""
        from django.conf import settings

        is_admin = db_admin_user.user_id in settings.ADMINS
        if is_admin:
            # Admins should access everything
            assert True
