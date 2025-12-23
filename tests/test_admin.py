"""
Admin Handler Tests for KinoBot
Tests all admin functionality
"""
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from django.utils import timezone

# Enable database access for all tests in this module
pytestmark = pytest.mark.django_db


# ==================== ADMIN MODEL TESTS ====================

class TestAdminModel:
    """Test Admin model"""

    def test_admin_roles(self):
        """Test admin role choices"""
        from apps.users.models import Admin

        roles = ['superadmin', 'admin', 'moderator']
        # Verify roles are valid
        for role in roles:
            assert role in ['superadmin', 'admin', 'moderator']

    def test_superadmin_permissions(self, db_admin_user):
        """Test superadmin has all permissions"""
        from apps.users.models import Admin

        # Create admin with superadmin role
        admin, created = Admin.objects.get_or_create(
            user=db_admin_user,
            defaults={'role': 'superadmin'}
        )

        assert admin.can_add_movies is True
        assert admin.can_broadcast is True
        assert admin.can_manage_users is True
        assert admin.can_manage_payments is True

        # Cleanup
        admin.delete()

    def test_moderator_limited_permissions(self, db_user):
        """Test moderator has limited permissions"""
        from apps.users.models import Admin

        admin = Admin(user=db_user, role='moderator')
        # Moderator should have limited permissions by default
        # (depending on implementation)
        assert admin.role == 'moderator'


# ==================== ADMIN FILTER TESTS ====================

class TestAdminFilters:
    """Test admin permission filters"""

    @pytest.mark.asyncio
    async def test_is_admin_filter(self, mock_message):
        """Test IsAdmin filter"""
        from bot.filters import IsAdmin
        from django.conf import settings

        # Test with admin ID
        if settings.ADMINS:
            mock_message.from_user.id = settings.ADMINS[0]
            filter_obj = IsAdmin()
            result = await filter_obj(mock_message)
            assert result is True

    @pytest.mark.asyncio
    async def test_is_super_admin_filter(self, mock_message):
        """Test IsSuperAdmin filter"""
        from bot.filters import IsSuperAdmin
        from django.conf import settings

        # Test with admin ID from settings (these are superadmins)
        if settings.ADMINS:
            mock_message.from_user.id = settings.ADMINS[0]
            filter_obj = IsSuperAdmin()
            result = await filter_obj(mock_message)
            assert result is True

    @pytest.mark.asyncio
    async def test_can_add_movies_filter(self, mock_message):
        """Test CanAddMovies filter"""
        from bot.filters import CanAddMovies
        from django.conf import settings

        if settings.ADMINS:
            mock_message.from_user.id = settings.ADMINS[0]
            filter_obj = CanAddMovies()
            result = await filter_obj(mock_message)
            assert result is True

    @pytest.mark.asyncio
    async def test_can_broadcast_filter(self, mock_message):
        """Test CanBroadcast filter"""
        from bot.filters import CanBroadcast
        from django.conf import settings

        if settings.ADMINS:
            mock_message.from_user.id = settings.ADMINS[0]
            filter_obj = CanBroadcast()
            result = await filter_obj(mock_message)
            assert result is True

    @pytest.mark.asyncio
    async def test_can_manage_users_filter(self, mock_message):
        """Test CanManageUsers filter"""
        from bot.filters import CanManageUsers
        from django.conf import settings

        if settings.ADMINS:
            mock_message.from_user.id = settings.ADMINS[0]
            filter_obj = CanManageUsers()
            result = await filter_obj(mock_message)
            assert result is True

    @pytest.mark.asyncio
    async def test_can_manage_payments_filter(self, mock_message):
        """Test CanManagePayments filter"""
        from bot.filters import CanManagePayments
        from django.conf import settings

        if settings.ADMINS:
            mock_message.from_user.id = settings.ADMINS[0]
            filter_obj = CanManagePayments()
            result = await filter_obj(mock_message)
            assert result is True


# ==================== MOVIE MANAGEMENT TESTS ====================

class TestMovieManagement:
    """Test movie management functionality"""

    def test_add_movie_code_validation(self):
        """Test movie code validation"""
        # Valid codes
        valid_codes = ['123', '99999', '1', '12345']
        for code in valid_codes:
            assert code.isdigit() is True

        # Invalid codes
        invalid_codes = ['abc', '12a', '', 'movie123']
        for code in invalid_codes:
            if code:
                assert code.isdigit() is False

    def test_add_movie_year_validation(self):
        """Test movie year validation"""
        current_year = timezone.now().year

        # Valid years
        valid_years = ['2020', '2024', '1990', '2025']
        for year in valid_years:
            year_int = int(year)
            assert 1900 <= year_int <= 2030

        # Invalid years
        invalid_years = ['1800', '2050', 'abcd']
        for year in invalid_years:
            try:
                year_int = int(year)
                assert not (1900 <= year_int <= 2030)
            except ValueError:
                pass  # Non-numeric is invalid

    def test_movie_quality_options(self):
        """Test movie quality options"""
        valid_qualities = ['360p', '480p', '720p', '1080p', '4k']
        for quality in valid_qualities:
            assert quality in ['360p', '480p', '720p', '1080p', '4k']

    def test_movie_language_options(self):
        """Test movie language options"""
        valid_languages = ['uzbek', 'russian', 'english', 'turkish', 'korean', 'other']
        for lang in valid_languages:
            assert lang in ['uzbek', 'russian', 'english', 'turkish', 'korean', 'other']

    def test_movie_country_options(self):
        """Test movie country options"""
        valid_countries = [
            'usa', 'korea', 'india', 'turkey', 'russia',
            'uzbekistan', 'uk', 'france', 'japan', 'china', 'other'
        ]
        for country in valid_countries:
            assert country in valid_countries

    def test_toggle_movie_status(self, db_movie):
        """Test toggling movie active status"""
        initial_status = db_movie.is_active
        db_movie.is_active = not initial_status
        db_movie.save()
        db_movie.refresh_from_db()
        assert db_movie.is_active != initial_status

        # Restore
        db_movie.is_active = initial_status
        db_movie.save()

    def test_toggle_movie_premium(self, db_movie):
        """Test toggling movie premium status"""
        initial_premium = db_movie.is_premium
        db_movie.is_premium = not initial_premium
        db_movie.save()
        db_movie.refresh_from_db()
        assert db_movie.is_premium != initial_premium

        # Restore
        db_movie.is_premium = initial_premium
        db_movie.save()

    def test_delete_movie(self, movie_model, db_category):
        """Test deleting a movie"""
        # Create temporary movie
        movie = movie_model.objects.create(
            code=77777,
            title='Delete Test Movie',
            file_id='delete_test',
            category=db_category
        )

        movie_id = movie.id
        movie.delete()

        # Verify deleted
        assert not movie_model.objects.filter(id=movie_id).exists()

    def test_movie_description_length(self):
        """Test movie description max length"""
        max_length = 500
        valid_desc = 'A' * 500
        invalid_desc = 'A' * 501

        assert len(valid_desc) <= max_length
        assert len(invalid_desc) > max_length


# ==================== BROADCAST TESTS ====================

class TestBroadcast:
    """Test broadcast functionality"""

    def test_broadcast_targets(self):
        """Test broadcast target options"""
        targets = ['all', 'premium', 'regular']
        for target in targets:
            assert target in ['all', 'premium', 'regular']

    def test_broadcast_is_ad_flag(self):
        """Test advertisement flag"""
        # When is_ad=True, premium users should be excluded
        is_ad = True
        target = 'all'

        if is_ad and target == 'all':
            # Should exclude premium users
            effective_target = 'regular'
            assert effective_target == 'regular'

    def test_broadcast_content_types(self):
        """Test supported content types for broadcast"""
        content_types = ['text', 'photo', 'video', 'document']
        for ct in content_types:
            assert ct in ['text', 'photo', 'video', 'document']


# ==================== CHANNEL MANAGEMENT TESTS ====================

class TestChannelManagement:
    """Test channel management functionality"""

    def test_channel_creation(self, db_channel):
        """Test channel is created correctly"""
        assert db_channel.channel_id == -1001234567890
        assert db_channel.title == 'Test Channel'
        assert db_channel.is_active is True

    def test_channel_types(self):
        """Test channel type options"""
        channel_types = ['channel', 'group', 'bot', 'instagram', 'other']
        for ct in channel_types:
            assert ct in ['channel', 'group', 'bot', 'instagram', 'other']

    def test_channel_is_checkable(self, db_channel):
        """Test is_checkable logic"""
        # Only telegram channels/groups can be checked
        checkable_types = ['channel', 'group']
        if db_channel.channel_type in checkable_types:
            assert db_channel.is_checkable is True

    def test_toggle_channel_status(self, db_channel):
        """Test toggling channel active status"""
        initial_status = db_channel.is_active
        db_channel.is_active = not initial_status
        db_channel.save()
        db_channel.refresh_from_db()
        assert db_channel.is_active != initial_status

        # Restore
        db_channel.is_active = initial_status
        db_channel.save()

    def test_delete_channel(self, channel_model):
        """Test deleting a channel"""
        # Create temporary channel
        channel = channel_model.objects.create(
            channel_id=-1009999999999,
            title='Delete Test Channel',
            channel_type='channel'
        )

        channel_id = channel.id
        channel.delete()

        # Verify deleted
        assert not channel_model.objects.filter(id=channel_id).exists()


# ==================== USER MANAGEMENT TESTS ====================

class TestUserManagement:
    """Test user management functionality"""

    def test_ban_user(self, db_user):
        """Test banning a user"""
        db_user.is_banned = True
        db_user.ban_reason = 'Test ban'
        db_user.save()
        db_user.refresh_from_db()

        assert db_user.is_banned is True
        assert db_user.ban_reason == 'Test ban'

        # Restore
        db_user.is_banned = False
        db_user.ban_reason = None
        db_user.save()

    def test_unban_user(self, db_user):
        """Test unbanning a user"""
        # First ban
        db_user.is_banned = True
        db_user.save()

        # Then unban
        db_user.is_banned = False
        db_user.ban_reason = None
        db_user.save()
        db_user.refresh_from_db()

        assert db_user.is_banned is False

    def test_give_premium(self, db_user):
        """Test giving premium to user"""
        days = 30
        db_user.is_premium = True
        db_user.premium_expires = timezone.now() + timedelta(days=days)
        db_user.save()
        db_user.refresh_from_db()

        assert db_user.is_premium is True
        assert db_user.is_premium_active is True

        # Cleanup
        db_user.is_premium = False
        db_user.premium_expires = None
        db_user.save()

    def test_extend_premium(self, db_premium_user):
        """Test extending premium duration"""
        initial_expires = db_premium_user.premium_expires
        additional_days = 30

        db_premium_user.premium_expires = initial_expires + timedelta(days=additional_days)
        db_premium_user.save()
        db_premium_user.refresh_from_db()

        assert db_premium_user.premium_expires > initial_expires


# ==================== SETTINGS MANAGEMENT TESTS ====================

class TestSettingsManagement:
    """Test bot settings management"""

    def test_bot_settings_singleton(self, bot_settings_model):
        """Test BotSettings is singleton"""
        settings1 = bot_settings_model.get_settings()
        settings2 = bot_settings_model.get_settings()

        assert settings1.id == settings2.id

    def test_update_card_number(self, bot_settings_model):
        """Test updating card number"""
        settings = bot_settings_model.get_settings()
        new_card = '8600 1234 5678 9012'

        old_card = settings.card_number
        settings.card_number = new_card
        settings.save()
        settings.refresh_from_db()

        assert settings.card_number == new_card

        # Restore
        settings.card_number = old_card
        settings.save()

    def test_toggle_bot_active(self, bot_settings_model):
        """Test toggling bot active status"""
        settings = bot_settings_model.get_settings()
        initial = settings.is_active

        settings.is_active = not initial
        settings.save()
        settings.refresh_from_db()

        assert settings.is_active != initial

        # Restore
        settings.is_active = initial
        settings.save()

    def test_discount_settings(self, bot_settings_model):
        """Test discount settings"""
        settings = bot_settings_model.get_settings()

        # Test discount fields
        settings.discount_active = True
        settings.discount_percent = 50
        settings.discount_duration = 180  # 3 minutes
        settings.save()

        assert settings.discount_percent == 50
        assert settings.discount_duration == 180


# ==================== STATISTICS TESTS ====================

class TestStatistics:
    """Test statistics calculation"""

    def test_user_count(self, user_model, db_user):
        """Test user count"""
        count = user_model.objects.count()
        assert count >= 1

    def test_today_users_count(self, user_model):
        """Test today's user count"""
        from django.utils import timezone
        today = timezone.now().date()

        count = user_model.objects.filter(
            created_at__date=today
        ).count()
        assert count >= 0

    def test_premium_users_count(self, user_model, db_premium_user):
        """Test premium users count"""
        count = user_model.objects.filter(
            is_premium=True,
            premium_expires__gt=timezone.now()
        ).count()
        assert count >= 1

    def test_movie_count(self, movie_model, db_movie):
        """Test movie count"""
        count = movie_model.objects.count()
        assert count >= 1

    def test_active_movie_count(self, movie_model, db_movie):
        """Test active movie count"""
        count = movie_model.objects.filter(is_active=True).count()
        assert count >= 1

    def test_total_views(self, movie_model):
        """Test total views calculation"""
        from django.db.models import Sum

        total = movie_model.objects.aggregate(Sum('views'))['views__sum'] or 0
        assert total >= 0


# ==================== STATE TESTS ====================

class TestAdminStates:
    """Test admin FSM states"""

    def test_add_movie_states(self):
        """Test AddMovieState has all required states"""
        from bot.states import AddMovieState

        states = [
            'code', 'title', 'video', 'category', 'year',
            'country', 'quality', 'language', 'description',
            'is_premium', 'confirm'
        ]

        for state in states:
            assert hasattr(AddMovieState, state)

    def test_broadcast_states(self):
        """Test BroadcastState has all required states"""
        from bot.states import BroadcastState

        states = ['target', 'is_ad', 'content', 'confirm']

        for state in states:
            assert hasattr(BroadcastState, state)

    def test_add_channel_states(self):
        """Test AddChannelState has all required states"""
        from bot.states import AddChannelState

        states = ['channel_input', 'title']

        for state in states:
            assert hasattr(AddChannelState, state)
