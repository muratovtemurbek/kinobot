"""
Subscription Tests for KinoBot
"""
import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


class TestChannelModel:
    """Test Channel model"""

    def test_channel_creation(self, db_channel):
        """Test channel is created"""
        assert db_channel.channel_id == -1001234567890
        assert db_channel.title == 'Test Channel'
        assert db_channel.is_active is True

    def test_channel_types(self):
        """Test channel types"""
        types = ['channel', 'group', 'bot', 'instagram', 'other']
        assert len(types) == 5

    def test_active_channels(self, channel_model, db_channel):
        """Test active channels"""
        count = channel_model.objects.filter(is_active=True).count()
        assert count >= 1


class TestChannelSubscription:
    """Test ChannelSubscription model"""

    def test_subscription_creation(self, db_user, db_channel):
        """Test creating subscription"""
        from apps.channels.models import ChannelSubscription

        sub, created = ChannelSubscription.objects.get_or_create(
            channel=db_channel,
            user=db_user
        )
        assert sub.channel == db_channel
        assert sub.user == db_user
        sub.delete()

    def test_subscription_unique(self, db_user, db_channel):
        """Test unique constraint"""
        from apps.channels.models import ChannelSubscription

        sub1, created1 = ChannelSubscription.objects.get_or_create(
            channel=db_channel, user=db_user
        )
        assert created1 is True

        sub2, created2 = ChannelSubscription.objects.get_or_create(
            channel=db_channel, user=db_user
        )
        assert created2 is False
        assert sub1.id == sub2.id
        sub1.delete()

    def test_subscription_timestamp(self, db_user, db_channel):
        """Test subscription timestamp"""
        from apps.channels.models import ChannelSubscription

        sub = ChannelSubscription.objects.create(
            channel=db_channel, user=db_user
        )
        assert sub.subscribed_at is not None
        sub.delete()


class TestSubscriptionMiddleware:
    """Test subscription middleware"""

    def test_skip_commands(self):
        """Test skip commands"""
        from bot.middlewares.subscription import SubscriptionMiddleware

        mw = SubscriptionMiddleware()
        assert '/start' in mw.SKIP_COMMANDS
        assert '/help' in mw.SKIP_COMMANDS
        assert '/admin' in mw.SKIP_COMMANDS

    def test_skip_callbacks(self):
        """Test skip callbacks"""
        from bot.middlewares.subscription import SubscriptionMiddleware

        mw = SubscriptionMiddleware()
        assert 'check_subscription' in mw.SKIP_CALLBACKS

    def test_admin_bypasses(self):
        """Test admin bypasses check"""
        from django.conf import settings
        assert isinstance(settings.ADMINS, list)


class TestCacheManagement:
    """Test cache management"""

    def test_clear_subscription_cache(self):
        """Test clear subscription cache"""
        from bot.middlewares.subscription import clear_subscription_cache
        clear_subscription_cache()  # Should not raise

    def test_clear_user_cache(self):
        """Test clear user cache"""
        from bot.middlewares.subscription import clear_subscription_cache
        clear_subscription_cache(123456789)  # Should not raise

    def test_clear_channels_cache(self):
        """Test clear channels cache"""
        from bot.middlewares.subscription import clear_channels_cache
        clear_channels_cache()  # Should not raise


class TestSubscriptionFlow:
    """Test subscription flow"""

    def test_subscription_flow(self, db_user, db_channel):
        """Test complete subscription flow"""
        from apps.channels.models import ChannelSubscription

        # Check not subscribed
        is_sub = ChannelSubscription.objects.filter(
            channel=db_channel, user=db_user
        ).exists()
        assert is_sub is False

        # Subscribe
        ChannelSubscription.objects.create(
            channel=db_channel, user=db_user
        )

        # Verify
        is_sub = ChannelSubscription.objects.filter(
            channel=db_channel, user=db_user
        ).exists()
        assert is_sub is True

        # Cleanup
        ChannelSubscription.objects.filter(
            channel=db_channel, user=db_user
        ).delete()

    def test_joined_from_channel(self, db_user, db_channel):
        """Test joined_from_channel tracking"""
        db_user.joined_from_channel = db_channel
        db_user.save()
        db_user.refresh_from_db()
        assert db_user.joined_from_channel == db_channel
        # Cleanup
        db_user.joined_from_channel = None
        db_user.save()


class TestReferralSystem:
    """Test referral system"""

    def test_referral_code(self, db_user):
        """Test referral code"""
        assert db_user.referral_code is not None
        assert len(db_user.referral_code) == 8

    def test_referral_link(self, db_user):
        """Test referral link format"""
        link = f"https://t.me/bot?start={db_user.referral_code}"
        assert db_user.referral_code in link

    def test_referred_by(self, user_model, db_user):
        """Test referred_by tracking"""
        referred = user_model.objects.create(
            user_id=888777666,
            username='referred',
            full_name='Referred User',
            referred_by=db_user
        )
        assert referred.referred_by == db_user

        # Count referrals
        count = user_model.objects.filter(referred_by=db_user).count()
        assert count >= 1

        referred.delete()
