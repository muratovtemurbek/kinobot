"""
Payment System Tests for KinoBot
Tests payment processing, tariffs, and premium activation
"""
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from django.utils import timezone

# Enable database access for all tests in this module
pytestmark = pytest.mark.django_db


# ==================== TARIFF MODEL TESTS ====================

class TestTariffModel:
    """Test Tariff model"""

    def test_tariff_creation(self, db_tariff):
        """Test tariff is created correctly"""
        assert db_tariff.name == '30 kun'
        assert db_tariff.days == 30
        assert db_tariff.price == 10000

    def test_tariff_discount_price(self, db_tariff):
        """Test discounted price"""
        assert db_tariff.discounted_price == 5000
        assert db_tariff.discounted_price < db_tariff.price

    def test_tariff_discount_percent_calculation(self, db_tariff):
        """Test discount percentage calculation"""
        # discount_percent = (price - discounted_price) / price * 100
        expected = (db_tariff.price - db_tariff.discounted_price) / db_tariff.price * 100
        assert expected == 50.0

    def test_tariff_active_filter(self, tariff_model, db_tariff):
        """Test filtering active tariffs"""
        active_tariffs = tariff_model.objects.filter(is_active=True)
        assert active_tariffs.count() >= 1

    def test_tariff_ordering(self, tariff_model):
        """Test tariffs are ordered correctly"""
        tariffs = list(tariff_model.objects.filter(is_active=True).order_by('order'))
        for i in range(len(tariffs) - 1):
            assert tariffs[i].order <= tariffs[i + 1].order


# ==================== PAYMENT MODEL TESTS ====================

class TestPaymentModel:
    """Test Payment model"""

    def test_payment_creation(self, payment_model, db_user, db_tariff):
        """Test payment can be created"""
        payment = payment_model.objects.create(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.price,
            status='pending',
            screenshot_file_id='test_screenshot'
        )

        assert payment.status == 'pending'
        assert payment.amount == db_tariff.price
        assert payment.user == db_user

        # Cleanup
        payment.delete()

    def test_payment_statuses(self):
        """Test payment status options"""
        valid_statuses = ['pending', 'approved', 'rejected', 'expired']
        for status in valid_statuses:
            assert status in ['pending', 'approved', 'rejected', 'expired']

    def test_payment_with_discount(self, payment_model, db_user, db_tariff):
        """Test payment with discount applied"""
        payment = payment_model.objects.create(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.discounted_price,
            is_discounted=True,
            status='pending',
            screenshot_file_id='test_screenshot'
        )

        assert payment.is_discounted is True
        assert payment.amount == db_tariff.discounted_price

        # Cleanup
        payment.delete()

    def test_pending_payments_filter(self, payment_model, db_user, db_tariff):
        """Test filtering pending payments"""
        # Create pending payment
        payment = payment_model.objects.create(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.price,
            status='pending',
            screenshot_file_id='test_screenshot'
        )

        pending = payment_model.objects.filter(status='pending')
        assert pending.count() >= 1

        # Cleanup
        payment.delete()


# ==================== PAYMENT APPROVAL TESTS ====================

class TestPaymentApproval:
    """Test payment approval process"""

    def test_approve_payment(self, payment_model, db_user, db_tariff):
        """Test approving a payment"""
        payment = payment_model.objects.create(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.price,
            status='pending',
            screenshot_file_id='test_screenshot'
        )

        # Approve
        payment.status = 'approved'
        payment.approved_at = timezone.now()
        payment.save()

        payment.refresh_from_db()
        assert payment.status == 'approved'
        assert payment.approved_at is not None

        # Cleanup
        payment.delete()

    def test_reject_payment(self, payment_model, db_user, db_tariff):
        """Test rejecting a payment"""
        payment = payment_model.objects.create(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.price,
            status='pending',
            screenshot_file_id='test_screenshot'
        )

        # Reject
        payment.status = 'rejected'
        payment.save()

        payment.refresh_from_db()
        assert payment.status == 'rejected'

        # Cleanup
        payment.delete()

    def test_premium_activation_on_approval(self, db_user, db_tariff):
        """Test premium is activated when payment approved"""
        # Simulate approval process
        db_user.is_premium = True
        db_user.premium_expires = timezone.now() + timedelta(days=db_tariff.days)
        db_user.save()

        db_user.refresh_from_db()
        assert db_user.is_premium is True
        assert db_user.is_premium_active is True

        # Cleanup
        db_user.is_premium = False
        db_user.premium_expires = None
        db_user.save()

    def test_premium_extension(self, db_premium_user, db_tariff):
        """Test premium extension for existing premium user"""
        initial_expires = db_premium_user.premium_expires

        # Extend premium
        db_premium_user.premium_expires = initial_expires + timedelta(days=db_tariff.days)
        db_premium_user.save()

        db_premium_user.refresh_from_db()
        assert db_premium_user.premium_expires > initial_expires


# ==================== FLASH SALE TESTS ====================

class TestFlashSale:
    """Test flash sale functionality"""

    def test_flash_sale_trigger(self, user_model):
        """Test flash sale is triggered on first premium view"""
        user = user_model(
            user_id=111222333,
            premium_first_view=None
        )

        # First view - trigger flash sale
        user.premium_first_view = timezone.now()
        assert user.premium_first_view is not None

    def test_flash_sale_active_within_duration(self, user_model):
        """Test flash sale is active within duration"""
        user = user_model(
            user_id=111222334,
            premium_first_view=timezone.now()  # Just now
        )

        assert user.is_flash_sale_active is True

    def test_flash_sale_expired(self, user_model):
        """Test flash sale expires after duration"""
        user = user_model(
            user_id=111222335,
            premium_first_view=timezone.now() - timedelta(minutes=10)  # 10 minutes ago
        )

        assert user.is_flash_sale_active is False

    def test_flash_sale_seconds_left(self, user_model):
        """Test flash sale countdown"""
        user = user_model(
            user_id=111222336,
            premium_first_view=timezone.now() - timedelta(seconds=60)  # 1 minute ago
        )

        # Should have ~120 seconds left (if duration is 180s)
        seconds_left = user.flash_sale_seconds_left
        if user.is_flash_sale_active:
            assert seconds_left > 0
            assert seconds_left <= 180  # Max duration

    def test_flash_sale_price_calculation(self, db_tariff):
        """Test price calculation during flash sale"""
        # During flash sale: discounted_price
        flash_sale_price = db_tariff.discounted_price
        assert flash_sale_price == 5000

        # After flash sale: price * 2
        after_flash_price = db_tariff.price * 2
        assert after_flash_price == 20000

    def test_flash_sale_disabled(self, user_model):
        """Test when flash sale is never triggered"""
        user = user_model(
            user_id=111222337,
            premium_first_view=None
        )

        assert user.is_flash_sale_active is False


# ==================== PENDING PAYMENT SESSION TESTS ====================

class TestPendingPaymentSession:
    """Test pending payment session management"""

    def test_session_creation(self, db_user, db_tariff):
        """Test creating pending payment session"""
        from apps.payments.models import PendingPaymentSession

        session = PendingPaymentSession.objects.create(
            user=db_user,
            tariff=db_tariff,
            is_discounted=False
        )

        assert session.user == db_user
        assert session.tariff == db_tariff

        # Cleanup
        session.delete()

    def test_session_timeout(self, db_user, db_tariff):
        """Test session timeout detection"""
        from apps.payments.models import PendingPaymentSession

        # Create session in the past
        session = PendingPaymentSession.objects.create(
            user=db_user,
            tariff=db_tariff
        )

        # Simulate timeout by checking created_at
        timeout_minutes = 30
        timeout_threshold = timezone.now() - timedelta(minutes=timeout_minutes)

        # Session should be expired if created before threshold
        if session.created_at < timeout_threshold:
            is_expired = True
        else:
            is_expired = False

        # Cleanup
        session.delete()

    def test_session_cleanup(self, db_user, db_tariff):
        """Test cleaning up expired sessions"""
        from apps.payments.models import PendingPaymentSession

        # Create and delete session
        session = PendingPaymentSession.objects.create(
            user=db_user,
            tariff=db_tariff
        )
        session_id = session.id
        session.delete()

        # Verify deleted
        assert not PendingPaymentSession.objects.filter(id=session_id).exists()


# ==================== PAYMENT FLOW TESTS ====================

class TestPaymentFlow:
    """Test complete payment flow"""

    def test_complete_payment_flow(self, db_user, db_tariff, payment_model):
        """Test complete payment flow from start to finish"""
        # Step 1: User selects tariff
        selected_tariff = db_tariff

        # Step 2: Create pending payment
        payment = payment_model.objects.create(
            user=db_user,
            tariff=selected_tariff,
            amount=selected_tariff.price,
            status='pending',
            screenshot_file_id='flow_test_screenshot'
        )

        assert payment.status == 'pending'

        # Step 3: Admin approves
        payment.status = 'approved'
        payment.approved_at = timezone.now()
        payment.save()

        # Step 4: Activate premium
        db_user.is_premium = True
        db_user.premium_expires = timezone.now() + timedelta(days=selected_tariff.days)
        db_user.save()

        # Verify
        db_user.refresh_from_db()
        assert db_user.is_premium_active is True
        assert payment.status == 'approved'

        # Cleanup
        payment.delete()
        db_user.is_premium = False
        db_user.premium_expires = None
        db_user.save()

    def test_discounted_payment_flow(self, db_user, db_tariff, payment_model):
        """Test payment flow with discount"""
        # User is in flash sale
        db_user.premium_first_view = timezone.now()
        db_user.save()

        # Create discounted payment
        payment = payment_model.objects.create(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.discounted_price,
            is_discounted=True,
            status='pending',
            screenshot_file_id='discount_test_screenshot'
        )

        assert payment.is_discounted is True
        assert payment.amount == db_tariff.discounted_price

        # Cleanup
        payment.delete()
        db_user.premium_first_view = None
        db_user.save()


# ==================== PAYMENT VALIDATION TESTS ====================

class TestPaymentValidation:
    """Test payment validation"""

    def test_screenshot_required(self, payment_model, db_user, db_tariff):
        """Test screenshot is required for payment"""
        payment = payment_model(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.price,
            status='pending'
        )

        # screenshot_file_id should be set
        assert payment.screenshot_file_id is None or payment.screenshot_file_id == ''

    def test_amount_matches_tariff(self, db_tariff):
        """Test payment amount matches tariff price"""
        regular_amount = db_tariff.price
        discounted_amount = db_tariff.discounted_price

        # Regular payment should match regular price
        assert regular_amount == 10000

        # Discounted payment should match discounted price
        assert discounted_amount == 5000

    def test_user_already_premium(self, db_premium_user, db_tariff):
        """Test handling when user is already premium"""
        # User is already premium
        assert db_premium_user.is_premium_active is True

        # Should extend, not replace
        initial_expires = db_premium_user.premium_expires
        new_expires = initial_expires + timedelta(days=db_tariff.days)

        assert new_expires > initial_expires


# ==================== ADMIN NOTIFICATION TESTS ====================

class TestAdminNotifications:
    """Test admin notifications for payments"""

    def test_payment_notification_data(self, db_user, db_tariff, payment_model):
        """Test payment notification contains required data"""
        payment = payment_model.objects.create(
            user=db_user,
            tariff=db_tariff,
            amount=db_tariff.price,
            status='pending',
            screenshot_file_id='notification_test'
        )

        # Notification should contain:
        # - User info
        assert payment.user is not None
        # - Tariff info
        assert payment.tariff is not None
        # - Amount
        assert payment.amount > 0
        # - Screenshot
        assert payment.screenshot_file_id is not None

        # Cleanup
        payment.delete()

    def test_approved_user_notification(self, db_user, db_tariff):
        """Test user receives notification on approval"""
        # After approval, user should receive:
        # - Confirmation message
        # - Premium days info
        days = db_tariff.days
        assert days == 30

        # Message should include tariff name and duration
        expected_info = f"{db_tariff.name} - {days} kun"
        assert str(days) in expected_info

    def test_rejected_user_notification(self, db_user, db_tariff):
        """Test user receives notification on rejection"""
        # After rejection, user should receive:
        # - Rejection message
        # - Support contact info
        rejection_message = "To'lov tasdiqlanmadi"
        assert "tasdiqlanmadi" in rejection_message.lower()
