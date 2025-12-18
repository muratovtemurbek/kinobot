from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Tariff, Payment


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ['name', 'days', 'price', 'discounted_price', 'discount_percent', 'order', 'is_active']
    list_filter = ['is_active']
    ordering = ['order', 'days']

    @admin.display(description='Chegirma %')
    def discount_percent(self, obj):
        percent = obj.discount_percent
        if percent > 0:
            return format_html('<span style="color: green;">-{}%</span>', percent)
        return '-'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'tariff', 'amount', 'status_badge', 'created_at']
    list_filter = ['status', 'created_at', 'is_discounted']
    search_fields = ['user__full_name', 'user__username', 'user__user_id']
    readonly_fields = ['user', 'tariff', 'amount', 'is_discounted', 'screenshot_file_id', 'created_at']
    ordering = ['-created_at']

    fieldsets = (
        ('To\'lov ma\'lumotlari', {
            'fields': ('user', 'tariff', 'amount', 'is_discounted', 'screenshot_file_id')
        }),
        ('Holat', {
            'fields': ('status', 'admin_note')
        }),
        ('Tasdiqlash', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Vaqt', {
            'fields': ('created_at',)
        }),
    )

    actions = ['approve_payments', 'reject_payments']

    @admin.display(description='Holat')
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'expired': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        text_color = 'black' if obj.status == 'pending' else 'white'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, text_color, obj.get_status_display()
        )

    @admin.action(description='Tasdiqlash')
    def approve_payments(self, request, queryset):
        from apps.users.models import User
        admin_user = User.objects.filter(user_id=request.user.id).first()

        for payment in queryset.filter(status='pending'):
            payment.status = 'approved'
            payment.approved_by = admin_user
            payment.approved_at = timezone.now()
            payment.save()

            # Premium berish
            user = payment.user
            user.is_premium = True
            if user.premium_expires and user.premium_expires > timezone.now():
                user.premium_expires += timezone.timedelta(days=payment.tariff.days)
            else:
                user.premium_expires = timezone.now() + timezone.timedelta(days=payment.tariff.days)
            user.save()

        self.message_user(request, f'{queryset.count()} to\'lov tasdiqlandi.')

    @admin.action(description='Rad etish')
    def reject_payments(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{queryset.count()} to\'lov rad etildi.')
