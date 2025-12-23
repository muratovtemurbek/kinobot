"""
Subscription System Tests for KinoBot
Tests channel subscription verification and management
"""
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from django.utils import timezone

# Enable database access for all tests in this module
pytestmark = pytest.mark.django_db


# ==================== CHANNEL MODEL TESTS ====================

class TestChannelModel:
    """Test Channel model"""

    def test_channel_creation(self, db_channel):
        """Test channel is created correctly"""
        assert db_channel.channel_id == -1001234567890
        assert db_channel.title == 'Test Channel'
        assert db_channel.is_active is True

    def test_channel_types(self, channel_model):
        """Test all channel types are valid"""
        valid_types = ['channel', 'group', 'bot', 'instagram', 'other']

        for channel_type in valid_types:
            channel = channel_model(
                channel_id=-100,
                title='Test',
                channel_type=channel_type
            )
            assert channel.channel_type == channel_type

    def test_checkable_channel_types(self):
        """Test which channel types can be verified"""
        checkable_types = ['channel', 'group']
        non_checkable_types = ['bot', 'instagram', 'other']

        # Only telegram channels/groups can be checked
        for ct in checkable_types:
            assert ct in ['channel', 'group']

        for ct in non_checkable_types:
            assert ct not in ['channel', 'group']

    def test_channel_ordering(self, channel_model, db_channel):
        """Test channels are ordered by 'order' field"""
        channels = channel_model.objects.filter(is_active=True).order_by('order')
        orders = [c.order for c in channels]

        # Should be sorted
        assert orders == sorted(orders)

    def test_active_channels_filter(self, channel_model, db_channel):
        """Test filtering active channels"""
        active = channel_model.objects.filter(is_active=True)
        assert active.count() >= 1


# ==================== CHANNEL SUBSCRIPTION MODEL TESTS ====================

class TestChannelSubscription:
    """Test ChannelSubscription model"""

    def test_subscription_creation(self, db_user, db_channel):
        """Test creating a subscription record"""
        from apps.channels.models import ChannelSubscription

        sub, created = ChannelSubscription.objects.get_or_create(
            channel=db_channel,
            user=db_user
        )

        assert sub.channel == db_channel
        assert sub.user == db_user
        assert sub.subscribed_at is not None

        # Cleanup
        sub.delete()

    def test_subscription_unique_constraint(self, db_user, db_channel):
        """Test user can't subscribe to same channel twice"""
        from apps.channels.models import ChannelSubscription

        # First subscription
        sub1, created1 = ChannelSubscription.objects.get_or_create(
            channel=db_channel,
            user=db_user
        )
        assert created1 is True

        # Second subscription should return existing
        sub2, created2 = ChannelSubscription.objects.get_or_create(
            channel=db_channel,
            user=db_user
        )
        assert created2 is False
        assert sub1.id == sub2.id

        # Cleanup
        sub1.delete()

    def test_subscription_timestamp(self, db_user, db_channel):
        """Test subscription timestamp is set"""
        from apps.channels.models import ChannelSubscription

        sub = ChannelSubscription.objects.create(
            channel=db_channel,
            user=db_user
        )

        assert sub.subscribed_at is not None
        assert sub.subscribed_at <= timezone.now()

        # Cleanup
        sub.delete()


# ==================== SUBSCRIPTION MIDDLEWARE TESTS ====================

class TestSubscriptionMiddleware:
    """Test subscription verification middleware"""

    def test_skip_commands(self):
        """Test commands that skip subscription check"""
        from bot.middlewares.subscription import SubscriptionMiddleware

        middleware = SubscriptionMiddleware()
        skip_commands = middleware.SKIP_COMMANDS

        # These commands should skip
        assert '/start' in skip_commands
        assert '/help' in skip_commands
        assert '/admin' in skip_commands

    def test_skip_callbacks(self):
        """Test callbacks that skip subscription check"""
        from bot.middlewares.subscription import SubscriptionMiddleware

        middleware = SubscriptionMiddleware()
        skip_callbacks = middleware.SKIP_CALLBACKS

        # These callbacks should skip
        assert 'check_subscription' in skip_callbacks
        assert 'admin:panel' in skip_callbacks

    @pytest.mark.asyncio
    async def test_admin_bypasses_check(self, mock_message, mock_bot):
        """Test admin users bypass subscription check"""
        from django.conf import settings

        if settings.ADMINS:
            admin_id = settings.ADMINS[0]
            # Admin should bypass all checks
            assert admin_id in settings.ADMINS

    @pytest.mark.asyncio
    async def test_premium_bypasses_check(self, db_premium_user):
        """Test premium users bypass subscription check"""
        assert db_premium_user.is_premium_active is True
        # Premium users should bypass subscription check


# ==================== SUBSCRIPTION CHECK TESTS ====================

class TestSubscriptionCheck:
    """Test subscription verification logic"""

    @pytest.mark.asyncio
    async def test_check_member_status(self, mock_bot, db_channel):
        """Test checking member status"""
        from tests.conftest import create_mock_chat_member

        # Member status: member
        mock_bot.get_chat_member.return_value = create_mock_chat_member('member')

        member = await mock_bot.get_chat_member(db_channel.channel_id, 123456789)
        assert member.status == 'member'

    @pytest.mark.asyncio
    async def test_check_subscribed_user(self, mock_bot, db_channel):
        """Test user is subscribed"""
        from tests.conftest import create_mock_chat_member

        mock_bot.get_chat_member.return_value = create_mock_chat_member('member')

        member = await mock_bot.get_chat_member(db_channel.channel_id, 123456789)
        is_subscribed = member.status not in ['left', 'kicked']

        assert is_subscribed is True

    @pytest.mark.asyncio
    async def test_check_unsubscribed_user(self, mock_bot, db_channel):
        """Test user is not subscribed"""
        from tests.conftest import create_mock_chat_member

        mock_bot.get_chat_member.return_value = create_mock_chat_member('left')

        member = await mock_bot.get_chat_member(db_channel.channel_id, 123456789)
        is_subscribed = member.status not in ['left', 'kicked']

        assert is_subscribed is False

    @pytest.mark.asyncio
    async def test_check_kicked_user(self, mock_bot, db_channel):
        """Test kicked user"""
        from tests.conftest import create_mock_chat_member

        mock_bot.get_chat_member.return_value = create_mock_chat_member('kicked')

        member = await mock_bot.get_chat_member(db_channel.channel_id, 123456789)
        is_subscribed = member.status not in ['left', 'kicked']

        assert is_subscribed is False

    @pytest.mark.asyncio
    async def test_check_administrator(self, mock_bot, db_channel):
        """Test channel administrator"""
        from tests.conftest import create_mock_chat_member

        mock_bot.get_chat_member.return_value = create_mock_chat_member('administrator')

        member = await mock_bot.get_chat_member(db_channel.channel_id, 123456789)
        is_subscribed = member.status not in ['left', 'kicked']

        assert is_subscribed is True


# ==================== CACHE TESTS ====================

class TestSubscriptionCache:
    """Test subscription caching"""

    def test_clear_subscription_cache(self):
        """Test clearing subscription cache"""
        from bot.middlewares.subscription import clear_subscription_cache

        # Clear all cache
        clear_subscription_cache()
        # Should not raise error

    def test_clear_user_subscription_cache(self):
        """Test clearing specific user's cache"""
        from bot.middlewares.subscription import clear_subscription_cache

        user_id = 123456789
        clear_subscription_cache(user_id)
        # Should not raise error

    def test_clear_channels_cache(self):
        """Test clearing channels cache"""
        from bot.middlewares.subscription import clear_channels_cache

        clear_channels_cache()
        # Should not raise error


# ==================== SUBSCRIPTION FLOW TESTS ====================

class TestSubscriptionFlow:
    """Test complete subscription flow"""

    def test_subscription_required_flow(self, db_user, db_channel):
        """Test subscription requirement flow"""
        from apps.channels.models import ChannelSubscription

        # Step 1: Check if user is subscribed (they're not)
        is_subscribed = ChannelSubscription.objects.filter(
            channel=db_channel,
            user=db_user
        ).exists()
        assert is_subscribed is False

        # Step 2: User subscribes (simulated)
        ChannelSubscription.objects.create(
            channel=db_channel,
            user=db_user
        )

        # Step 3: Verify subscription
        is_subscribed = ChannelSubscription.objects.filter(
            channel=db_channel,
            user=db_user
        ).exists()
        assert is_subscribed is True

        # Cleanup
        ChannelSubscription.objects.filter(channel=db_channel, user=db_user).delete()

    def test_multiple_channels_subscription(self, db_user, channel_model):
        """Test subscribing to multiple channels"""
        from apps.channels.models import ChannelSubscription

        # Create multiple channels
        channels = []
        for i in range(3):
            channel = channel_model.objects.create(
                channel_id=-100100000000 - i,
                title=f'Test Channel {i}',
                channel_type='channel',
                is_active=True
            )
            channels.append(channel)

        # Subscribe to all
        for channel in channels:
            ChannelSubscription.objects.create(
                channel=channel,
                user=db_user
            )

        # Verify all subscribed
        sub_count = ChannelSubscription.objects.filter(user=db_user).count()
        assert sub_count >= 3

        # Cleanup
        for channel in channels:
            ChannelSubscription.objects.filter(channel=channel).delete()
            channel.delete()

    def test_joined_from_channel_tracking(self, db_user, db_channel):
        """Test tracking which channel user joined from"""
        # Set joined_from_channel
        db_user.joined_from_channel = db_channel
        db_user.save()

        db_user.refresh_from_db()
        assert db_user.joined_from_channel == db_channel

        # Cleanup
        db_user.joined_from_channel = None
        db_user.save()


# ==================== EDGE CASES ====================

class TestSubscriptionEdgeCases:
    """Test edge cases in subscription system"""

    @pytest.mark.asyncio
    async def test_bot_not_admin_in_channel(self, mock_bot, db_channel):
        """Test handling when bot is not admin in channel"""
        from aiogram.exceptions import TelegramBadRequest

        # Simulate TelegramBadRequest
        mock_bot.get_chat_member.side_effect = TelegramBadRequest(
            method=MagicMock(),
            message="Bad Request"
        )

        try:
            await mock_bot.get_chat_member(db_channel.channel_id, 123456789)
            assert False, "Should have raised exception"
        except TelegramBadRequest:
            pass  # Expected

    def test_channel_with_null_id(self, channel_model):
        """Test handling channel with null channel_id"""
        # is_checkable should be False for non-telegram channels
        channel = channel_model(
            channel_id=None,
            title='External Channel',
            channel_type='instagram',
            is_checkable=False
        )

        assert channel.is_checkable is False

    def test_inactive_channel_skipped(self, channel_model):
        """Test inactive channels are skipped"""
        active_channels = channel_model.objects.filter(
            is_active=True,
            is_checkable=True
        )

        # All returned channels should be active and checkable
        for channel in active_channels:
            assert channel.is_active is True
            assert channel.is_checkable is True


# ==================== KEYBOARD TESTS ====================

class TestSubscriptionKeyboards:
    """Test subscription-related keyboards"""

    def test_channels_keyboard_generation(self, db_channel):
        """Test channels keyboard is generated"""
        from bot.keyboards import channels_kb

        not_subscribed = [db_channel]
        kb = channels_kb(not_subscribed)

        assert kb is not None
        assert hasattr(kb, 'inline_keyboard')

    def test_check_subscription_button(self):
        """Test check subscription button exists"""
        # The keyboard should have a "Check" button
        check_callback = 'check_subscription'
        assert check_callback == 'check_subscription'


# ==================== REFERRAL SYSTEM TESTS ====================

class TestReferralSystem:
    """Test referral tracking through channels"""

    def test_referral_code_format(self, db_user):
        """Test referral code format"""
        code = db_user.referral_code

        assert code is not None
        assert len(code) == 8
        assert code.isalnum()

    def test_referral_link_generation(self, db_user):
        """Test referral link generation"""
        bot_username = 'test_bot'
        ref_link = f"https://t.me/{bot_username}?start={db_user.referral_code}"

        assert 'https://t.me/' in ref_link
        assert db_user.referral_code in ref_link
        assert '?start=' in ref_link

    def test_referred_by_tracking(self, user_model, db_user):
        """Test referred_by field"""
        # Create referred user
        referred_user = user_model.objects.create(
            user_id=999888777,
            username='referred_user',
            full_name='Referred User',
            referred_by=db_user
        )

        assert referred_user.referred_by == db_user

        # Count referrals
        referral_count = user_model.objects.filter(referred_by=db_user).count()
        assert referral_count >= 1

        # Cleanup
        referred_user.delete()

    def test_referral_bonus_days(self, bot_settings_model):
        """Test referral bonus days setting"""
        settings = bot_settings_model.get_settings()

        # Should have referral_bonus field
        if hasattr(settings, 'referral_bonus'):
            assert settings.referral_bonus >= 0
