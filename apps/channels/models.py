from django.db import models
from django.utils import timezone


class Channel(models.Model):
    """Majburiy obuna kanali"""

    TYPE_CHOICES = [
        ('telegram_channel', 'Telegram kanal'),
        ('telegram_group', 'Telegram guruh'),
        ('telegram_bot', 'Telegram bot'),
        ('instagram', 'Instagram'),
        ('external', 'Tashqi platforma'),
    ]

    channel_id = models.BigIntegerField(unique=True, blank=True, null=True, verbose_name='Kanal ID')
    username = models.CharField(max_length=100, blank=True, default='', verbose_name='Username')
    title = models.CharField(max_length=255, verbose_name='Kanal nomi')
    invite_link = models.URLField(verbose_name='Havola')

    channel_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='telegram_channel', verbose_name='Turi')

    order = models.PositiveIntegerField(default=0, verbose_name='Tartib')
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan")

    class Meta:
        verbose_name = 'Kanal'
        verbose_name_plural = 'Kanallar'
        ordering = ['order', 'title']

    def __str__(self):
        return self.title

    @property
    def is_checkable(self):
        """Obunani tekshirsa bo'ladimi"""
        # Faqat Telegram kanal va guruhlar tekshiriladi
        checkable_types = ['telegram_channel', 'telegram_group', 'public', 'private', 'group']
        return self.channel_type in checkable_types and self.channel_id is not None

    @property
    def subscribers_count(self):
        """Bot orqali obuna bo'lganlar soni"""
        return self.subscriptions.count()


class ChannelSubscription(models.Model):
    """Kanal obunasi - user qachon qaysi kanalga obuna bo'lgani"""

    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Kanal'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='channel_subscriptions',
        verbose_name='Foydalanuvchi'
    )
    subscribed_at = models.DateTimeField(default=timezone.now, verbose_name='Obuna vaqti')

    class Meta:
        verbose_name = 'Kanal obunasi'
        verbose_name_plural = 'Kanal obunalari'
        unique_together = ['channel', 'user']
        ordering = ['-subscribed_at']

    def __str__(self):
        return f"{self.user} -> {self.channel}"
