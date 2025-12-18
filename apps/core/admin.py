from django.contrib import admin
from .models import BotSettings, Broadcast


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_active', 'discount_active', 'referral_active']

    fieldsets = (
        ('Asosiy', {
            'fields': ('is_active', 'maintenance_message')
        }),
        ('To\'lov sozlamalari', {
            'fields': ('card_number', 'card_holder')
        }),
        ('Chegirma', {
            'fields': ('discount_active', 'discount_percent', 'discount_duration'),
            'description': 'Chegirma muddati sekundda (180 = 3 daqiqa)'
        }),
        ('Trial', {
            'fields': ('free_trial_days',)
        }),
        ('Referal', {
            'fields': ('referral_active', 'referral_bonus')
        }),
        ('Kontakt', {
            'fields': ('admin_contact',)
        }),
    )

    def has_add_permission(self, request):
        return not BotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ['target', 'content_type', 'is_advertisement', 'total_users', 'sent_count', 'failed_count', 'is_completed', 'started_at']
    list_filter = ['target', 'content_type', 'is_advertisement', 'is_completed']
    readonly_fields = ['total_users', 'sent_count', 'failed_count', 'is_completed', 'sent_by', 'started_at', 'completed_at']
    ordering = ['-started_at']
