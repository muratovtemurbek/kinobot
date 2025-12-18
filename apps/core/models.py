from django.db import models
from django.core.cache import cache


class BotSettings(models.Model):
    """Bot sozlamalari - Singleton"""

    # Asosiy
    is_active = models.BooleanField(default=True, verbose_name='Bot aktiv')
    maintenance_message = models.TextField(
        blank=True,
        default='Bot texnik ishlar sababli vaqtincha to\'xtatilgan. Iltimos keyinroq urinib ko\'ring.',
        verbose_name='Texnik ishlar xabari'
    )

    # To'lov
    card_number = models.CharField(max_length=50, verbose_name='Karta raqami')
    card_holder = models.CharField(max_length=100, verbose_name='Karta egasi')

    # Chegirma
    discount_active = models.BooleanField(default=True, verbose_name='Chegirma aktiv')
    discount_percent = models.PositiveIntegerField(default=50, verbose_name='Chegirma foizi')
    discount_duration = models.PositiveIntegerField(default=180, verbose_name='Chegirma muddati (sekund)')

    # Trial
    free_trial_days = models.PositiveIntegerField(default=7, verbose_name='Bepul kunlar soni')

    # Referal
    referral_active = models.BooleanField(default=True, verbose_name='Referal aktiv')
    referral_bonus = models.PositiveIntegerField(default=1, verbose_name='Referal bonus (kun)')

    # Admin
    admin_contact = models.CharField(max_length=100, blank=True, default='', verbose_name='Admin kontakt')

    class Meta:
        verbose_name = 'Bot sozlamalari'
        verbose_name_plural = 'Bot sozlamalari'

    def __str__(self):
        return 'Bot sozlamalari'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('bot_settings')

    @classmethod
    def get_settings(cls):
        """Singleton instance olish"""
        settings = cache.get('bot_settings')
        if not settings:
            settings, _ = cls.objects.get_or_create(
                pk=1,
                defaults={
                    'card_number': '8600 0000 0000 0000',
                    'card_holder': 'CARD HOLDER',
                }
            )
            cache.set('bot_settings', settings, 300)
        return settings


class Broadcast(models.Model):
    """Xabar yuborish"""

    TARGET_CHOICES = [
        ('all', 'Hammaga'),
        ('premium', 'Premium foydalanuvchilar'),
        ('regular', 'Oddiy foydalanuvchilar'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('text', 'Matn'),
        ('photo', 'Rasm'),
        ('video', 'Video'),
        ('document', 'Fayl'),
    ]

    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all', verbose_name='Kimga')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='text', verbose_name='Kontent turi')

    text = models.TextField(blank=True, default='', verbose_name='Xabar matni')
    file_id = models.CharField(max_length=255, blank=True, default='', verbose_name='File ID')

    is_advertisement = models.BooleanField(default=False, verbose_name='Reklama (premium ga bormaydi)')

    buttons = models.JSONField(blank=True, null=True, verbose_name='Inline tugmalar')

    # Statistika
    total_users = models.PositiveIntegerField(default=0, verbose_name='Jami foydalanuvchilar')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='Yuborildi')
    failed_count = models.PositiveIntegerField(default=0, verbose_name='Xato')

    is_completed = models.BooleanField(default=False, verbose_name='Tugallandi')

    sent_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='broadcasts',
        verbose_name='Kim yubordi'
    )

    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Boshlangan')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Tugallangan')

    class Meta:
        verbose_name = 'Xabar yuborish'
        verbose_name_plural = 'Xabar yuborishlar'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.get_target_display()} - {self.started_at.strftime('%d.%m.%Y %H:%M')}"
